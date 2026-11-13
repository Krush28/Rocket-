"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Lang } from "@/lib/i18n";
import type { Plan } from "@/lib/api";

// Free maps only: Leaflet (unpkg CDN) + CARTO "Voyager" tiles on OpenStreetMap data + public OSRM road routing (no keys).
// Shows the farm, every ranked mandi (net in hand + distance), the best road route, and nearby storage.
const LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";  // free OSM standard tiles (attribution required, no key)
const ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · routes <a href="https://project-osrm.org">OSRM</a>';

// Minimal typing of the parts of Leaflet we use (loaded at runtime from the CDN, so no npm package / types needed).
type LMap = { remove(): void; removeLayer(l: unknown): void; fitBounds(b: unknown, o?: unknown): void; flyToBounds(b: unknown, o?: unknown): void };
type LMarker = { addTo(m: LMap): LMarker; bindTooltip(h: string, o?: unknown): LMarker; bindPopup(h: string, o?: unknown): LMarker; on(e: string, f: () => void): LMarker; openPopup(): void };
type LNS = {
  map(el: HTMLElement, o?: unknown): LMap; tileLayer(u: string, o?: unknown): { addTo(m: LMap): void };
  control: { zoom(o?: unknown): { addTo(m: LMap): void } }; marker(ll: [number, number], o?: unknown): LMarker;
  polyline(ll: [number, number][], o?: unknown): { addTo(m: LMap): unknown }; latLngBounds(ll: [number, number][]): unknown; divIcon(o: unknown): unknown;
};
declare global { interface Window { L?: LNS } }

let loading: Promise<LNS> | null = null;
function loadLeaflet(): Promise<LNS> {
  if (window.L) return Promise.resolve(window.L);
  if (!loading) {
    loading = new Promise((ok, bad) => {
      const css = document.createElement("link");
      css.rel = "stylesheet"; css.href = LEAFLET_CSS; document.head.appendChild(css);
      const s = document.createElement("script");
      s.src = LEAFLET_JS; s.async = true; s.onload = () => (window.L ? ok(window.L) : bad(new Error("leaflet"))); s.onerror = bad;
      document.head.appendChild(s);
    });
  }
  return loading;
}

const T = {
  title: { en: "Your mandis on the map", hi: "नक्शे पर आपकी मंडियाँ", mr: "नकाशावर तुमच्या मंडई" },
  sub: { en: "Road distance and what you keep at each mandi. Tap a mandi to see its route.", hi: "हर मंडी की सड़क दूरी और आपके हाथ में कितना बचेगा। रास्ता देखने के लिए मंडी दबाएँ।",
    mr: "प्रत्येक मंडईचे रस्ता अंतर आणि तुमच्या हाती किती राहील. मार्ग पाहण्यासाठी मंडई दाबा." },
  farm: { en: "Your farm", hi: "आपका खेत", mr: "तुमचे शेत" }, best: { en: "Best mandi", hi: "सबसे अच्छी मंडी", mr: "सर्वोत्तम मंडई" },
  other: { en: "Other mandis", hi: "अन्य मंडियाँ", mr: "इतर मंडई" }, store: { en: "Storage", hi: "भंडारण", mr: "साठवण" },
  keep: { en: "you keep", hi: "हाथ में", mr: "हाती" }, road: { en: "by road", hi: "सड़क से", mr: "रस्त्याने" },
  drive: { en: "drive", hi: "सफ़र", mr: "प्रवास" }, perq: { en: "/qtl", hi: "/क्विंटल", mr: "/क्विंटल" },
  ask: { en: "Ask the assistant about this mandi", hi: "इस मंडी के बारे में सहायक से पूछें", mr: "या मंडईबद्दल सहाय्यकाला विचारा" },
  less: { en: "less than best", hi: "सबसे अच्छे से कम", mr: "सर्वोत्तमपेक्षा कमी" },
};
const tt = (k: keyof typeof T, l: Lang) => T[k][l] || T[k].en;
const inr = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");
const short = (k: string) => k.split(", ")[0];

type Pt = { key: string; label: string; lat: number; lon: number; net: number; price: number; km: number; rank: number; dup?: boolean };
type Route = { km: number; min: number; line: [number, number][] };

function pin(html: string, size: number) {
  return window.L!.divIcon({ html, className: "kx-pin", iconSize: [size, size], iconAnchor: [size / 2, size / 2], popupAnchor: [0, -size / 2] });
}

export default function MandiMap({ plan, lang, names, onSay }: { plan: Plan; lang: Lang; names: Record<string, string>; onSay: (t: string) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<LMap | null>(null);
  const layers = useRef<Record<string, unknown[]>>({});
  const markers = useRef<Record<string, LMarker>>({});
  const [routes, setRoutes] = useState<Record<string, Route>>({});
  const [active, setActive] = useState<string | null>(null);
  const [showStore, setShowStore] = useState(true);
  const [ready, setReady] = useState(false);

  const farm = plan.profile.location as { name: string; lat: number; lon: number };
  const pts: Pt[] = useMemo(() => {
    const geo = new Map((plan.mandis || []).map((m) => [m.name, m as unknown as { lat: number; lon: number }]));
    return plan.options.filter((o) => o.type !== "hold").map((o, i) => ({ o, g: geo.get(o.destination), i }))
      .filter((x) => x.g && x.g.lat != null)
      .map(({ o, g, i }) => ({ key: o.destination, label: names[o.destination] || o.destination, lat: g!.lat, lon: g!.lon, net: o.net, price: o.price, km: o.distance_km, rank: i + 1 }))
      .map((p, i, all) => {  // two mandis in the same town (e.g. APMC + sub-yard): fan them out so no pin hides another
        const n = all.slice(0, i).filter((q) => Math.abs(q.lat - p.lat) < 0.012 && Math.abs(q.lon - p.lon) < 0.012).length;
        return n ? { ...p, lat: p.lat + 0.03 * Math.sin(n * 2.1), lon: p.lon - 0.035 * Math.abs(Math.cos(n * 2.1)) - 0.02, dup: true } : p;
      });
  }, [plan, names]);
  const stores = useMemo(() => ((plan.storage || []) as unknown as { name: string; lat: number; lon: number; distance_km: number; rate_qtl_day: number }[])
    .filter((s) => s.lat != null).slice(0, 4), [plan]);
  const best = pts[0];

  // real road routes for the top 3 (public OSRM server; a dashed straight line is drawn until/unless it answers)
  useEffect(() => {
    if (!farm?.lat) return;
    let live = true;
    pts.slice(0, 3).forEach((p) => {
      fetch(`https://router.project-osrm.org/route/v1/driving/${farm.lon},${farm.lat};${p.lon},${p.lat}?overview=full&geometries=geojson`)
        .then((r) => r.json()).then((d) => {
          const r0 = d?.routes?.[0];
          if (!live || !r0) return;
          setRoutes((x) => ({ ...x, [p.key]: { km: r0.distance / 1000, min: r0.duration / 60, line: r0.geometry.coordinates.map((c: number[]) => [c[1], c[0]]) } }));
        }).catch(() => {});
    });
    return () => { live = false; };
  }, [farm?.lat, farm?.lon, pts]);

  // build the map once per plan
  useEffect(() => {
    if (!box.current || !farm?.lat) return;
    let dead = false;
    loadLeaflet().then((L) => {
      if (dead || !box.current) return;
      map.current?.remove();
      const m = L.map(box.current, { zoomControl: false, scrollWheelZoom: false });
      map.current = m;
      L.control.zoom({ position: "bottomright" }).addTo(m);
      L.tileLayer(TILES, { attribution: ATTR, maxZoom: 18, className: "kx-tiles" }).addTo(m);
      markers.current = {};
      L.marker([farm.lat, farm.lon], { icon: pin(`<div class="kx-farm"><svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" fill="#fff"/></svg></div>`, 44), zIndexOffset: 1000 })
        .addTo(m).bindTooltip(`<b>${tt("farm", lang)}</b><br/>${farm.name}`, { direction: "top", offset: [0, -20] });
      pts.forEach((p) => {
        const isBest = p.rank === 1;
        const mk = L.marker([p.lat, p.lon], {
          icon: pin(isBest ? `<div class="kx-best"><span>★</span></div>` : `<div class="kx-mandi">${p.rank}</div>`, isBest ? 46 : 34),
          zIndexOffset: isBest ? 900 : 500 - p.rank,
        }).addTo(m);
        mk.bindTooltip(`<div class="kx-tag ${isBest ? "kx-tag-best" : ""}">${inr(p.net)}<small>${Math.round(p.km)} km</small></div>`,
          { permanent: true, direction: p.dup ? "left" : "right", offset: [p.dup ? -16 : isBest ? 22 : 16, 0], className: "kx-tip" });
        const diff = best && !isBest ? `<div class="kx-pop-diff">−${inr(best.net - p.net)} ${tt("less", lang)}</div>` : "";
        mk.bindPopup(`<div class="kx-pop"><div class="kx-pop-rank">#${p.rank}${isBest ? " · " + tt("best", lang) : ""}</div><div class="kx-pop-name">${short(p.label)}</div>
          <div class="kx-pop-sub">${p.label.split(", ").slice(1).join(", ")}</div><div class="kx-pop-net">${inr(p.net)} <span>${tt("keep", lang)}</span></div>
          <div class="kx-pop-row">${inr(p.price)}${tt("perq", lang)} · ${Math.round(p.km)} km</div>${diff}</div>`, { closeButton: false, maxWidth: 260 });
        mk.on("click", () => setActive(p.key));
        markers.current[p.key] = mk;
      });
      const all: [number, number][] = [[farm.lat, farm.lon], ...pts.map((p) => [p.lat, p.lon] as [number, number])];
      m.fitBounds(L.latLngBounds(all), { padding: [50, 50], maxZoom: 11 });
      setReady(true);
    }).catch(() => {});
    return () => { dead = true; };
  }, [farm?.lat, farm?.lon, farm?.name, pts, best, lang]);

  // lines (redrawn when road routes arrive / selection changes) and storage markers
  useEffect(() => {
    const L = window.L, m = map.current;
    if (!L || !m || !ready || !farm?.lat) return;
    Object.values(layers.current).flat().forEach((l) => m.removeLayer(l));
    layers.current = {};
    pts.forEach((p) => {
      const r = routes[p.key];
      const on = active === p.key || (!active && p.rank === 1);
      const line: [number, number][] = r ? r.line : [[farm.lat, farm.lon], [p.lat, p.lon]];
      const ls: unknown[] = [];
      if (on) ls.push(L.polyline(line, { color: "#0F3D2E", weight: 10, opacity: 0.22, lineCap: "round" }).addTo(m));
      ls.push(L.polyline(line, on ? { color: p.rank === 1 ? "#F2B01E" : "#2D6A52", weight: 5, opacity: 1, lineCap: "round" }
        : { color: "#1C5A43", weight: 2, opacity: 0.45, dashArray: "4 8" }).addTo(m));
      layers.current[p.key] = ls;
    });
    if (showStore) {
      layers.current.__store = stores.map((s) => L.marker([s.lat, s.lon], { icon: pin(`<div class="kx-store">❄</div>`, 26), zIndexOffset: 100 }).addTo(m)
        .bindTooltip(`<b>${s.name}</b><br/>${Math.round(s.distance_km)} km · ₹${s.rate_qtl_day}/q/day`, { direction: "top" }));
    }
  }, [routes, active, ready, pts, stores, showStore, farm?.lat, farm?.lon]);

  useEffect(() => () => { map.current?.remove(); map.current = null; }, []);

  function focus(p: Pt) {
    setActive(p.key);
    const r = routes[p.key];
    const L = window.L, m = map.current;
    if (!L || !m) return;
    m.flyToBounds(L.latLngBounds(r ? r.line : [[farm.lat, farm.lon], [p.lat, p.lon]]), { padding: [60, 60], duration: 0.8, maxZoom: 12 });
    setTimeout(() => markers.current[p.key]?.openPopup(), 850);
  }

  if (!farm?.lat || pts.length === 0) return null;
  const sel = pts.find((p) => p.key === active);
  return (
    <section id="sec-map" className="relative isolate z-0 overflow-hidden rounded-[22px] border border-rule bg-cream">
      <style>{CSS}</style>
      <div className="flex flex-wrap items-end justify-between gap-2 px-5 pt-5">
        <div>
          <h2 className="font-display text-[22px] font-bold">{tt("title", lang)}</h2>
          <p className="text-[14px] text-muted">{tt("sub", lang)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[13px]">
          <span className="kx-leg"><i className="kx-dot" style={{ background: "#1C5A43" }} />{tt("farm", lang)}</span>
          <span className="kx-leg"><i className="kx-dot" style={{ background: "#F2B01E" }} />{tt("best", lang)}</span>
          <span className="kx-leg"><i className="kx-dot" style={{ background: "#fff", border: "2px solid #1C5A43" }} />{tt("other", lang)}</span>
          {stores.length > 0 && (
            <button onClick={() => setShowStore(!showStore)} className={`kx-leg ${showStore ? "" : "opacity-50"}`}><i className="kx-dot" style={{ background: "#3B82F6" }} />{tt("store", lang)}</button>
          )}
        </div>
      </div>
      <div className="relative mt-3">
        <div ref={box} className="h-[420px] w-full sm:h-[480px]" aria-label={tt("title", lang)} />
        {best && (
          <div className="pointer-events-none absolute left-3 top-3 z-[500] max-w-[78%] rounded-2xl bg-forest/95 px-4 py-3 text-cream shadow-xl">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-mint">★ {tt("best", lang)}</p>
            <p className="font-display text-[18px] font-bold leading-tight">{short(best.label)}</p>
            <p className="text-[14px]"><b className="text-mustard">{inr(best.net)}</b> {tt("keep", lang)} · {routes[best.key]
              ? `${Math.round(routes[best.key].km)} km ${tt("road", lang)} · ${Math.round(routes[best.key].min)} min ${tt("drive", lang)}` : `${Math.round(best.km)} km`}</p>
          </div>
        )}
      </div>
      <div className="flex gap-2 overflow-x-auto px-4 py-4">
        {pts.map((p) => {
          const r = routes[p.key];
          const on = active === p.key || (!active && p.rank === 1);
          return (
            <button key={p.key} onClick={() => focus(p)}
              className={`min-w-[190px] shrink-0 rounded-2xl border-2 p-3 text-left transition ${on ? (p.rank === 1 ? "border-mustard bg-[#FFF6DD]" : "border-leaf bg-okbg") : "border-rule bg-paper hover:border-sage"}`}>
              <div className="flex items-center gap-2">
                <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-[13px] font-bold ${p.rank === 1 ? "bg-mustard text-ink" : "bg-forest text-cream"}`}>{p.rank === 1 ? "★" : p.rank}</span>
                <span className="truncate font-semibold">{short(p.label)}</span>
              </div>
              <p className="mt-1 font-display text-[20px] font-bold">{inr(p.net)}</p>
              <p className="text-[13px] text-muted">{r ? `${Math.round(r.km)} km · ${Math.round(r.min)} min` : `${Math.round(p.km)} km`} · {inr(p.price)}{tt("perq", lang)}</p>
              {p.rank > 1 && best && <p className="text-[12px] font-semibold text-loss">−{inr(best.net - p.net)}</p>}
            </button>
          );
        })}
      </div>
      {sel && (
        <div className="px-5 pb-4">
          <button onClick={() => onSay(`price at ${short(sel.label)}`)} className="text-[14px] font-semibold text-leaf underline">{tt("ask", lang)}</button>
        </div>
      )}
    </section>
  );
}

const CSS = `
.kx-pin{background:transparent;border:0}
.kx-tiles{filter:saturate(.75) brightness(1.03) contrast(.95)}
.kx-farm{width:44px;height:44px;border-radius:50% 50% 50% 4px;transform:rotate(-45deg);background:#1C5A43;display:grid;place-items:center;box-shadow:0 6px 16px rgba(15,61,46,.45);border:3px solid #fff}
.kx-farm svg{transform:rotate(45deg)}
.kx-best{width:46px;height:46px;border-radius:50%;background:#F2B01E;border:3px solid #fff;display:grid;place-items:center;animation:kxpulse 2s infinite;font-size:22px;color:#11221A;font-weight:800}
.kx-mandi{width:34px;height:34px;border-radius:50%;background:#fff;border:3px solid #1C5A43;display:grid;place-items:center;font:700 14px/1 system-ui;color:#0F3D2E;box-shadow:0 3px 10px rgba(0,0,0,.2)}
.kx-store{width:26px;height:26px;border-radius:8px;background:#3B82F6;color:#fff;display:grid;place-items:center;font-size:14px;border:2px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.25)}
@keyframes kxpulse{0%{box-shadow:0 0 0 0 rgba(242,176,30,.65)}70%{box-shadow:0 0 0 18px rgba(242,176,30,0)}100%{box-shadow:0 0 0 0 rgba(242,176,30,0)}}
.kx-tip{background:transparent;border:0;box-shadow:none;padding:0}
.kx-tip:before{display:none}
.kx-tag{background:#0F3D2E;color:#F3F1E8;border-radius:10px;padding:3px 8px;font:700 13px/1.2 system-ui;white-space:nowrap;box-shadow:0 3px 10px rgba(0,0,0,.25)}
.kx-tag small{display:block;font-weight:500;font-size:11px;color:#A9C9B4}
.kx-tag-best{background:#F2B01E;color:#11221A}.kx-tag-best small{color:#4a3a00}
.kx-pop{font-family:system-ui;min-width:190px}.kx-pop-rank{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#2D6A52}
.kx-pop-name{font-size:17px;font-weight:800;color:#11221A}.kx-pop-sub{font-size:12px;color:#55635B}
.kx-pop-net{margin-top:6px;font-size:20px;font-weight:800;color:#0F3D2E}.kx-pop-net span{font-size:12px;font-weight:600;color:#55635B}
.kx-pop-row{font-size:13px;color:#33433A}.kx-pop-diff{margin-top:4px;font-size:12px;font-weight:700;color:#B03A2E}
.leaflet-popup-content-wrapper{border-radius:16px}
.kx-leg{display:inline-flex;align-items:center;gap:6px;border-radius:999px;background:#ECEAE0;padding:4px 10px}
.kx-dot{display:inline-block;width:12px;height:12px;border-radius:50%}
`;
