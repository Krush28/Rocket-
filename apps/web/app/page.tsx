"use client";

import { useEffect, useRef, useState } from "react";
import AgentBar from "@/components/AgentBar";
import Landing from "@/components/Landing";
import Results from "@/components/Results";
import { agent, type AgentReply, type Crop, type Order, type Plan } from "@/lib/api";
import { isLang, type Lang } from "@/lib/i18n";
import { listen, speak, stopSpeaking } from "@/lib/speech";

const DEVICE = "kxDevice", LANG = "kxLang";
const SWITCH: Record<Lang, string> = { en: "switch to english", hi: "हिंदी में बोलो", mr: "मराठी मध्ये बोला" };

function store(k: string, v?: string) {
  try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch { /* private mode: memory only */ }
  return null;
}

// One voice agent for the whole app: intake (confirm first) -> plan -> spoken commands. The device id is how a farmer is remembered.
export default function Home() {
  const [sid, setSid] = useState("");
  const [lang, setLang] = useState<Lang>("en");
  const [reply, setReply] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [crops, setCrops] = useState<Crop[]>([]);
  const [chips, setChips] = useState<string[]>([]);
  const [awaiting, setAwaiting] = useState<string | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const picked = useRef(false), handsFree = useRef(false), stop = useRef<() => void>(), started = useRef(false), langRef = useRef<Lang>("en");

  function apply(r: AgentReply) {
    const l = isLang(r.lang) ? r.lang : langRef.current;
    langRef.current = l; setLang(l); setReply(r.reply); setCrops(r.crops ?? []); setChips(r.chips ?? []); setAwaiting(r.awaiting ?? null);
    let reset = false;
    for (const a of r.actions ?? []) {
      if (a.type === "plan") setPlan(a.plan);
      else if (a.type === "order") setOrder(a.order);
      else if (a.type === "lang" && isLang(a.value)) { picked.current = true; store(LANG, a.value); langRef.current = a.value; setLang(a.value); }
      else if (a.type === "reset") { reset = true; setPlan(null); setOrder(null); setCrops([]); }
      else if (a.type === "tab") setTimeout(() => document.getElementById(`sec-${a.value}`)?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    }
    return { l, reset };
  }

  async function send(text: string, id = sid) {
    setBusy(true); setError("");
    try {
      const r = await agent(id, text, picked.current ? langRef.current : undefined);
      const { l, reset } = apply(r);
      if (reset) return send("", id);
      if (handsFree.current && r.reply) {
        await speak(r.reply, l);
        if (handsFree.current) void mic(true); // hands-free loop: listen again right after speaking
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Could not reach KRISHI-X."); }
    finally { setBusy(false); }
  }

  async function mic(auto = false) {
    if (listening && !auto) { handsFree.current = false; stop.current?.(); stopSpeaking(); return; }
    handsFree.current = true; setListening(true); setError("");
    try {
      const said = (await listen(langRef.current, (s) => { stop.current = s; })).trim();
      setListening(false);
      if (said) await send(said); else handsFree.current = false; // silence ends the loop
    } catch (e) { handsFree.current = false; setListening(false); setError(e instanceof Error ? e.message : "Microphone error."); }
  }

  function chooseLang(l: Lang) {
    picked.current = true; store(LANG, l); langRef.current = l; setLang(l);
    void send(SWITCH[l]);
  }

  useEffect(() => {
    if (started.current) return; // StrictMode runs effects twice in dev
    started.current = true;
    let id = store(DEVICE);
    if (!id) { id = crypto.randomUUID(); store(DEVICE, id); }
    const saved = store(LANG), nav = navigator.language.slice(0, 2);
    const l: Lang = isLang(saved) ? saved : isLang(nav) ? nav : "en";
    picked.current = isLang(saved) || nav === "hi" || nav === "mr";
    langRef.current = l; setLang(l); setSid(id);
    void send("", id); // greeting, or "welcome back" with the remembered crops
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const voice = { lang, reply, chips, busy, listening, error, onMic: () => mic(), onSend: (t: string) => send(t), onLang: chooseLang };
  if (!plan) return <Landing {...voice} crops={crops} awaiting={awaiting} />;
  return (
    <>
      <Results plan={plan} lang={lang} order={order} crops={crops} onSay={(t) => send(t)} />
      <AgentBar {...voice} />
    </>
  );
}
