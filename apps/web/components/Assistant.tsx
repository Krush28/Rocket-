"use client";

import { useEffect, useRef, useState } from "react";
import { chat, type ChatReply, type Slots } from "@/lib/api";
import { cropName, t, type Lang } from "@/lib/i18n";
import { listen, speak } from "@/lib/speech";

type Msg = { who: "farmer" | "assistant"; text: string };
const newId = () => crypto.randomUUID(); // the session id is the only key to this farmer's profile: keep it unguessable
const EXAMPLES = ["200 quintal onion near Niphad", "1000 kg tomato near Ponda, Goa"];

export default function Assistant({ onConfirmed }: { onConfirmed: (r: ChatReply, lang: Lang) => void }) {
  const [sid] = useState(newId);
  const [lang, setLang] = useState<Lang>("en");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [slots, setSlots] = useState<Slots>({});
  const [state, setState] = useState("collecting");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const stopRef = useRef<() => void>();
  const voiceRef = useRef(false); // speak replies once the farmer has used the mic
  const picked = useRef(false); // true once the farmer taps a language button
  const endRef = useRef<HTMLDivElement>(null);

  async function send(text: string, l: Lang = lang) {
    setBusy(true); setError("");
    if (text) setMsgs((m) => [...m, { who: "farmer", text }]);
    try {
      const r = await chat(sid, text, picked.current ? l : undefined); // unpicked: the backend auto-detects the language
      setMsgs((m) => [...m, { who: "assistant", text: r.reply }]);
      setSlots(r.slots); setState(r.state);
      if (r.lang !== l && (r.lang === "hi" || r.lang === "mr" || r.lang === "en")) setLang(r.lang);
      if (voiceRef.current) speak(r.reply, (r.lang as Lang) || l);
      if (r.done && r.plan) onConfirmed(r, (r.lang as Lang) || l);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach KRISHI-X. Check your connection.");
    } finally { setBusy(false); }
  }

  const greeted = useRef(false);
  useEffect(() => { if (!greeted.current) { greeted.current = true; send(""); } }, []); // eslint-disable-line react-hooks/exhaustive-deps -- greet once (StrictMode runs effects twice in dev)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [msgs]);

  async function mic() {
    if (listening) { stopRef.current?.(); return; }
    setError(""); setListening(true); voiceRef.current = true;
    try {
      const said = await listen(lang, (stop) => { stopRef.current = stop; });
      if (said.trim()) await send(said.trim());
    } catch (e) { setError(e instanceof Error ? e.message : "Microphone error."); }
    finally { setListening(false); }
  }

  const last = [...msgs].reverse().find((m) => m.who === "assistant");
  const chip = "rounded-full bg-leaf px-4 min-h-[48px] text-[16px] text-cream hover:bg-moss disabled:opacity-50";

  return (
    <main className="min-h-screen bg-forest text-cream">
      <div className="mx-auto flex min-h-screen max-w-xl flex-col px-4 pb-6 pt-6 sm:px-6">
        <header className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-mustard" aria-hidden>
              <svg width="22" height="22" viewBox="0 0 26 26" fill="none" stroke="#11221A" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 4v17M8 22h10M4 9h18" /><path d="M4 9l-2.5 6h5zM22 9l-2.5 6h5z" /></svg>
            </div>
            <span className="font-display text-[22px] font-extrabold tracking-tight">KRISHI-X</span>
          </div>
          <div role="group" aria-label="Language" className="inline-flex rounded-xl bg-leaf p-1">
            {(["en", "hi", "mr"] as Lang[]).map((l) => (
              <button key={l} onClick={() => { picked.current = true; setLang(l); }} aria-pressed={lang === l}
                className={`min-h-[44px] rounded-lg px-3 text-[16px] ${lang === l ? "bg-cream font-semibold text-ink" : "text-cream"}`}>
                {l === "en" ? "EN" : l === "hi" ? "हिं" : "मरा"}
              </button>
            ))}
          </div>
        </header>

        <h1 className="mt-8 font-display text-[32px] font-bold leading-tight tracking-tight sm:text-[36px]">{t("title", lang)}</h1>
        <p className="mt-2 text-[17px] text-sage">{t("sub", lang)}</p>

        <section aria-live="polite" className="mt-6 rounded-3xl bg-leaf/60 p-4">
          <p className="text-[19px] leading-snug">{last?.text ?? "…"}</p>
          {msgs.length > 1 && (
            <details className="mt-3 text-[15px] text-sage">
              <summary className="cursor-pointer">{t("conversation", lang)} ({msgs.length})</summary>
              <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
                {msgs.map((m, i) => <li key={i} className={m.who === "farmer" ? "text-mint" : ""}>{m.who === "farmer" ? `${t("you", lang)}: ` : ""}{m.text}</li>)}
              </ul>
              <div ref={endRef} />
            </details>
          )}
        </section>

        <ProfileCard slots={slots} lang={lang} />

        {state === "confirming" ? (
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button disabled={busy} onClick={() => send(t("yesWord", lang))} className="min-h-[56px] rounded-full bg-mustard text-[18px] font-bold text-ink disabled:opacity-50">{t("yes", lang)}</button>
            <button disabled={busy} onClick={() => send(t("noWord", lang))} className="min-h-[56px] rounded-full bg-cream text-[18px] font-semibold text-ink disabled:opacity-50">{t("change", lang)}</button>
          </div>
        ) : null}

        <div className="flex flex-1 flex-col items-center justify-center gap-3 py-8">
          <button onClick={mic} disabled={busy && !listening} aria-label={listening ? t("listening", lang) : t("tap", lang)}
            className={`grid h-28 w-28 place-items-center rounded-full bg-mustard shadow-[0_0_0_12px_#2D6A52,0_0_0_26px_#1C5A43] transition disabled:opacity-60 sm:h-32 sm:w-32 ${listening ? "animate-pulse" : ""}`}>
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#11221A" strokeWidth="2" strokeLinecap="round" aria-hidden><rect x="9" y="3" width="6" height="12" rx="3" fill="#11221A" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
          </button>
          <div className="mt-4 text-[17px] font-semibold">{listening ? t("listening", lang) : busy ? "…" : t("tap", lang)}</div>
          {error && <p role="alert" className="rounded-xl bg-note px-4 py-2 text-center text-[16px] text-ink">{error}</p>}
        </div>

        {state === "collecting" && !slots.crop && (
          <div className="mb-3 flex flex-wrap gap-2">
            {EXAMPLES.map((e) => <button key={e} disabled={busy} onClick={() => send(e)} className={chip}>{e}</button>)}
          </div>
        )}
        <form className="flex gap-2.5" onSubmit={(e) => { e.preventDefault(); if (input.trim()) { send(input.trim()); setInput(""); } }}>
          <label htmlFor="msg" className="sr-only">{t("type", lang)}</label>
          <input id="msg" value={input} onChange={(e) => setInput(e.target.value)} placeholder={t("type", lang)} maxLength={2000} autoComplete="off"
            className="min-h-[56px] min-w-0 flex-1 rounded-full bg-cream px-5 text-[18px] text-ink placeholder:text-muted" />
          <button type="submit" disabled={busy || !input.trim()} aria-label={t("send", lang)} className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-mustard disabled:opacity-50">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#11221A" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12h14M13 6l6 6-6 6" /></svg>
          </button>
        </form>
      </div>
    </main>
  );
}

function ProfileCard({ slots, lang }: { slots: Slots; lang: Lang }) {
  if (!slots.crop && !slots.qty && !slots.location) return null;
  const yn = (v?: boolean) => (v === undefined ? "—" : v ? t("yesWord", lang) : t("noWord", lang));
  const rows: [string, string][] = [
    [t("crop", lang), slots.crop ? cropName(slots.crop, lang) : "—"],
    [t("qty", lang), slots.qty ? `${slots.qty.original_qty} ${slots.qty.original_unit} (${slots.qty.qty_kg.toLocaleString("en-IN")} kg)` : "—"],
    [t("place", lang), slots.location?.name ?? "—"],
    [t("ready", lang), yn(slots.ready)],
    [t("store", lang), yn(slots.can_store)],
  ];
  return (
    <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 rounded-3xl bg-cream p-4 text-ink sm:grid-cols-3">
      {rows.map(([k, v]) => (
        <div key={k} className="min-w-0"><dt className="text-[13px] uppercase tracking-wider text-muted">{k}</dt><dd className="truncate text-[17px] font-semibold capitalize">{v}</dd></div>
      ))}
    </dl>
  );
}
