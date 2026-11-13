"use client";

import { useState } from "react";
import type { Crop } from "@/lib/api";
import { t, unitName, type Lang } from "@/lib/i18n";
import { LangSwitch, MicButton, ResetButton, SendForm } from "./Voice";

type Props = { lang: Lang; reply: string; chips: string[]; crops: Crop[]; awaiting: string | null; busy: boolean; listening: boolean; error: string;
  onMic: () => void; onSend: (t: string) => void; onLang: (l: Lang) => void; onReset: () => void };

// First screen = the voice agent only (Rocket's voice-first landing in the settlement-slip design).
export default function Landing({ lang, reply, chips, crops, awaiting, busy, listening, error, onMic, onSend, onLang, onReset }: Props) {
  const [typed, setTyped] = useState("");
  const chip = "rounded-full bg-leaf px-4 min-h-[48px] text-[16px] text-cream hover:bg-moss disabled:opacity-50";
  const confirm = awaiting === "confirm";
  return (
    <main className="min-h-screen bg-forest text-cream" lang={lang}>
      <div className="mx-auto flex min-h-screen max-w-xl flex-col px-4 pb-6 pt-6 sm:px-6">
        <header className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-mustard" aria-hidden>
              <svg width="22" height="22" viewBox="0 0 26 26" fill="none" stroke="#11221A" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 4v17M8 22h10M4 9h18" /><path d="M4 9l-2.5 6h5zM22 9l-2.5 6h5z" /></svg>
            </div>
            <span className="font-display text-[22px] font-extrabold tracking-tight">{lang === "en" ? "KRISHI-X" : "कृषि-एक्स"}</span>
          </div>
          <div className="flex items-center gap-2">
            {(crops.length > 0 || (awaiting && awaiting !== "crops")) && <ResetButton lang={lang} busy={busy} onReset={onReset} dark />}
            <LangSwitch lang={lang} onLang={onLang} dark />
          </div>
        </header>

        <h1 className="mt-8 font-display text-[32px] font-bold leading-tight tracking-tight sm:text-[36px]">{t("title", lang)}</h1>
        <p className="mt-2 text-[17px] text-sage">{t("sub", lang)}</p>

        <p aria-live="polite" className="mt-6 min-h-[3.5rem] rounded-3xl bg-leaf/60 p-4 text-[19px] leading-snug">{reply || "…"}</p>

        {crops.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2" aria-label={t("crops", lang)}>
            {crops.map((c) => <li key={c.crop} className="rounded-full bg-cream px-4 py-2 text-[16px] font-semibold text-ink">{c.label}{c.qty ? ` · ${c.qty} ${unitName(c.unit, lang)}` : ""}</li>)}
          </ul>
        )}

        {confirm && (
          <div className="mt-4 grid grid-cols-2 gap-3">
            <button disabled={busy} onClick={() => onSend(t("yesWord", lang))} className="min-h-[56px] rounded-full bg-mustard text-[18px] font-bold text-ink disabled:opacity-50">{t("yes", lang)}</button>
            <button disabled={busy} onClick={() => onSend(t("noWord", lang))} className="min-h-[56px] rounded-full bg-cream text-[18px] font-semibold text-ink disabled:opacity-50">{t("change", lang)}</button>
          </div>
        )}

        <div className="flex flex-1 flex-col items-center justify-center gap-3 py-8">
          <MicButton lang={lang} busy={busy} listening={listening} onMic={onMic} big />
          {error && <p role="alert" className="rounded-xl bg-note px-4 py-2 text-center text-[16px] text-ink">{error}</p>}
        </div>

        {(chips.length > 0 || !crops.length) && (
          <div className="mb-3 flex flex-wrap gap-2">
            {(chips.length ? chips : [t("ex1", lang), t("ex2", lang)]).map((e) => <button key={e} disabled={busy} onClick={() => onSend(e)} className={chip}>{e}</button>)}
          </div>
        )}
        <SendForm lang={lang} busy={busy} value={typed} setValue={setTyped} onSend={onSend} />
      </div>
    </main>
  );
}
