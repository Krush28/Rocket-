"use client";

import { useEffect, useState } from "react";
import { card, Pill, PortalShell, Stat } from "@/components/Portal";
import { fpo, kg, rupees, short } from "@/lib/ops";

type Summary = Awaited<ReturnType<typeof fpo>>;

// FPO / farmer-association head: what members hold, what can go as pooled truckloads, and the sales pipeline.
export default function FPO() {
  const [s, setS] = useState<Summary | null>(null), [err, setErr] = useState("");
  useEffect(() => {
    const load = () => fpo().then(setS).catch((e) => setErr(e.message));
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);
  const total = s?.members_produce.reduce((a, r) => a + r.qty_kg, 0) ?? 0;
  const inFlight = s ? Object.entries(s.orders_by_status).filter(([k]) => !["sale_confirmed", "cancelled"].includes(k)).reduce((a, [, v]) => a + v, 0) : 0;
  return (
    <PortalShell role="fpo" title="FPO head">
      {() => (
        <>
          {err && <p className="text-loss">{err}</p>}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Members' produce" value={kg(total)} /><Stat label="Orders in progress" value={inFlight} />
            <Stat label="Sales closed" value={s?.sales_closed ?? 0} /><Stat label="Members earned (net)" value={rupees(s?.net_earnings_total ?? 0)} />
          </div>
          <section className={`${card} mt-6`}>
            <h2 className="font-display text-[22px] font-bold">Produce ready to sell, by crop</h2>
            <p className="text-[14px] text-muted">Pool members&apos; lots into full trucks (10 t) to cut transport cost per quintal.</p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-[15px]">
                <thead><tr className="text-muted"><th className="py-2">Crop</th><th>Farmers</th><th>Quantity</th><th>Full trucks</th></tr></thead>
                <tbody>
                  {s?.members_produce.map((r) => (
                    <tr key={r.crop} className="border-t border-rule"><td className="py-2 font-semibold capitalize">{r.crop_label}</td><td>{r.farmers}</td>
                      <td>{kg(r.qty_kg)}</td><td>{r.trucks_10t}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className={`${card} mt-6`}>
            <h2 className="font-display text-[22px] font-bold">Recent orders</h2>
            <div className="mt-3 grid gap-2">
              {s?.recent_orders.length === 0 && <p className="text-muted">No orders yet.</p>}
              {s?.recent_orders.map((o) => (
                <div key={o.id} className="flex flex-wrap items-center justify-between gap-2 border-t border-rule pt-2">
                  <div>
                    <p className="font-semibold">{o.id} · <span className="capitalize">{o.payload.profile.crop.split("(")[0]}</span> {kg(o.payload.profile.qty_kg)}</p>
                    <p className="text-[14px] text-muted">{o.payload.profile.location.name} → {short(o.payload.option.destination)}
                      {o.transport ? ` · token ${o.transport.id}${o.transport.transporter ? ` (${o.transport.transporter})` : ""}` : ""}</p>
                  </div>
                  <div className="flex items-center gap-2"><span className="text-[15px] font-semibold">
                    {rupees(o.payload.final?.net_earnings ?? o.payload.option.net)}</span><Pill s={o.status} /></div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </PortalShell>
  );
}
