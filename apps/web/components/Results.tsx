"use client";

import type { Crop, Option, Order, Plan } from "@/lib/api";
import Journey from "./Journey";
import { cropName, isKey, rupees, t, unitName, type Key, type Lang } from "@/lib/i18n";
import PriceChart from "./PriceChart";

const card = "rounded-[22px] bg-white p-5 scroll-mt-4";
const h2 = "font-display text-[20px] font-bold tracking-tight";
const DED: Record<string, Key> = { transport: "transportCost", handling: "handling", commission: "commission", storage: "storageCost", financing: "financing", risk_allowance: "risk_allowance" };
const ORDER_SAY: Record<Lang, string> = { en: "create the order", hi: "ऑर्डर बनाओ", mr: "ऑर्डर तयार करा" };
let NAMES: Record<string, string> = {}; // mandi key -> name in the farmer's script (set per render from plan.names)
const short = (k: string) => (NAMES[k] || k).split(", ")[0];
const rest = (k: string) => (NAMES[k] || k).split(", ").slice(1).join(", ");
const word = (k: string, l: Lang) => (isKey(k) ? t(k, l) : k); // codes -> farmer words, unknown codes pass through

type Props = { plan: Plan; lang: Lang; order: Order | null; crops: Crop[]; onSay: (text: string) => void };

export default function Results({ plan: p, lang, order, crops, onSay }: Props) {
  const rec = p.recommendation;
  const best = rec?.best;
  const decision = rec?.decision ?? p.sell_vs_hold?.decision;
  const firstPrice = p.prices ? Object.values(p.prices)[0] : undefined;
  const allStale = !!p.prices && Object.values(p.prices).every((x) => x.stale);
  const live = p.data_mode === "LIVE" && !allStale;
  const failed = p.trace.find((x) => x.status === "failed");
  const prof = p.profile;
  NAMES = p.names || {};
  const ranked = p.options.filter((o) => o.type !== "hold");
  const km = t("km", lang);

  return (
    <main className="min-h-screen bg-paper pb-56" lang={lang}>
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-5 sm:px-6">
        <header className="flex items-center justify-between gap-3">
          <span className="font-display text-[22px] font-extrabold tracking-tight">{lang === "en" ? "KRISHI-X" : "कृषि-एक्स"}</span>
          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[13px] font-semibold tracking-wide ${live ? "bg-okbg text-forest" : "bg-note text-ink"}`}>
            <span className={`h-2 w-2 rounded-full ${live ? "bg-[#2E7D4F]" : "bg-mustard"}`} />
            {live ? `${t("live", lang)} · ${firstPrice?.latest_date ?? ""}` : allStale && p.data_mode === "LIVE" ? `${t("old", lang)} · ${firstPrice?.latest_date ?? ""}` : t("demo", lang)}
          </span>
        </header>

        {crops.length > 1 && (
          <nav aria-label={t("crops", lang)} className="flex flex-wrap gap-2">
            {crops.map((c) => (
              <button key={c.crop} onClick={() => !c.active && onSay(c.label)} aria-pressed={c.active}
                className={`min-h-[44px] rounded-full px-4 text-[16px] font-semibold ${c.active ? "bg-forest text-cream" : "bg-white text-ink"}`}>
                {c.label}{c.qty ? ` · ${c.qty} ${unitName(c.unit, lang)}` : ""}
              </button>
            ))}
          </nav>
        )}

        {best ? (
          <section className="rounded-[28px] bg-forest p-6 text-cream">
            <p className="text-[13px] font-semibold uppercase tracking-widest text-sage">{prof.original_qty} {unitName(prof.original_unit, lang)} {cropName(prof.crop, lang)} · {prof.location.name}</p>
            <h1 className="mt-2 font-display text-[24px] font-bold leading-tight tracking-tight">{best.label}</h1>
            <p className="mt-4 text-[15px] text-sage">{t("keep", lang)}</p>
            <p className="font-display text-[48px] font-extrabold leading-none tracking-tighter text-white sm:text-[56px]">{rupees(best.net)}</p>
            <KeepBar gross={best.gross_revenue} costs={best.total_deductions} lang={lang} />
            <p className="mt-3 text-[14px] text-sage">{best.verification} · {short(best.destination)} · {t("kmEst", lang, { n: best.distance_km })}</p>
            {!order && <button onClick={() => onSay(ORDER_SAY[lang])} className="mt-5 min-h-[56px] w-full rounded-full bg-mustard text-[18px] font-bold text-ink">{t("order", lang)}</button>}
          </section>
        ) : (
          <section className="rounded-[28px] bg-forest p-6 text-cream">
            <h1 className="font-display text-[24px] font-bold">{t("noReco", lang)}</h1>
            <p className="mt-2 text-[17px] text-sage">{rec?.reason ?? failed?.error ?? t("noOption", lang)}</p>
            {!!rec?.excluded?.length && (
              <ul className="mt-3 list-disc pl-5 text-[15px] text-sage">{rec.excluded.map((e) => <li key={e.mandi}>{t("excluded", lang)}: {short(e.mandi)}: {e.reason}</li>)}</ul>
            )}
          </section>
        )}

        {order && (
          <section id="sec-order" className={card}>
            <h2 className={h2}>{t("orderTitle", lang)} · {order.id}</h2>
            <Journey order={order} lang={lang} />
          </section>
        )}

        {best && (
          <section className="rounded-[22px] border-[1.5px] border-rule bg-cream p-5">
            <h2 className="text-[12px] font-semibold uppercase tracking-widest text-muted">{t("slip", lang)}</h2>
            <Row label={t("gross", lang)} value={rupees(best.gross_revenue)} strong />
            {Object.entries(best.deductions).filter(([, v]) => v > 0).map(([k, v]) => <Row key={k} label={`− ${DED[k] ? t(DED[k], lang) : k}`} value={rupees(v)} muted />)}
            <div className="flex justify-between pt-3 font-display text-[20px] font-bold"><span>= {t("net", lang)}</span><span>{rupees(best.net)}</span></div>
            <p className="mt-2 text-[13px] text-muted">{t("costsNote", lang)}</p>
          </section>
        )}

        {decision && (
          <section className={card}>
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className={h2}>{t("hold", lang)}</h2>
              <span className="rounded-full bg-[#FCE9B2] px-3 py-1 text-[13px] font-bold tracking-wide text-[#6B4A00]">{word(decision.action, lang)}</span>
              {rec?.confidence && <span className="rounded-full bg-[#ECEAE0] px-3 py-1 text-[13px] font-semibold">{t("confidence", lang)}: {word(rec.confidence.label, lang)}</span>}
            </div>
            <p className="mt-2 text-[17px] text-[#33433A]">{decision.reason}</p>
            {!!decision.factors?.length && <ul className="mt-2 list-disc pl-5 text-[15px] text-[#33433A]">{decision.factors.map((f) => <li key={f}>{f}</li>)}</ul>}
            {decision.reconsider_on && <p className="mt-2 text-[15px] text-muted">{t("checkAgain", lang, { d: decision.reconsider_on })}</p>}
            {rec?.confidence && <p className="mt-1 text-[13px] text-muted">{[...rec.confidence.detractors, ...rec.confidence.contributors].slice(0, 3).join(" · ")}</p>}
          </section>
        )}

        {ranked.length > 0 && (
          <section id="sec-compare" className={`${card} py-2`}>
            <h2 className={`${h2} pb-1 pt-3`}>{t("where", lang)}</h2>
            {ranked.map((o, i) => <OptionRow key={o.label} o={o} i={i} bestNet={ranked[0].net} lang={lang} km={km} />)}
          </section>
        )}

        {best && <section id="sec-forecast" className={card}><h2 className={`${h2} mb-3`}>{t("history", lang)} · {short(best.destination)}</h2><PriceChart crop={prof.crop} mandiKey={best.destination} lang={lang} /></section>}

        <section className={card}>
          <h2 className={h2}>{t("retail", lang)}</h2>
          {p.retail?.length ? (
            <ul className="mt-2 space-y-1 text-[16px]">{p.retail.map((r) => <li key={r.city}>{r.city}: {rupees(r.retail_price)}{t("qtl", lang)} <span className="text-[13px] text-muted">{t("retailNote", lang)}</span></li>)}</ul>
          ) : <p className="mt-2 text-[16px] text-muted">{t("retailNone", lang)}</p>}
        </section>

        <div id="sec-logistics" className="grid scroll-mt-4 gap-4 sm:grid-cols-2">
          <section className={card}>
            <h2 className={h2}>{t("storage", lang)}</h2>
            {p.storage?.length ? p.storage.slice(0, 3).map((w) => (
              <div key={w.name} className="mt-3 border-t border-[#ECEAE0] pt-3 text-[15px]">
                <b>{w.name}</b> <span className="text-[13px] text-muted">· {w.verification}</span>
                <div className="text-muted">{w.distance_km} {km} · ₹{w.rate_qtl_day}{t("perDay", lang)} · {t("week", lang, { x: rupees(w.est_cost_7d) })} ({w.cost_label})</div>
                <div className="text-[13px] text-muted">{w.availability}</div>
              </div>
            )) : <p className="mt-2 text-[16px] text-muted">{t("noStorage", lang)}</p>}
          </section>
          <section className={card}>
            <h2 className={h2}>{t("transport", lang)}</h2>
            {p.transport?.slice(0, 2).map((tr) => (
              <div key={tr.destination} className="mt-3 border-t border-[#ECEAE0] pt-3 text-[15px]">
                <b>{short(tr.destination)}</b> <span className="text-muted">· {tr.distance_km} {km}</span>
                {tr.options.slice(0, 2).map((v) => <div key={v.transporter} className="text-muted">{v.vehicle}: {rupees(v.total)} ({rupees(v.per_qtl)}{t("qtl", lang)}) · {v.quote_status}</div>)}
              </div>
            ))}
          </section>
        </div>

        <section className="rounded-[22px] bg-note p-5 text-[15px] text-[#3A2A00]"><b>{t("real", lang)}:</b> {p.labels}</section>
      </div>
    </main>
  );
}

function KeepBar({ gross, costs, lang }: { gross: number; costs: number; lang: Lang }) {
  const kept = gross > 0 ? Math.max(0, Math.min(100, ((gross - costs) / gross) * 100)) : 0;
  return (
    <>
      <div className="mt-4 flex h-2 gap-[3px] overflow-hidden rounded bg-leaf" aria-hidden>
        <div className="bg-mint" style={{ width: `${kept}%` }} /><div className="min-w-[4px] flex-1 bg-mustard" />
      </div>
      <div className="mt-1.5 flex justify-between text-[13px] text-sage"><span>{t("kept", lang, { n: Math.round(kept) })}</span><span>{t("costs", lang, { x: rupees(costs) })}</span></div>
    </>
  );
}

function Row({ label, value, strong, muted }: { label: string; value: string; strong?: boolean; muted?: boolean }) {
  return <div className={`flex justify-between border-b-[1.5px] border-dashed border-[#C9C6B4] py-2.5 text-[16px] ${muted ? "text-muted" : ""}`}><span>{label}</span>{strong ? <b>{value}</b> : <span>{value}</span>}</div>;
}

function OptionRow({ o, i, bestNet, lang, km }: { o: Option; i: number; bestNet: number; lang: Lang; km: string }) {
  return (
    <div className="grid grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-3 border-t-[1.5px] border-[#ECEAE0] py-3.5">
      <div className={`grid h-9 w-9 place-items-center rounded-full text-[14px] font-bold ${i === 0 ? "bg-forest text-cream" : "bg-[#ECEAE0]"}`}>{i + 1}</div>
      <div className="min-w-0">
        <div className="truncate text-[16px] font-semibold">{short(o.destination)}</div>
        <div className="truncate text-[13px] text-muted">{rest(o.destination) && `${rest(o.destination)} · `}{o.distance_km} {km} · {rupees(o.price)}{t("qtl", lang)} · {word(o.type, lang)}</div>
      </div>
      <div className="text-right">
        <b className="font-display text-[18px]">{rupees(o.net)}</b>
        {i > 0 && <div className="text-[13px] text-loss">−{rupees(bestNet - o.net).slice(1)}</div>}
      </div>
    </div>
  );
}
