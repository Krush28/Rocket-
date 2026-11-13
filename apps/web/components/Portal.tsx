"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { logout, notes, notesRead, session, type Note, type Role, type User } from "@/lib/ops";

// Shared frame for the role portals: header, live notification bell, sign-out. Redirects to /login if the role does not match.
export function PortalShell({ role, title, children }: { role: Role; title: string; children: (u: User) => ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    const s = session();
    if (!s || (s.user.role !== role && s.user.role !== "admin")) router.replace(`/login?role=${role}`);
    else setUser(s.user);
  }, [role, router]);
  if (!user) return <main className="min-h-screen bg-paper" />;
  return (
    <main className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-20 border-b border-moss bg-forest text-cream">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-mustard font-display font-extrabold text-ink">K</span>
            <span className="font-display text-[19px] font-bold">KRISHI-X <span className="font-normal text-sage">· {title}</span></span>
          </Link>
          <div className="flex items-center gap-2">
            <Bell dark />
            <span className="hidden text-[14px] text-sage sm:inline">{user.name || user.phone}</span>
            <button onClick={() => { logout(); router.replace("/login"); }} className="min-h-[40px] rounded-lg bg-leaf px-3 text-[14px] hover:bg-moss">Sign out</button>
          </div>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">{children(user)}</div>
    </main>
  );
}

// Notification bell: polls every 5 s; for the farmer app pass the device id.
export function Bell({ device, dark, onNew }: { device?: string; dark?: boolean; onNew?: (n: Note) => void }) {
  const [items, setItems] = useState<Note[]>([]);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let last = -1, live = true;
    const tick = async () => {
      try {
        const n = await notes(device);
        if (!live) return;
        if (last >= 0 && n[0] && n[0].id > last) onNew?.(n[0]);
        last = n[0]?.id ?? 0;
        setItems(n);
      } catch { /* offline: keep the last list */ }
    };
    void tick();
    const t = setInterval(tick, 5000);
    return () => { live = false; clearInterval(t); };
  }, [device, onNew]);
  const unread = items.filter((i) => !i.read).length;
  return (
    <div className="relative">
      <button aria-label="Notifications" onClick={() => { setOpen(!open); if (!open && unread) void notesRead(device).then(() => setItems(items.map((i) => ({ ...i, read: true })))); }}
        className={`relative grid h-10 w-10 place-items-center rounded-xl ${dark ? "bg-leaf text-cream hover:bg-moss" : "bg-[#ECEAE0] text-ink"}`}>
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></svg>
        {unread > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-mustard px-1 text-[11px] font-bold text-ink">{unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 top-12 z-30 max-h-[70vh] w-[min(360px,90vw)] overflow-auto rounded-2xl border border-rule bg-cream p-2 text-ink shadow-xl">
          {items.length === 0 && <p className="p-3 text-[14px] text-muted">No notifications yet.</p>}
          {items.map((n) => (
            <div key={n.id} className={`rounded-xl p-3 ${n.read ? "" : "bg-okbg"}`}>
              <p className="text-[15px] font-semibold">{n.title}</p>
              {n.body && <p className="text-[14px] text-muted">{n.body}</p>}
              {n.at && <p className="mt-1 text-[12px] text-muted">{new Date(n.at).toLocaleString()}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-2xl border border-rule bg-cream p-4">
      <p className="text-[12px] font-semibold uppercase tracking-widest text-muted">{label}</p>
      <p className="mt-1 font-display text-[26px] font-bold">{value}</p>
    </div>
  );
}

export function Pill({ s }: { s: string }) {
  const tone = /deliver|confirm|accept|sale_confirmed|released/.test(s) ? "bg-okbg text-[#1C5A43]" : /cancel|reject/.test(s) ? "bg-[#F6D5D0] text-loss" : "bg-note text-[#6B4A00]";
  return <span className={`rounded-full px-3 py-1 text-[13px] font-semibold ${tone}`}>{s.replace(/_/g, " ")}</span>;
}

export const card = "rounded-[22px] border border-rule bg-cream p-5";
export const btn = "min-h-[44px] rounded-xl px-4 text-[15px] font-semibold disabled:opacity-50";
