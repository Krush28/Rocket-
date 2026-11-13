"use client";

import { useState } from "react";
import { t, type Lang } from "@/lib/i18n";
import { LangSwitch, MicButton, ResetButton, SendForm } from "./Voice";

type Props = { lang: Lang; reply: string; chips: string[]; busy: boolean; listening: boolean; error: string; onMic: () => void; onSend: (t: string) => void; onLang: (l: Lang) => void; onReset: () => void };

// Always-visible voice bar on the results screen: speak or type a command; the agent answers and moves the screen.
export default function AgentBar({ lang, reply, chips, busy, listening, error, onMic, onSend, onLang, onReset }: Props) {
  const [typed, setTyped] = useState("");
  return (
    <div className="fixed inset-x-0 bottom-0 z-20 border-t border-moss bg-forest/95 text-cream backdrop-blur" lang={lang}>
      <div className="mx-auto flex max-w-3xl flex-col gap-2 px-4 py-3 sm:px-6">
        <div className="flex items-start justify-between gap-3">
          <p aria-live="polite" className="line-clamp-3 min-w-0 flex-1 text-[16px] leading-snug">{error || reply}</p>
          <div className="flex shrink-0 items-center gap-2">
            <ResetButton lang={lang} busy={busy} onReset={onReset} dark />
            <LangSwitch lang={lang} onLang={onLang} dark />
          </div>
        </div>
        {chips.length > 0 && (
          <div className="flex gap-2">
            {chips.map((c) => <button key={c} disabled={busy} onClick={() => onSend(c)} className="min-h-[48px] flex-1 rounded-full bg-mustard text-[17px] font-bold text-ink disabled:opacity-50">{c}</button>)}
          </div>
        )}
        <div className="flex items-center gap-2.5">
          <MicButton lang={lang} busy={busy} listening={listening} onMic={onMic} />
          <SendForm lang={lang} busy={busy} value={typed} setValue={setTyped} onSend={onSend} placeholder={t("ask", lang)} />
        </div>
      </div>
    </div>
  );
}
