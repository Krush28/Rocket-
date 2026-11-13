"use client";

import { useCallback, useEffect, useState } from "react";
import { btn, card, Pill, PortalShell, Stat } from "@/components/Portal";
import { bookAct, bookings, kg, myWarehouses, rupees, type Booking, type Warehouse } from "@/lib/ops";

export default function WarehousePortal() {
  const [rows, setRows] = useState<Booking[]>([]), [wh, setWh] = useState<Warehouse[]>([]);
  const [busy, setBusy] = useState(false), [err, setErr] = useState("");
  const load = useCallback(async () => {
    try { const [b, w] = await Promise.all([bookings(), myWarehouses()]); setRows(b); setWh(w); setErr(""); }
    catch (e) { setErr(e instanceof Error ? e.message : "offline"); }
  }, []);
  useEffect(() => { void load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);
  async function act(b: Booking, a: string) {
    setBusy(true);
    try { await bookAct(b.id, a); await load(); } catch (e) { setErr(e instanceof Error ? e.message : "failed"); } finally { setBusy(false); }
  }
  const pending = rows.filter((b) => b.status === "requested"), stored = rows.filter((b) => b.status === "confirmed");
  const cap = wh.reduce((s, w) => s + w.declared_capacity_qtl, 0), free = wh.reduce((s, w) => s + w.free_qtl, 0);
  return (
    <PortalShell role="warehouse" title="Warehouse">
      {() => (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="New requests" value={pending.length} /><Stat label="In storage" value={stored.length} />
            <Stat label="Capacity" value={`${Math.round(cap).toLocaleString("en-IN")} q`} /><Stat label="Free" value={`${Math.round(free).toLocaleString("en-IN")} q`} />
          </div>
          {err && <p className="mt-3 text-loss">{err}</p>}
          <h2 className="mt-6 font-display text-[22px] font-bold">Storage requests</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {rows.length === 0 && <p className="text-muted">No requests yet. Farmers&apos; bookings appear here automatically.</p>}
            {rows.map((b) => (
              <div key={b.id} className={card}>
                <div className="flex items-center justify-between gap-2"><p className="font-display text-[20px] font-bold">{b.id}</p><Pill s={b.status} /></div>
                <p className="mt-2 text-[17px]"><b>{b.crop_label}</b> · {kg(b.qty_kg)} · {b.days} days</p>
                <p className="mt-1 text-[15px] text-muted">{b.warehouse?.name} · {b.warehouse?.temp}</p>
                <p className="mt-1 text-[15px]">Estimated charge <b>{rupees(b.est_cost)}</b></p>
                {b.status === "requested" && (
                  <div className="mt-3 flex gap-2">
                    <button disabled={busy} onClick={() => act(b, "confirm")} className={`${btn} bg-forest text-cream`}>Confirm space</button>
                    <button disabled={busy} onClick={() => act(b, "reject")} className={`${btn} bg-[#ECEAE0]`}>Reject</button>
                  </div>
                )}
                {b.status === "confirmed" && <button disabled={busy} onClick={() => act(b, "release")} className={`${btn} mt-3 bg-[#ECEAE0]`}>Release stock</button>}
              </div>
            ))}
          </div>
          <h2 className="mt-6 font-display text-[22px] font-bold">My warehouses</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            {wh.map((w) => (
              <div key={w.id} className={card}>
                <p className="font-display text-[18px] font-bold">{w.name}</p>
                <p className="text-[14px] text-muted">{w.type} · {w.temp}</p>
                <p className="mt-2 text-[15px]">{Math.round(w.free_qtl).toLocaleString("en-IN")} of {Math.round(w.declared_capacity_qtl).toLocaleString("en-IN")} q free</p>
                <p className="text-[15px]">₹{w.rate_qtl_day}/q/day · min {w.min_days} days</p>
              </div>
            ))}
          </div>
        </>
      )}
    </PortalShell>
  );
}
