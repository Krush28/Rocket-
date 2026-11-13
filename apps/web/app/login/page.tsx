"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { login, type Role } from "@/lib/ops";

const ROLES: { role: Role; title: string; desc: string; go: string }[] = [
  { role: "farmer", title: "Farmer", desc: "Talk to the AI: best mandi, sell or hold, transport, storage.", go: "/" },
  { role: "fpo", title: "FPO / Association head", desc: "Members' produce, pooled loads, sales pipeline.", go: "/fpo" },
  { role: "transporter", title: "Transporter", desc: "Accept loads by booking token, pick up, deliver.", go: "/transporter" },
  { role: "warehouse", title: "Warehouse operator", desc: "Confirm storage requests, manage capacity.", go: "/warehouse" },
  { role: "admin", title: "Admin", desc: "Platform overview and data jobs.", go: "/admin" },
];
const STATES = ["Maharashtra", "Uttar Pradesh", "Punjab", "Madhya Pradesh", "Karnataka", "Gujarat", "Rajasthan", "Haryana", "Telangana", "Andhra Pradesh",
  "Tamil Nadu", "Kerala", "West Bengal", "Bihar", "Odisha", "Goa"];

function Login() {
  const router = useRouter();
  const q = useSearchParams();
  const [role, setRole] = useState<Role>((q.get("role") as Role) || "transporter");
  const [phone, setPhone] = useState(""), [name, setName] = useState(""), [state, setState] = useState("Maharashtra");
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const target = ROLES.find((r) => r.role === role)!;

  async function go() {
    if (role === "farmer") return router.push("/");
    setBusy(true); setErr("");
    try { await login(phone, role, name, state); router.push(target.go); }
    catch (e) { setErr(e instanceof Error ? e.message : "Could not sign in"); }
    finally { setBusy(false); }
  }

  return (
    <main className="min-h-screen bg-forest text-cream">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <h1 className="font-display text-[32px] font-bold">Sign in to KRISHI-X</h1>
        <p className="mt-1 text-[16px] text-sage">One platform for the whole journey: farm → mandi, or farm → storage → mandi.</p>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {ROLES.map((r) => (
            <button key={r.role} onClick={() => setRole(r.role)}
              className={`rounded-2xl border-2 p-4 text-left ${role === r.role ? "border-mustard bg-leaf" : "border-moss bg-forest hover:bg-leaf"}`}>
              <p className="font-display text-[19px] font-bold">{r.title}</p>
              <p className="text-[14px] text-sage">{r.desc}</p>
            </button>
          ))}
        </div>
        {role !== "farmer" && (
          <form className="mt-6 grid gap-3 rounded-2xl bg-cream p-5 text-ink sm:grid-cols-3" onSubmit={(e) => { e.preventDefault(); void go(); }}>
            <label className="text-[14px] font-semibold">Mobile number
              <input required inputMode="tel" pattern="\+?\d{10,13}" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="98XXXXXXXX"
                className="mt-1 w-full rounded-xl border border-rule bg-white px-3 py-2.5 text-[16px]" /></label>
            <label className="text-[14px] font-semibold">Name / company
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder={role === "transporter" ? "Sharma Transport" : "Your name"}
                className="mt-1 w-full rounded-xl border border-rule bg-white px-3 py-2.5 text-[16px]" /></label>
            <label className="text-[14px] font-semibold">State
              <select value={state} onChange={(e) => setState(e.target.value)} className="mt-1 w-full rounded-xl border border-rule bg-white px-3 py-2.5 text-[16px]">
                {STATES.map((s) => <option key={s}>{s}</option>)}</select></label>
            <button disabled={busy} className="min-h-[48px] rounded-xl bg-forest text-[16px] font-bold text-cream sm:col-span-3">
              {busy ? "Signing in…" : `Continue as ${target.title}`}</button>
            {err && <p className="text-[14px] text-loss sm:col-span-3">{err}</p>}
          </form>
        )}
        {role === "farmer" && <button onClick={go} className="mt-6 min-h-[52px] w-full rounded-xl bg-mustard text-[18px] font-bold text-ink">Open the farmer assistant</button>}
      </div>
    </main>
  );
}

export default function Page() {
  return <Suspense><Login /></Suspense>;
}
