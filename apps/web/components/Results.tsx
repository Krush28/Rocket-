"use client";

import { useState } from "react";
import { createOrder, type ChatReply, type Option } from "@/lib/api";
import { rupees, t, type Lang } from "@/lib/i18n";
import PriceChart from "./PriceChart";

const card = "rounded-[22px] bg-white p-5";
const h2 = "font-display text-[20px] font-bold tracking-tight";
const DED: Record<string, string> = { transport: "Transport", handling: "Handling (hamali)", commission: "Commission", storage: "Storage", financing: "Financing", risk_allowance: "Risk allowance" };
const short = (k: string) => k.split(", ")[0];
const rest = (k: string) => k.split(", ").slice(1).join(", ");

export default function Results({ reply, lang, onRestart }: { reply: ChatReply; lang: Lang; onRestart: () => void }) {
  const p = reply.plan!;
  const best = p.recommendation?.best;
  const decision = p.recommendation?.decision ?? p.sell_vs_hold?.decision;
  const live = p.data_mode === "LIVE";
  const firstPrice = p.prices ? Object.values(p.prices)[0] : undefined;
  const failed = p.trace.find((x) => x.status === "failed");
  const [order, setOrder] = useState<string>("");
  const prof = p.profile;
  const ranked = p.options.filter((o) => o.type !== "hold");

  return (
    <main className="min-h-screen bg-paper">
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-5 sm:px-6">
        <header className="flex items-center justify-between gap-3">
          <span className="font-display text-[22px] font-extrabold tracking-tight">KRISHI-X</span>
          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[13px] font-semibold tracking-wide ${live ? "bg-okbg text-forest" : "bg-note text-ink"}`}>
            <span className={`h-2 w-2 rounded-full ${live ? "bg-[#2E7D4F]" : "bg-mustard"}`} />
            {live ? `LIVE PRICES · ${firstPrice?.latest_date ?? ""}` : "DEMO DATA"}
          </span>
        </header>

        {best ? (
          <section className="rounded-[28px] bg-forest p-6 text-cream">
            <p className="text-[13px] font-semibold uppercase tracking-widest text-sage">{prof.original_qty} {prof.original_unit} {prof.crop} · {prof.location.name}</p>
            <h1 className="mt-2 font-display text-[24px] font-bold leading-tight tracking-tight">{best.label}</h1>
            <p className="mt-4 text-[15px] text-sage">{t("keep", lang)}</p>
            <p className="font-display text-[48px] font-extrabold leading-none tracking-tighter text-white sm:text-[56px]">{rupees(best.net)}</p>
            <KeepBar gross={best.gross_revenue} costs={best.total_deductions} />
            <p className="mt-3 text-[14px] text-sage">{best.verification} · {short(best.destination)} · {best.distance_km} km (estimate)</p>
            {order ? <p role="status" className="mt-5 rounded-2xl bg-leaf p-3 text-[16px]">Order {order} created. Amounts are expected, not final.</p> : (
              <button onClick={() => createOrder(best, prof).then((o) => setOrder(o.id)).catch(() => setOrder(""))}
                className="mt-5 min-h-[56px] w-full rounded-full bg-mustard text-[18px] font-bold text-ink">{t("order", lang)}</button>
            )}
          </section>
        ) : (
          <section className="rounded-[28px] bg-forest p-6 text-cream">
            <h1 className="font-display text-[24px] font-bold">Not enough information to recommend a sale</h1>
            <p className="mt-2 text-[17px] text-sage">{failed?.error ?? "No feasible selling option was found."}</p>
          </section>
        )}

        {best && (
          <section className="rounded-[22px] border-[1.5px] border-rule bg-cream p-5">
            <h2 className="text-[12px] font-semibold uppercase tracking-widest text-muted">{t("slip", lang)}</h2>
            <Row label={t("gross", lang)} value={rupees(best.gross_revenue)} strong />
            {Object.entries(best.deductions).filter(([, v]) => v > 0).map(([k, v]) => <Row key={k} label={`− ${DED[k] ?? k}`} value={rupees(v)} muted />)}
            <div className="flex justify-between pt-3 font-display text-[20px] font-bold"><span>= {t("net", lang)}</span><span>{rupees(best.net)}</span></div>
            <p className="mt-2 text-[13px] text-muted">Costs are ESTIMATES (editable placeholders), not verified quotes.</p>
          </section>
        )}

        {decision && (
          <section className={card}>
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className={h2}>{t("hold", lang)}</h2>
              <span className="rounded-full bg-[#FCE9B2] px-3 py-1 text-[13px] font-bold tracking-wide text-[#6B4A00]">{decision.action}</span>
            </div>
            <p className="mt-2 text-[17px] text-[#33433A]">{decision.reason}</p>
            {decision.reconsider_on && <p className="mt-1 text-[15px] text-muted">Check again on {decision.reconsider_on}. Future prices are never guaranteed.</p>}
            {!!p.sell_vs_hold?.skipped?.length && (
              <ul className="mt-2 list-disc pl-5 text-[15px] text-muted">{p.sell_vs_hold.skipped.map((s) => <li key={s.days}>Hold {s.days} days: {s.why}</li>)}</ul>
            )}
          </section>
        )}

        {ranked.length > 0 && (
          <section className={`${card} py-2`}>
            <h2 className={`${h2} pb-1 pt-3`}>{t("where", lang)}</h2>
            {ranked.map((o, i) => <OptionRow key={o.label} o={o} i={i} bestNet={ranked[0].net} />)}
          </section>
        )}

        {best && <section className={card}><h2 className={`${h2} mb-3`}>{t("history", lang)} · {short(best.destination)}</h2><PriceChart crop={prof.crop} mandiKey={best.destination} /></section>}

        <section className={card}>
          <h2 className={h2}>{t("retail", lang)}</h2>
          {p.retail?.length ? (
            <ul className="mt-2 space-y-1 text-[16px]">{p.retail.map((r) => <li key={r.city}>{r.city}: {rupees(r.retail_price)}/qtl-equivalent <span className="text-[13px] text-muted">(DEMO, consumer price, not your selling price)</span></li>)}</ul>
          ) : <p className="mt-2 text-[16px] text-muted">No verified retail price source is connected yet. Retail prices are never your selling price.</p>}
        </section>

        <div className="grid gap-4 sm:grid-cols-2">
          <section className={card}>
            <h2 className={h2}>{t("storage", lang)}</h2>
            {p.storage?.length ? p.storage.slice(0, 3).map((w) => (
              <div key={w.name} className="mt-3 border-t border-[#ECEAE0] pt-3 text-[15px]">
                <b>{w.name}</b> <span className="text-[13px] text-muted">· {w.verification}</span>
                <div className="text-muted">{w.distance_km} km · ₹{w.rate_qtl_day}/qtl/day · 7 days ≈ {rupees(w.est_cost_7d)} ({w.cost_label})</div>
                <div className="text-[13px] text-muted">{w.availability}</div>
              </div>
            )) : <p className="mt-2 text-[16px] text-muted">No storage found within 200 km.</p>}
          </section>
          <section className={card}>
            <h2 className={h2}>{t("transport", lang)}</h2>
            {p.transport?.slice(0, 2).map((tr) => (
              <div key={tr.destination} className="mt-3 border-t border-[#ECEAE0] pt-3 text-[15px]">
                <b>{short(tr.destination)}</b> <span className="text-muted">· {tr.distance_km} km</span>
                {tr.options.slice(0, 2).map((v) => <div key={v.transporter} className="text-muted">{v.vehicle}: {rupees(v.total)} ({rupees(v.per_qtl)}/qtl) · {v.quote_status}</div>)}
              </div>
            ))}
          </section>
        </div>

        <section className="rounded-[22px] bg-note p-5 text-[15px] text-[#3A2A00]"><b>{t("real", lang)}:</b> {p.labels}</section>
        <button onClick={onRestart} className="min-h-[52px] rounded-full bg-forest text-[17px] font-semibold text-cream">{t("restart", lang)}</button>
      </div>
    </main>
  );
}

function KeepBar({ gross, costs }: { gross: number; costs: number }) {
  const kept = gross > 0 ? Math.max(0, Math.min(100, ((gross - costs) / gross) * 100)) : 0;
  return (
    <>
      <div className="mt-4 flex h-2 gap-[3px] overflow-hidden rounded bg-leaf" aria-hidden>
        <div className="bg-mint" style={{ width: `${kept}%` }} /><div className="min-w-[4px] flex-1 bg-mustard" />
      </div>
      <div className="mt-1.5 flex justify-between text-[13px] text-sage"><span>{Math.round(kept)}% kept</span><span>costs {rupees(costs)}</span></div>
    </>
  );
}

function Row({ label, value, strong, muted }: { label: string; value: string; strong?: boolean; muted?: boolean }) {
  return <div className={`flex justify-between border-b-[1.5px] border-dashed border-[#C9C6B4] py-2.5 text-[16px] ${muted ? "text-muted" : ""}`}><span>{label}</span>{strong ? <b>{value}</b> : <span>{value}</span>}</div>;
}

function OptionRow({ o, i, bestNet }: { o: Option; i: number; bestNet: number }) {
  return (
    <div className="grid grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-3 border-t-[1.5px] border-[#ECEAE0] py-3.5">
      <div className={`grid h-9 w-9 place-items-center rounded-full text-[14px] font-bold ${i === 0 ? "bg-forest text-cream" : "bg-[#ECEAE0]"}`}>{i + 1}</div>
      <div className="min-w-0">
        <div className="truncate text-[16px] font-semibold">{short(o.destination)}</div>
        <div className="truncate text-[13px] text-muted">{rest(o.destination) && `${rest(o.destination)} · `}{o.distance_km} km · {rupees(o.price)}/qtl · {o.type.replace("_", " ")}</div>
      </div>
      <div className="text-right">
        <b className="font-display text-[18px]">{rupees(o.net)}</b>
        {i > 0 && <div className="text-[13px] text-loss">−{rupees(bestNet - o.net).slice(1)}</div>}
      </div>
    </div>
  );
}
