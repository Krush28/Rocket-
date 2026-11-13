"use client";

import { useCallback, useEffect, useState } from "react";
import { btn, card, Pill, PortalShell, Stat } from "@/components/Portal";
import { jobAct, jobs, kg, rupees, short, type Job } from "@/lib/ops";

const NEXT: Record<string, { action: string; label: string }> = {
  open: { action: "accept", label: "Accept load" }, accepted: { action: "pickup", label: "Mark picked up" }, picked_up: { action: "deliver", label: "Mark delivered" },
};

function Load({ j, onAct, busy }: { j: Job; onAct: (j: Job, a: string) => void; busy: boolean }) {
  const n = NEXT[j.status];
  return (
    <div className={card}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-display text-[20px] font-bold">Token {j.id}</p><Pill s={j.status} />
      </div>
      <p className="mt-2 text-[17px]"><b>{j.crop_label}</b> · {kg(j.qty_kg)}</p>
      <p className="mt-1 text-[15px] text-muted">{j.pickup.name} → {short(j.drop.name)}{j.distance_km ? ` · ${Math.round(j.distance_km)} km` : ""}</p>
      <p className="mt-1 text-[15px]">Estimated fare <b>{rupees(j.est_fare)}</b>{j.vehicle ? ` · ${j.vehicle}` : ""}</p>
      {j.pickup.lat != null && j.drop.lat != null && (
        <a className="mt-2 inline-block text-[14px] font-semibold text-leaf underline" target="_blank" rel="noreferrer"
          href={`https://www.google.com/maps/dir/${j.pickup.lat},${j.pickup.lon}/${j.drop.lat},${j.drop.lon}`}>Open route</a>
      )}
      <div className="mt-3 flex gap-2">
        {n && <button disabled={busy} onClick={() => onAct(j, n.action)} className={`${btn} bg-forest text-cream`}>{n.label}</button>}
        {j.status === "accepted" && <button disabled={busy} onClick={() => onAct(j, "release")} className={`${btn} bg-[#ECEAE0]`}>Release</button>}
      </div>
    </div>
  );
}

export default function Transporter() {
  const [open, setOpen] = useState<Job[]>([]), [mine, setMine] = useState<Job[]>([]);
  const [busy, setBusy] = useState(false), [err, setErr] = useState("");
  const load = useCallback(async () => {
    try { const [o, m] = await Promise.all([jobs("open"), jobs("mine")]); setOpen(o); setMine(m); setErr(""); }
    catch (e) { setErr(e instanceof Error ? e.message : "offline"); }
  }, []);
  useEffect(() => { void load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);
  async function act(j: Job, a: string) {
    setBusy(true);
    try { await jobAct(j.id, a); await load(); } catch (e) { setErr(e instanceof Error ? e.message : "failed"); } finally { setBusy(false); }
  }
  const active = mine.filter((j) => j.status !== "delivered" && j.status !== "cancelled");
  const done = mine.filter((j) => j.status === "delivered");
  return (
    <PortalShell role="transporter" title="Transporter">
      {() => (
        <>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Open loads" value={open.length} /><Stat label="My active" value={active.length} />
            <Stat label="Delivered" value={done.length} />
          </div>
          {err && <p className="mt-3 text-loss">{err}</p>}
          <h2 className="mt-6 font-display text-[22px] font-bold">My loads</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {active.length === 0 && <p className="text-muted">No active loads. Accept one below.</p>}
            {active.map((j) => <Load key={j.id} j={j} onAct={act} busy={busy} />)}
          </div>
          <h2 className="mt-6 font-display text-[22px] font-bold">Open loads near you</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {open.length === 0 && <p className="text-muted">No open loads right now. New ones appear here automatically.</p>}
            {open.map((j) => <Load key={j.id} j={j} onAct={act} busy={busy} />)}
          </div>
          {done.length > 0 && (
            <>
              <h2 className="mt-6 font-display text-[22px] font-bold">Delivered</h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">{done.slice(0, 6).map((j) => <Load key={j.id} j={j} onAct={act} busy={busy} />)}</div>
            </>
          )}
        </>
      )}
    </PortalShell>
  );
}
