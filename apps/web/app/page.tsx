"use client";

import { useState } from "react";
import Assistant from "@/components/Assistant";
import Results from "@/components/Results";
import type { ChatReply } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

// Opens straight into the voice assistant; the results view appears only after the farmer confirms.
export default function Home() {
  const [done, setDone] = useState<{ reply: ChatReply; lang: Lang } | null>(null);
  if (done?.reply.plan) return <Results reply={done.reply} lang={done.lang} onRestart={() => setDone(null)} />;
  return <Assistant onConfirmed={(reply, lang) => setDone({ reply, lang })} />;
}
