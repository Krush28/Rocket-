"use client";

import { t, type Lang } from "@/lib/i18n";

export function LangSwitch({ lang, onLang, dark }: { lang: Lang; onLang: (l: Lang) => void; dark?: boolean }) {
  return (
    <div role="group" aria-label={t("langWord", lang)} className={`inline-flex rounded-xl p-1 ${dark ? "bg-leaf" : "bg-[#ECEAE0]"}`}>
      {(["en", "hi", "mr"] as Lang[]).map((l) => (
        <button key={l} onClick={() => l !== lang && onLang(l)} aria-pressed={lang === l} lang={l}
          className={`min-h-[44px] rounded-lg px-3 text-[16px] ${lang === l ? (dark ? "bg-cream font-semibold text-ink" : "bg-forest font-semibold text-cream") : dark ? "text-cream" : "text-ink"}`}>
          {l === "en" ? "EN" : l === "hi" ? "हिं" : "मरा"}
        </button>
      ))}
    </div>
  );
}

export function MicButton({ lang, busy, listening, onMic, big }: { lang: Lang; busy: boolean; listening: boolean; onMic: () => void; big?: boolean }) {
  const size = big ? "h-28 w-28 sm:h-32 sm:w-32 shadow-[0_0_0_12px_#2D6A52,0_0_0_26px_#1C5A43]" : "h-14 w-14 shrink-0";
  const label = listening ? t("listening", lang) : t("tap", lang);
  return (
    <>
      <button onClick={onMic} disabled={busy && !listening} aria-label={label}
        className={`grid ${size} place-items-center rounded-full bg-mustard transition disabled:opacity-60 ${listening ? "animate-pulse" : ""}`}>
        <svg width={big ? 52 : 26} height={big ? 52 : 26} viewBox="0 0 24 24" fill="none" stroke="#11221A" strokeWidth="2" strokeLinecap="round" aria-hidden>
          <rect x="9" y="3" width="6" height="12" rx="3" fill="#11221A" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
        </svg>
      </button>
      {big && <div className="mt-4 text-[17px] font-semibold">{busy && !listening ? "…" : label}</div>}
    </>
  );
}

export function SendForm({ lang, busy, value, setValue, onSend, placeholder }: { lang: Lang; busy: boolean; value: string; setValue: (v: string) => void;
  onSend: (t: string) => void; placeholder?: string }) {
  return (
    <form className="flex min-w-0 flex-1 gap-2.5" onSubmit={(e) => { e.preventDefault(); if (value.trim()) { onSend(value.trim()); setValue(""); } }}>
      <label htmlFor="msg" className="sr-only">{t("type", lang)}</label>
      <input id="msg" value={value} onChange={(e) => setValue(e.target.value)} placeholder={placeholder ?? t("type", lang)} maxLength={2000} autoComplete="off" lang={lang}
        className="min-h-[56px] min-w-0 flex-1 rounded-full bg-cream px-5 text-[18px] text-ink placeholder:text-muted" />
      <button type="submit" disabled={busy || !value.trim()} aria-label={t("send", lang)} className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-mustard disabled:opacity-50">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#11221A" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12h14M13 6l6 6-6 6" /></svg>
      </button>
    </form>
  );
}
