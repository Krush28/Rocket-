"use client";

import { useEffect, useState } from "react";
import { card, PortalShell, Stat } from "@/components/Portal";
import { adminOverview } from "@/lib/ops";

export default function Admin() {
  const [o, setO] = useState<Record<string, unknown> | null>(null), [err, setErr] = useState("");
  useEffect(() => {
    const load = () => adminOverview().then(setO).catch((e) => setErr(e.message));
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);
  const job = (o?.price_job || {}) as { pairs_done?: number; pairs_total?: number; updated?: string };
  const KEYS: [string, string][] = [["orders", "Sale orders"], ["transport_jobs", "Transport loads"], ["storage_bookings", "Storage bookings"],
    ["warehouses", "Warehouses"], ["users", "Registered users"], ["notifications", "Notifications sent"]];
  return (
    <PortalShell role="admin" title="Admin">
      {() => (
        <>
          {err && <p className="text-loss">{err}</p>}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {KEYS.map(([k, label]) => <Stat key={k} label={label} value={String(o?.[k] ?? "—")} />)}
          </div>
          <section className={`${card} mt-6`}>
            <h2 className="font-display text-[22px] font-bold">Live price import</h2>
            <p className="mt-1 text-[16px]">Mandi prices and history refresh every 6 hours (5 states × 25 crops), plus the official daily file.</p>
            <p className="mt-2 text-[16px]">Today: <b>{job.pairs_done ?? 0}</b> of {job.pairs_total ?? 0} state × crop pairs updated
              {job.updated ? ` · last ${new Date(job.updated).toLocaleTimeString()}` : ""}</p>
            <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-[#ECEAE0]">
              <div className="h-full bg-mint" style={{ width: `${Math.round(100 * (job.pairs_done ?? 0) / Math.max(1, job.pairs_total ?? 1))}%` }} />
            </div>
          </section>
        </>
      )}
    </PortalShell>
  );
}
