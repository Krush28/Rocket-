"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Area, ComposedChart, Line, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import AgentBar from "@/components/AgentBar";
import { agent, series, type AgentReply } from "@/lib/api";
import { dashboard, isSample, type CropCard, type Dash, type DashOrder } from "@/lib/dash";
import { cropName, isLang, statusName, unitName, type Lang } from "@/lib/i18n";
import Weather from "@/components/Weather";
import { farmerPart, isEchoOfRecent, listen, rememberReply, speak, stopSpeaking } from "@/lib/speech";

// ---------------------------------------------------------------- words (farmer language, short)
const W = {
  title: { en: "My farm dashboard", hi: "मेरा खेती डैशबोर्ड", mr: "माझा शेती डॅशबोर्ड" },
  back: { en: "Assistant", hi: "सहायक", mr: "सहाय्यक" },
  takeHome: { en: "You can take home about", hi: "आपके हाथ में लगभग", mr: "तुमच्या हातात सुमारे" },
  acrossCrops: { en: "from all your crops, after every cost", hi: "सभी फसलों से, सारे खर्च के बाद", mr: "सर्व पिकांतून, सर्व खर्चानंतर" },
  crops: { en: "Crops", hi: "फसलें", mr: "पिके" },
  tickets: { en: "Tickets", hi: "टिकट", mr: "तिकिटे" },
  sold: { en: "Already earned", hi: "कमाई हो चुकी", mr: "मिळालेली कमाई" },
  open: { en: "open", hi: "चालू", mr: "सुरू" },
  next: { en: "Next step", hi: "अगला कदम", mr: "पुढची पायरी" },
  home: { en: "Home", hi: "होम", mr: "मुख्य" },
  forecast: { en: "Forecast", hi: "भाव अनुमान", mr: "भाव अंदाज" },
  storage: { en: "Storage", hi: "भंडारण", mr: "साठवण" },
  transport: { en: "Transport", hi: "ढुलाई", mr: "वाहतूक" },
  chat: { en: "Chat", hi: "बातचीत", mr: "गप्पा" },
  alerts: { en: "Alerts", hi: "सूचनाएँ", mr: "सूचना" },
  sellNow: { en: "SELL NOW", hi: "अभी बेचें", mr: "आता विका" },
  hold: { en: "HOLD", hi: "रुकें", mr: "थांबा" },
  unsure: { en: "NOT SURE YET", hi: "अभी पक्का नहीं", mr: "अजून नक्की नाही" },
  bestPlace: { en: "Best place", hi: "सबसे अच्छी जगह", mr: "सर्वोत्तम ठिकाण" },
  keep: { en: "You keep", hi: "आपको बचेगा", mr: "तुम्हाला राहील" },
  sale: { en: "Sale", hi: "बिक्री", mr: "विक्री" },
  costs: { en: "Costs", hi: "खर्च", mr: "खर्च" },
  why: { en: "Why", hi: "क्यों", mr: "का" },
  sure: { en: "How sure", hi: "कितना भरोसा", mr: "किती खात्री" },
  others: { en: "Other places", hi: "दूसरी जगहें", mr: "इतर ठिकाणे" },
  perQtl: { en: "/quintal", hi: "/क्विंटल", mr: "/क्विंटल" },
  km: { en: "km", hi: "किमी", mr: "किमी" },
  up: { en: "Price may go UP", hi: "भाव बढ़ सकता है", mr: "भाव वाढू शकतो" },
  down: { en: "Price may go DOWN", hi: "भाव गिर सकता है", mr: "भाव घसरू शकतो" },
  flat: { en: "Price may stay about the same", hi: "भाव लगभग वैसा ही रह सकता है", mr: "भाव साधारण तसाच राहू शकतो" },
  inDays: { en: "in {n} days", hi: "{n} दिन में", mr: "{n} दिवसांत" },
  today: { en: "Today", hi: "आज", mr: "आज" },
  past: { en: "Past price", hi: "पिछला भाव", mr: "मागील भाव" },
  fcNote: { en: "Forecast from past prices, checked against simple baselines. Not a guarantee.", hi: "पिछले भावों से अनुमान, सरल तरीकों से जाँचा गया। गारंटी नहीं।", mr: "मागील भावांवरून अंदाज, साध्या पद्धतींशी तपासला. हमी नाही." },
  range: { en: "likely range", hi: "संभावित दायरा", mr: "संभाव्य पट्टा" },
  noFc: { en: "Not enough past prices for a reliable forecast. I will not guess.", hi: "भरोसेमंद अनुमान के लिए पुराने भाव कम हैं। मैं अंदाज़ा नहीं लगाऊँगा।", mr: "विश्वसनीय अंदाजासाठी जुने भाव पुरेसे नाहीत. मी अंदाज लावणार नाही." },
  noTickets: { en: "No ticket yet. Say \"create the order\" when you are ready to sell.", hi: "अभी कोई टिकट नहीं। बेचने को तैयार हों तो \"ऑर्डर बनाओ\" बोलिए।", mr: "अजून तिकीट नाही. विकायला तयार असाल तेव्हा \"ऑर्डर तयार करा\" म्हणा." },
  token: { en: "Truck token", hi: "ट्रक टोकन", mr: "ट्रक टोकन" },
  to: { en: "to", hi: "→", mr: "→" },
  driver: { en: "Transporter", hi: "ट्रांसपोर्टर", mr: "वाहतूकदार" },
  waiting: { en: "Waiting for a transporter to accept", hi: "ट्रांसपोर्टर के स्वीकार करने का इंतज़ार", mr: "वाहतूकदाराच्या स्वीकृतीची प्रतीक्षा" },
  call: { en: "Call", hi: "कॉल करें", mr: "कॉल करा" },
  notVerified: { en: "number given by the transporter, not verified", hi: "ट्रांसपोर्टर का दिया नंबर, जाँचा नहीं गया", mr: "वाहतूकदाराने दिलेला नंबर, तपासलेला नाही" },
  noPhone: { en: "Phone number appears here when a transporter accepts your load.", hi: "ट्रांसपोर्टर लोड स्वीकार करेगा तब फ़ोन नंबर यहाँ दिखेगा।", mr: "वाहतूकदार लोड स्वीकारल्यावर फोन नंबर इथे दिसेल." },
  fare: { en: "Fare (estimate)", hi: "किराया (अनुमान)", mr: "भाडे (अंदाज)" },
  earned: { en: "You earned", hi: "आपकी कमाई", mr: "तुमची कमाई" },
  booked: { en: "Booked", hi: "बुक किया", mr: "बुक केले" },
  notBooked: { en: "Not booked yet. Best store for you:", hi: "अभी बुक नहीं। आपके लिए सबसे अच्छा भंडार:", mr: "अजून बुक नाही. तुमच्यासाठी सर्वोत्तम साठवण:" },
  sayBook: { en: "Say \"book storage\" to send a request.", hi: "अनुरोध भेजने के लिए \"भंडारण बुक करो\" बोलिए।", mr: "विनंती पाठवण्यासाठी \"साठवण बुक करा\" म्हणा." },
  days: { en: "days", hi: "दिन", mr: "दिवस" },
  for7: { en: "for 7 days (estimate)", hi: "7 दिन के लिए (अनुमान)", mr: "7 दिवसांसाठी (अंदाज)" },
  operatorConfirms: { en: "The store owner must confirm space.", hi: "जगह की पुष्टि भंडार मालिक करेगा।", mr: "जागेची खात्री साठवण मालक करेल." },
  noStore: { en: "No suitable store found near your farm.", hi: "आपके खेत के पास सही भंडार नहीं मिला।", mr: "तुमच्या शेताजवळ योग्य साठवण मिळाली नाही." },
  fleets: { en: "Truck options to", hi: "ट्रक विकल्प:", mr: "ट्रक पर्याय:" },
  hours: { en: "h drive", hi: "घंटे का सफ़र", mr: "तासांचा प्रवास" },
  you: { en: "You", hi: "आप", mr: "तुम्ही" },
  noChat: { en: "Nothing said yet. Tap the mic below and ask anything.", hi: "अभी कोई बात नहीं हुई। नीचे माइक दबाकर कुछ भी पूछिए।", mr: "अजून काही बोलणे नाही. खालील माइक दाबून काहीही विचारा." },
  noAlerts: { en: "No alerts.", hi: "कोई सूचना नहीं।", mr: "सूचना नाहीत." },
  sample: { en: "Sample", hi: "नमूना", mr: "नमुना" },
  sampleData: { en: "Sample data: some places and fleets are examples, not real businesses.", hi: "नमूना डेटा: कुछ जगहें और ट्रक उदाहरण हैं, असली कंपनियाँ नहीं।", mr: "नमुना डेटा: काही ठिकाणे व ट्रक उदाहरणे आहेत, खऱ्या कंपन्या नाहीत." },
  live: { en: "Live prices", hi: "आज के भाव", mr: "आजचे भाव" },
  demoPrices: { en: "Sample prices", hi: "नमूना भाव", mr: "नमुना भाव" },
  empty: { en: "Tell the assistant your crops first. Your dashboard fills up as you go.", hi: "पहले सहायक को अपनी फसलें बताइए। डैशबोर्ड अपने आप भरता जाएगा।", mr: "आधी सहाय्यकाला तुमची पिके सांगा. डॅशबोर्ड आपोआप भरत जाईल." },
  start: { en: "Start talking", hi: "बात शुरू करें", mr: "बोलायला सुरू करा" },
  loading: { en: "Loading your dashboard…", hi: "डैशबोर्ड खुल रहा है…", mr: "डॅशबोर्ड उघडत आहे…" },
  tryVoice: { en: "Try saying", hi: "बोलकर देखें", mr: "बोलून पहा" },
  estimates: { en: "All money is an estimate from today's prices and listed costs. Not a guarantee.", hi: "सारी रकम आज के भाव और खर्च पर आधारित अनुमान है। गारंटी नहीं।", mr: "सर्व रक्कम आजच्या भाव व खर्चावर आधारित अंदाज आहे. हमी नाही." },
} as const;
type WK = keyof typeof W;
const w = (k: WK, l: Lang, n?: number | string) => (W[k][l] as string).replace("{n}", String(n ?? ""));

const SAY: Record<string, Record<Lang, string>> = {
  tickets: { en: "show my tickets", hi: "मेरे टिकट दिखाओ", mr: "माझी तिकिटे दाखवा" },
  phone: { en: "transporter phone number", hi: "ट्रांसपोर्टर का नंबर दिखाओ", mr: "वाहतूकदाराचा नंबर दाखवा" },
  hold: { en: "should I sell now or hold?", hi: "अभी बेचूँ या रुकूँ?", mr: "आता विकू का थांबू?" },
  forecast: { en: "will the price go up?", hi: "भाव बढ़ेगा क्या?", mr: "भाव वाढेल का?" },
  order: { en: "create the order", hi: "ऑर्डर बनाओ", mr: "ऑर्डर तयार करा" },
  storage: { en: "book storage", hi: "भंडारण बुक करो", mr: "साठवण बुक करा" },
};
const SECTIONS = ["home", "crops", "forecast", "tickets", "storage", "transport", "chat", "alerts"] as const;
type Section = (typeof SECTIONS)[number];
const TAB_TO_SECTION: Record<string, Section> = { compare: "crops", forecast: "forecast", logistics: "storage", order: "tickets" };
const STEPS = ["created", "transport_requested", "transport_accepted", "in_transit", "delivered", "sale_confirmed"];

const inr = (n: number | null | undefined) => (n == null ? "—" : "₹" + Math.round(n).toLocaleString("en-IN"));
const place = (k?: string | null) => (k || "").split(", ")[0];
const qtyText = (c: { original_qty: number; original_unit: string; crop: string }, l: Lang) => `${c.original_qty} ${unitName(c.original_unit, l)} ${cropName(c.crop, l)}`;
const clock = (iso?: string | null) => { try { return iso ? new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : ""; } catch { return ""; } };

// ---------------------------------------------------------------- small pieces
function Icon({ d, className = "h-6 w-6" }: { d: string; className?: string }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden><path d={d} /></svg>;
}
const ICON: Record<Section, string> = {
  home: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
  crops: "M12 21V10M12 10c0-4 3-7 7-7 0 4-3 7-7 7zM12 13c0-3-2.5-5.5-6-5.5 0 3 2.5 5.5 6 5.5z",
  forecast: "M3 17l5-5 4 3 8-8M15 7h5v5",
  tickets: "M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4zM10 5v14",
  storage: "M3 9l9-5 9 5v11H3zM7 20v-7h10v7M7 16h10",
  transport: "M3 6h11v10H3zM14 10h4l3 3v3h-7M7 19a2 2 0 1 0 0-.01M17 19a2 2 0 1 0 0-.01",
  chat: "M4 5h16v11H8l-4 4z",
  alerts: "M6 16V11a6 6 0 1 1 12 0v5l2 2H4zM10 21h4",
};

function Badge({ children, tone = "note" }: { children: ReactNode; tone?: "note" | "ok" | "loss" | "dark" }) {
  const c = { note: "bg-note text-[#6B4A00]", ok: "bg-okbg text-forest", loss: "bg-[#F6DAD6] text-loss", dark: "bg-white/15 text-cream" }[tone];
  return <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-[12px] font-semibold ${c}`}>{children}</span>;
}

function Card({ id, title, icon, children, action }: { id: Section; title: string; icon: Section; children: ReactNode; action?: ReactNode }) {
  return (
    <section id={`sec-${id}`} className="scroll-mt-24 rounded-[28px] border border-rule bg-cream p-5 shadow-[0_1px_0_#DAD7C6] sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2.5 font-display text-[22px] font-bold tracking-tight">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-forest text-mustard"><Icon d={ICON[icon]} className="h-5 w-5" /></span>{title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function SayChip({ text, onSay }: { text: string; onSay: (t: string) => void }) {
  return (
    <button onClick={() => onSay(text)} className="inline-flex min-h-[40px] items-center gap-1.5 rounded-full border border-rule bg-white px-3.5 text-[14px] font-semibold text-forest hover:border-forest">
      <Icon d="M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3" className="h-4 w-4" />“{text}”
    </button>
  );
}

function Verdict({ action, l }: { action?: string; l: Lang }) {
  const a = (action || "").toUpperCase();
  const [txt, cls] = a.startsWith("SELL") ? [w("sellNow", l), "bg-mint text-forest"] : a.startsWith("HOLD") ? [w("hold", l), "bg-mustard text-ink"] : [w("unsure", l), "bg-white/20 text-cream"];
  return <span className={`inline-flex rounded-2xl px-4 py-2 font-display text-[22px] font-extrabold tracking-tight ${cls}`}>{txt}</span>;
}

function Meter({ score }: { score: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="h-3 flex-1 overflow-hidden rounded-full bg-rule"><div className="h-full rounded-full bg-gradient-to-r from-mustard to-moss" style={{ width: `${pct}%` }} /></div>
      <span className="font-display text-[18px] font-bold tabular-nums">{pct}%</span>
    </div>
  );
}

// ---------------------------------------------------------------- sections
function CropBlock({ c, l, onSay }: { c: CropCard; l: Lang; onSay: (t: string) => void }) {
  const b = c.best;
  const max = Math.max(...c.options.map((o) => o.net), b?.net ?? 0, 1);
  return (
    <article className="overflow-hidden rounded-[24px] border border-rule bg-white">
      <div className="bg-forest p-5 text-cream">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[14px] font-semibold uppercase tracking-widest text-sage">{qtyText(c, l)}</p>
          <Verdict action={c.decision?.action} l={l} />
        </div>
        {b ? (
          <>
            <p className="mt-4 text-[14px] text-sage">{w("bestPlace", l)}</p>
            <h3 className="font-display text-[26px] font-bold leading-tight">{place(b.destination)}</h3>
            <p className="mt-1 text-[15px] text-sage">{b.label}</p>
            <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-[14px] text-sage">{w("keep", l)}</p>
                <p className="font-display text-[44px] font-extrabold leading-none tracking-tighter text-white">{inr(b.net)}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone="dark">{inr(b.price)}{w("perQtl", l)}</Badge>
                <Badge tone="dark">{Math.round(b.distance_km)} {w("km", l)}</Badge>
                {isSample(b.verification) && <Badge>{w("sample", l)}</Badge>}
              </div>
            </div>
            <div className="mt-4">
              <div className="flex h-3 overflow-hidden rounded-full bg-white/15">
                <div className="bg-mint" style={{ width: `${(b.net / Math.max(b.gross_revenue, 1)) * 100}%` }} />
                <div className="bg-[#E5866F]" style={{ width: `${(b.total_deductions / Math.max(b.gross_revenue, 1)) * 100}%` }} />
              </div>
              <div className="mt-1.5 flex justify-between text-[13px] text-sage">
                <span>{w("sale", l)} {inr(b.gross_revenue)}</span><span>{w("costs", l)} −{inr(b.total_deductions)}</span>
              </div>
            </div>
          </>
        ) : <p className="mt-4 text-[17px] text-sage">{c.no_best_reason}</p>}
      </div>
      <div className="grid gap-5 p-5">
        <div>
          <p className="text-[13px] font-semibold uppercase tracking-widest text-muted">{w("why", l)}</p>
          <p className="mt-1 text-[16px] leading-snug">{c.decision?.reason}</p>
          {!!c.decision?.factors?.length && <ul className="mt-2 grid gap-1 text-[14px] text-muted">{c.decision.factors.slice(0, 3).map((f) => <li key={f} className="flex gap-2"><span className="text-moss">●</span>{f}</li>)}</ul>}
          {c.confidence && (
            <div className="mt-4">
              <p className="mb-1.5 text-[13px] font-semibold uppercase tracking-widest text-muted">{w("sure", l)}</p>
              <Meter score={c.confidence.score} />
            </div>
          )}
        </div>
        <div>
          <p className="text-[13px] font-semibold uppercase tracking-widest text-muted">{w("others", l)}</p>
          <ol className="mt-2 grid gap-2">
            {c.options.map((o, i) => (
              <li key={o.label + i}>
                <div className="flex items-baseline justify-between gap-2 text-[15px]">
                  <span className="min-w-0 truncate"><b className="mr-1.5 font-display">{i + 1}</b>{place(o.destination)}</span>
                  <b className="tabular-nums">{inr(o.net)}</b>
                </div>
                <div className="mt-1 h-2 rounded-full bg-paper"><div className={`h-full rounded-full ${i === 0 ? "bg-moss" : "bg-sage"}`} style={{ width: `${(o.net / max) * 100}%` }} /></div>
              </li>
            ))}
          </ol>
          <div className="mt-4 flex flex-wrap gap-2"><SayChip text={SAY.hold[l]} onSay={onSay} /></div>
        </div>
      </div>
    </article>
  );
}

function ForecastBlock({ c, l }: { c: CropCard; l: Lang }) {
  const f = c.forecast;
  const [hist, setHist] = useState<[string, number][]>([]);
  const dest = c.best?.destination;
  useEffect(() => { if (dest) series(c.crop, dest).then((s) => setHist(s?.history.slice(-30) ?? [])).catch(() => setHist([])); }, [c.crop, dest]);
  if (!f) return <div className="rounded-[22px] bg-white p-5"><p className="font-display text-[19px] font-bold">{cropName(c.crop, l)}</p><p className="mt-1 text-[16px] text-muted">{w("noFc", l)}</p></div>;
  const last = f.points[f.points.length - 1];
  const ch = f.change_pct ?? 0;
  const dir: WK = ch > 1 ? "up" : ch < -1 ? "down" : "flat";
  const rows = [
    ...hist.map(([d, v]) => ({ d: d.slice(5), v })),
    { d: w("today", l), v: f.current, p: f.current, band: [f.current, f.current] as [number, number] },
    ...f.points.map((p) => ({ d: p.date.slice(5), p: p.predicted, band: [p.lo, p.hi] as [number, number] })),
  ];
  return (
    <div className="rounded-[22px] bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[14px] font-semibold uppercase tracking-widest text-muted">{cropName(c.crop, l)} · {place(f.mandi)}</p>
          <p className={`mt-1 flex items-center gap-2 font-display text-[24px] font-extrabold tracking-tight ${dir === "up" ? "text-moss" : dir === "down" ? "text-loss" : "text-ink"}`}>
            <Icon d={dir === "up" ? "M12 19V5M5 12l7-7 7 7" : dir === "down" ? "M12 5v14M5 12l7 7 7-7" : "M5 12h14"} className="h-7 w-7" />
            {w(dir, l)}
          </p>
          <p className="text-[16px] text-muted">{inr(f.current)} → <b className="text-ink">{inr(last.predicted)}</b>{w("perQtl", l)} {w("inDays", l, last.days)} {ch ? `(${ch > 0 ? "+" : ""}${ch}%)` : ""}</p>
        </div>
        <Badge tone="ok">{w("range", l)}: {inr(last.lo)}–{inr(last.hi)}</Badge>
      </div>
      <div className="mt-4 h-56 w-full" aria-label={`${w("forecast", l)} ${cropName(c.crop, l)}`}>
        <ResponsiveContainer>
          <ComposedChart data={rows} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
            <defs><linearGradient id={`g-${c.crop}`} x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#F2B01E" stopOpacity={0.45} /><stop offset="100%" stopColor="#F2B01E" stopOpacity={0.12} /></linearGradient></defs>
            <XAxis dataKey="d" tick={{ fontSize: 12, fill: "#55635B" }} minTickGap={28} tickLine={false} axisLine={{ stroke: "#DAD7C6" }} />
            <YAxis tick={{ fontSize: 12, fill: "#55635B" }} width={52} domain={["auto", "auto"]} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${v}`} />
            <Tooltip formatter={(v) => (Array.isArray(v) ? `${inr(Number(v[0]))} – ${inr(Number(v[1]))}` : inr(Number(v)))} contentStyle={{ borderRadius: 14, border: "1px solid #DAD7C6" }} />
            <Area dataKey="band" stroke="none" fill={`url(#g-${c.crop})`} isAnimationActive={false} name={w("range", l)} />
            <Line dataKey="v" stroke="#0F3D2E" strokeWidth={2.5} dot={false} isAnimationActive={false} name={w("past", l)} />
            <Line dataKey="p" stroke="#C88A00" strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 3, fill: "#C88A00" }} isAnimationActive={false} name={w("forecast", l)} />
            <ReferenceDot x={w("today", l)} y={f.current} r={6} fill="#0F3D2E" stroke="#fff" strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-[13px] text-muted">{w("fcNote", l)}</p>
    </div>
  );
}

function Ticket({ o, l, onSay }: { o: DashOrder; l: Lang; onSay: (t: string) => void }) {
  const idx = STEPS.indexOf(o.status);
  const tr = o.transport;
  const opt = o.payload.option;
  const prof = o.payload.profile as unknown as { crop: string; qty_kg: number; original_qty?: number; original_unit?: string };
  const final = o.payload.final;
  const cancelled = o.status === "cancelled";
  return (
    <article className="relative overflow-hidden rounded-[24px] bg-white shadow-[0_2px_0_#DAD7C6]">
      <div className="flex flex-col sm:flex-row">
        <div className="min-w-0 flex-1 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-display text-[20px] font-extrabold tracking-tight">{o.id}</span>
            <Badge tone={cancelled ? "loss" : o.status === "sale_confirmed" ? "ok" : "note"}>{statusName(o.status, l)}</Badge>
            {isSample((opt as { verification?: string }).verification) && <Badge>{w("sample", l)}</Badge>}
          </div>
          <p className="mt-2 text-[17px]"><b>{prof.original_qty ? `${prof.original_qty} ${unitName(prof.original_unit || "", l)}` : `${Math.round(prof.qty_kg)} kg`} {cropName(prof.crop, l)}</b> {w("to", l)} <b>{place(opt.destination)}</b></p>
          <p className="text-[15px] text-muted">{opt.label} · {w("keep", l)} {inr(opt.net)}</p>
          {final && <p className="mt-2 rounded-xl bg-okbg px-3 py-2 text-[16px] text-forest">{w("earned", l)} <b className="font-display text-[20px]">{inr(final.net_earnings)}</b></p>}
          {!cancelled && (
            <ol className="mt-4 grid grid-cols-6 gap-1" aria-label="progress">
              {STEPS.map((s, i) => (
                <li key={s} className="flex flex-col items-center gap-1 text-center">
                  <span className={`grid h-7 w-7 place-items-center rounded-full text-[12px] font-bold ${i <= idx ? "bg-moss text-white" : "bg-paper text-muted"} ${i === idx ? "ring-4 ring-mustard/50" : ""}`}>{i < idx ? "✓" : i + 1}</span>
                  <span className={`hidden text-[11px] leading-tight sm:block ${i === idx ? "font-semibold text-ink" : "text-muted"}`}>{statusName(s, l)}</span>
                </li>
              ))}
            </ol>
          )}
          {!cancelled && idx >= 0 && <p className="mt-2 text-[14px] font-semibold text-moss sm:hidden">{idx + 1}/6 · {statusName(o.status, l)}</p>}
        </div>
        <div className="relative shrink-0 border-t-2 border-dashed border-rule bg-paper p-4 sm:w-[38%] sm:max-w-[240px] sm:border-l-2 sm:border-t-0">
          <span className="absolute -left-3 -top-3 h-6 w-6 rounded-full bg-cream" /><span className="absolute -right-3 -top-3 h-6 w-6 rounded-full bg-cream sm:-bottom-3 sm:-left-3 sm:right-auto sm:top-auto" />
          <p className="text-[12px] font-semibold uppercase tracking-widest text-muted">{w("token", l)}</p>
          <p className="font-display text-[22px] font-extrabold tracking-tight">{tr?.id ?? "—"}</p>
          {tr?.est_fare != null && <p className="mt-2 text-[13px] text-muted">{w("fare", l)}<br /><b className="text-[16px] text-ink">{inr(tr.est_fare)}</b></p>}
          <p className="mt-2 text-[13px] text-muted">{w("driver", l)}</p>
          <p className="text-[15px] font-semibold">{tr?.transporter || (tr ? w("waiting", l) : "—")}</p>
          {o.contact ? (
            <>
              <a href={`tel:${o.contact.phone}`} className="mt-2 inline-flex min-h-[48px] max-w-full flex-wrap items-center gap-2 rounded-full bg-forest px-4 text-[15px] font-bold text-cream">
                <Icon d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" className="h-4 w-4" />{w("call", l)} {o.contact.phone}
              </a>
              <p className="mt-1 text-[11px] text-muted">{w("notVerified", l)}</p>
            </>
          ) : tr && !cancelled ? <p className="mt-2 text-[12px] text-muted">{w("noPhone", l)}</p> : null}
        </div>
      </div>
      {o.status === "delivered" && <div className="border-t border-rule px-5 py-3"><SayChip text={l === "en" ? "I sold at 2100" : l === "hi" ? "2100 में बेचा" : "2100 ला विकले"} onSay={onSay} /></div>}
    </article>
  );
}

// ---------------------------------------------------------------- page
function DashboardPage() {
  const q = useSearchParams(), router = useRouter();
  const [sid, setSid] = useState("");
  const [lang, setLang] = useState<Lang>("en");
  const [d, setD] = useState<Dash | null>(null);
  const [err, setErr] = useState("");
  const [reply, setReply] = useState("");
  const [ai, setAi] = useState("");
  const [chips, setChips] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [active, setActive] = useState<Section>("home");
  const langRef = useRef<Lang>("en"), handsFree = useRef(false), stop = useRef<() => void>();

  const load = useCallback((id: string, l: Lang) => dashboard(id, l).then((x) => { setD(x); setErr(""); }).catch((e) => setErr(e instanceof Error ? e.message : "Error")), []);
  const go = useCallback((s: string) => {
    const sec = (SECTIONS as readonly string[]).includes(s) ? (s as Section) : "home";
    setActive(sec);
    setTimeout(() => document.getElementById(`sec-${sec}`)?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
  }, []);

  useEffect(() => {
    let id = "", l: Lang = "en";
    try { id = localStorage.getItem("kxDevice") || ""; const s = localStorage.getItem("kxLang"); l = isLang(q.get("lang")) ? (q.get("lang") as Lang) : isLang(s) ? s : "en"; } catch { /* private mode */ }
    if (!id) { id = crypto.randomUUID(); try { localStorage.setItem("kxDevice", id); } catch { /* memory only */ } }
    langRef.current = l; setLang(l); setSid(id);
    void load(id, l).then(() => { const s = q.get("section"); if (s) go(s); });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {  // tickets move when the transporter or store owner acts: keep the page fresh
    if (!sid) return;
    const t = setInterval(() => { void load(sid, langRef.current); }, 8000);
    return () => clearInterval(t);
  }, [sid, load]);

  function apply(r: AgentReply) {
    const l = isLang(r.lang) ? r.lang : langRef.current;
    langRef.current = l; setLang(l); setReply(r.reply); setAi(r.ai ?? ""); setChips(r.chips ?? []);
    let refresh = false;
    for (const a of r.actions ?? []) {
      if (a.type === "nav" && a.value === "dashboard") go(a.section || "home");
      else if (a.type === "nav") router.push(`/${a.value}?${new URLSearchParams({ state: a.state || "", lang: l, ...(a.cat ? { cat: a.cat } : {}), ...(a.q ? { q: a.q } : {}) })}`);
      else if (a.type === "tab") go(TAB_TO_SECTION[a.value] || "home");
      else if (a.type === "reset") { router.push("/"); return l; }
      else if (a.type === "lang" && isLang(a.value)) { try { localStorage.setItem("kxLang", a.value); } catch { /* ok */ } refresh = true; }
      else refresh = true; // plan / order / storage changed
    }
    if (refresh || l !== lang) void load(sid, l);
    return l;
  }

  async function send(text: string) {
    if (!sid) return;
    setBusy(true);
    try {
      const r = await agent(sid, text, langRef.current);
      const l = apply(r);
      rememberReply(r.reply || "");
      void load(sid, l);
      if (handsFree.current && r.reply) { await speak(r.reply, l); if (handsFree.current) void mic(true); }
    } catch (e) { setErr(e instanceof Error ? e.message : "Could not reach KRISHI-X."); }
    finally { setBusy(false); }
  }

  const echoes = useRef(0);
  async function mic(auto = false) {
    if (listening && !auto) { handsFree.current = false; stop.current?.(); stopSpeaking(); return; }
    handsFree.current = true; setListening(true);
    try {
      const said = (await listen(langRef.current, (s) => { stop.current = s; })).trim();
      setListening(false);
      const mine = said ? farmerPart(said) : null;
      if (mine) { echoes.current = 0; await send(mine); return; } // our echoed question + the farmer's answer: send only the answer
      if (said && isEchoOfRecent(said)) {  // our own voice: never act on it; two in a row -> stop and wait for a tap
        echoes.current += 1;
        if (echoes.current >= 2) { handsFree.current = false; echoes.current = 0; return; }
        void mic(true); return;
      }
      echoes.current = 0;
      if (said) await send(said); else handsFree.current = false;
    } catch (e) { handsFree.current = false; setListening(false); setErr(e instanceof Error ? e.message : "Microphone error."); }
  }

  const l = lang;
  const sample = !!d && (d.data_mode !== "LIVE" || d.crops.some((c) => isSample(c.best?.verification) || isSample(c.storage_suggestion?.verification)));
  const nextStep = (() => {
    if (!d?.farmer) return null;
    const open = d.orders.find((o) => !["sale_confirmed", "cancelled"].includes(o.status));
    if (open) return `${open.id}: ${statusName(open.status, l)}`;
    const c = d.crops[0];
    return c?.decision?.action ? `${cropName(c.crop, l)}: ${c.decision.action.startsWith("HOLD") ? w("hold", l) : c.decision.action.startsWith("SELL") ? w("sellNow", l) : w("unsure", l)}` : null;
  })();

  return (
    <main className="min-h-screen bg-paper pb-48 text-ink" lang={l}>
      {/* header + hero */}
      <header className="bg-forest text-cream">
        <div className="mx-auto max-w-6xl px-4 pb-8 pt-5 sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <Link href={`/?lang=${l}`} className="inline-flex min-h-[44px] items-center gap-2 rounded-full bg-white/10 px-4 text-[15px] font-semibold hover:bg-white/20">
              <Icon d="M15 18l-6-6 6-6" className="h-5 w-5" />{w("back", l)}
            </Link>
            <div className="flex items-center gap-2">
              {d?.data_mode && <Badge tone={d.data_mode === "LIVE" ? "ok" : "note"}><span className={`h-2 w-2 rounded-full ${d.data_mode === "LIVE" ? "bg-[#2E7D4F]" : "bg-mustard"}`} />{d.data_mode === "LIVE" ? w("live", l) : w("demoPrices", l)}</Badge>}
              <div className="flex overflow-hidden rounded-full bg-white/10 text-[14px] font-semibold">
                {(["en", "hi", "mr"] as Lang[]).map((x) => (
                  <button key={x} aria-pressed={x === l} onClick={() => { void send({ en: "switch to english", hi: "हिंदी में बोलो", mr: "मराठी मध्ये बोला" }[x]); }}
                    className={`min-h-[40px] px-3 ${x === l ? "bg-mustard text-ink" : ""}`}>{{ en: "EN", hi: "हिं", mr: "मरा" }[x]}</button>
                ))}
              </div>
            </div>
          </div>
          <p className="mt-6 text-[14px] font-semibold uppercase tracking-[0.2em] text-sage">{w("title", l)}{d?.farmer ? ` · ${place(d.farmer.location.name)}` : ""}</p>
          {d?.farmer ? (
            <div className="mt-2 grid gap-6 lg:grid-cols-[1.3fr_1fr] lg:items-end">
              <div>
                <p className="text-[17px] text-sage">{w("takeHome", l)}</p>
                <p className="font-display text-[56px] font-extrabold leading-[0.95] tracking-tighter text-white sm:text-[76px]">{inr(d.totals.expected_net)}</p>
                <p className="mt-1 text-[15px] text-sage">{w("acrossCrops", l)}</p>
                {nextStep && <p className="mt-4 inline-flex items-center gap-2 rounded-2xl bg-mustard px-4 py-2.5 text-[16px] font-bold text-ink"><Icon d="M5 12h14M13 6l6 6-6 6" className="h-5 w-5" />{w("next", l)}: {nextStep}</p>}
              </div>
              <div className="grid grid-cols-3 gap-2.5">
                {[[w("crops", l), String(d.farmer.crops.length), d.farmer.crops.map((c) => cropName(c.crop, l)).join(", ")],
                  [w("tickets", l), String(d.orders.length), `${d.totals.open_tickets} ${w("open", l)}`],
                  [w("sold", l), inr(d.totals.sold_net), ""]].map(([a, b, c]) => (
                  <div key={a} className="rounded-[20px] bg-white/10 p-3.5">
                    <p className="text-[12px] font-semibold uppercase tracking-widest text-sage">{a}</p>
                    <p className="mt-1 font-display text-[26px] font-extrabold leading-none tabular-nums">{b}</p>
                    {c && <p className="mt-1 truncate text-[12px] text-sage">{c}</p>}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-3">
              <p className="max-w-xl font-display text-[30px] font-bold leading-tight">{d ? w("empty", l) : w("loading", l)}</p>
              {d && <Link href={`/?lang=${l}`} className="mt-4 inline-flex min-h-[52px] items-center rounded-full bg-mustard px-6 text-[17px] font-bold text-ink">{w("start", l)}</Link>}
            </div>
          )}
        </div>
      </header>

      {/* section bar: also what the farmer can say */}
      <nav className="sticky top-0 z-10 border-b border-rule bg-paper/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl gap-2 overflow-x-auto px-4 py-2.5 sm:px-6">
          {SECTIONS.map((s) => (
            <button key={s} onClick={() => go(s)} aria-current={active === s}
              className={`inline-flex min-h-[44px] shrink-0 items-center gap-2 rounded-full px-4 text-[15px] font-semibold ${active === s ? "bg-forest text-cream" : "bg-white text-ink"}`}>
              <Icon d={ICON[s]} className="h-4 w-4" />{w(s as WK, l)}
              {s === "tickets" && !!d?.totals.open_tickets && <span className="rounded-full bg-mustard px-1.5 text-[12px] text-ink">{d.totals.open_tickets}</span>}
              {s === "alerts" && !!d?.alerts.filter((a) => !a.read).length && <span className="h-2 w-2 rounded-full bg-loss" />}
            </button>
          ))}
        </div>
      </nav>

      <div className="mx-auto grid max-w-6xl gap-5 px-4 py-6 sm:px-6">
        <span id="sec-home" className="-mt-24 block scroll-mt-0 pt-24" />
        {err && <p className="rounded-2xl bg-[#F6DAD6] p-4 text-[16px] text-loss">{err}</p>}
        {sample && <p className="flex items-start gap-2 rounded-2xl bg-note p-4 text-[15px] text-[#6B4A00]"><Icon d="M12 8v5M12 16h.01M10.3 3.9L2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" className="mt-0.5 h-5 w-5 shrink-0" />{w("sampleData", l)}</p>}

        {d?.farmer && (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[14px] font-semibold text-muted">{w("tryVoice", l)}:</span>
              <SayChip text={SAY.forecast[l]} onSay={send} /><SayChip text={SAY.tickets[l]} onSay={send} /><SayChip text={SAY.phone[l]} onSay={send} />
            </div>

            {d?.farmer?.location?.lat != null && d.farmer.location.lon != null &&
              <Weather lat={d.farmer.location.lat} lon={d.farmer.location.lon} place={place(d.farmer.location.name)} lang={l} />}
            <Card id="crops" icon="crops" title={w("crops", l)}>
              <div className="grid gap-5 lg:grid-cols-2">{d.crops.map((c) => <CropBlock key={c.crop} c={c} l={l} onSay={send} />)}</div>
            </Card>

            <Card id="forecast" icon="forecast" title={w("forecast", l)}>
              <div className="grid gap-5 lg:grid-cols-2">{d.crops.map((c) => <ForecastBlock key={c.crop} c={c} l={l} />)}</div>
            </Card>

            <Card id="tickets" icon="tickets" title={w("tickets", l)} action={!d.orders.some((o) => !["sale_confirmed", "cancelled"].includes(o.status)) ? <SayChip text={SAY.order[l]} onSay={send} /> : undefined}>
              {d.orders.length ? <div className="grid gap-4">{d.orders.map((o) => <Ticket key={o.id} o={o} l={l} onSay={send} />)}</div>
                : <p className="rounded-2xl bg-white p-5 text-[17px] text-muted">{w("noTickets", l)}</p>}
            </Card>

            <div className="grid gap-5 lg:grid-cols-2">
              <Card id="storage" icon="storage" title={w("storage", l)}>
                <div className="grid gap-3">
                  {d.storage.map((b) => (
                    <div key={b.id} className="rounded-[20px] bg-white p-4">
                      <div className="flex flex-wrap items-center gap-2"><b className="font-display text-[18px]">{b.id}</b><Badge tone={b.status === "confirmed" ? "ok" : b.status === "rejected" ? "loss" : "note"}>{w("booked", l)} · {b.status}</Badge></div>
                      <p className="mt-1 text-[17px] font-semibold">{b.warehouse?.name}</p>
                      <p className="text-[15px] text-muted">{cropName(b.crop, l)} · {Math.round(b.qty_kg / 100)} q · {b.days} {w("days", l)} · {inr(b.est_cost)}</p>
                      <p className="mt-1 text-[13px] text-muted">{w("operatorConfirms", l)}</p>
                    </div>
                  ))}
                  {d.crops.filter((c) => !d.storage.some((b) => b.crop === c.crop)).map((c) => (
                    <div key={c.crop} className="rounded-[20px] border-2 border-dashed border-rule bg-white/60 p-4">
                      <p className="text-[14px] font-semibold text-muted">{cropName(c.crop, l)} · {w("notBooked", l)}</p>
                      {c.storage_suggestion ? (
                        <>
                          <p className="mt-1 flex flex-wrap items-center gap-2 text-[18px] font-bold">{c.storage_suggestion.name}{isSample(c.storage_suggestion.verification) && <Badge>{w("sample", l)}</Badge>}</p>
                          <p className="text-[15px] text-muted">{c.storage_suggestion.type} · {Math.round(c.storage_suggestion.distance_km)} {w("km", l)} · {inr(c.storage_suggestion.est_cost_7d)} {w("for7", l)}</p>
                          <div className="mt-2"><SayChip text={SAY.storage[l]} onSay={send} /></div>
                        </>
                      ) : <p className="mt-1 text-[16px]">{w("noStore", l)}</p>}
                    </div>
                  ))}
                </div>
              </Card>

              <Card id="transport" icon="transport" title={w("transport", l)}>
                <div className="grid gap-4">
                  {d.orders.filter((o) => o.contact).map((o) => (
                    <a key={o.id} href={`tel:${o.contact!.phone}`} className="flex items-center justify-between gap-3 rounded-[20px] bg-forest p-4 text-cream">
                      <span><span className="block text-[13px] text-sage">{o.transport?.id} · {w("driver", l)}</span><b className="text-[18px]">{o.contact!.name}</b><span className="block text-[12px] text-sage">{w("notVerified", l)}</span></span>
                      <span className="inline-flex min-h-[48px] items-center gap-2 rounded-full bg-mustard px-4 font-bold text-ink">{w("call", l)} {o.contact!.phone}</span>
                    </a>
                  ))}
                  {d.crops.filter((c) => c.transport).map((c) => (
                    <div key={c.crop} className="rounded-[20px] bg-white p-4">
                      <p className="text-[14px] font-semibold text-muted">{cropName(c.crop, l)} · {w("fleets", l)} {place(c.transport!.destination)} · {Math.round(c.transport!.distance_km)} {w("km", l)}{c.transport!.est_hours ? ` · ${c.transport!.est_hours} ${w("hours", l)}` : ""}</p>
                      <ul className="mt-2 grid gap-2">
                        {c.transport!.options.map((t) => (
                          <li key={t.transporter} className="flex items-center justify-between gap-3 rounded-2xl bg-paper px-3 py-2.5">
                            <span className="min-w-0"><b className="block truncate text-[16px]">{t.transporter}</b><span className="text-[13px] text-muted">{t.vehicle} · {inr(t.per_qtl)}{w("perQtl", l)}</span></span>
                            <span className="flex shrink-0 flex-col items-end gap-1"><b className="tabular-nums">{inr(t.total)}</b>{isSample(t.verification) && <Badge>{w("sample", l)}</Badge>}</span>
                          </li>
                        ))}
                      </ul>
                      {!d.orders.some((o) => o.contact) && <p className="mt-2 text-[13px] text-muted">{w("noPhone", l)}</p>}
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
              <Card id="chat" icon="chat" title={w("chat", l)}>
                {d.chat.length ? (
                  <ol ref={(el) => { if (el) el.scrollTop = el.scrollHeight; }} className="grid max-h-[460px] gap-3 overflow-y-auto pr-1">
                    {d.chat.slice(-20).map((t, i) => (
                      <li key={i} className="grid gap-1.5">
                        <p className="ml-auto max-w-[85%] rounded-[20px] rounded-br-md bg-forest px-4 py-2.5 text-[16px] text-cream"><span className="block text-[11px] text-sage">{w("you", l)} · {clock(t.at)}</span>{t.u}</p>
                        <p className="max-w-[85%] rounded-[20px] rounded-bl-md bg-white px-4 py-2.5 text-[16px]"><span className="block text-[11px] font-semibold text-moss">KRISHI-X</span>{t.a}</p>
                      </li>
                    ))}
                  </ol>
                ) : <p className="text-[16px] text-muted">{w("noChat", l)}</p>}
              </Card>
              <Card id="alerts" icon="alerts" title={w("alerts", l)}>
                {d.alerts.length ? (
                  <ul className="grid gap-2">
                    {d.alerts.map((a) => (
                      <li key={a.id} className={`rounded-2xl p-3.5 ${a.read ? "bg-white" : "bg-note"}`}>
                        <p className="text-[16px] font-bold">{a.title}</p><p className="text-[14px] text-muted">{a.body}</p><p className="mt-1 text-[12px] text-muted">{clock(a.at)}</p>
                      </li>
                    ))}
                  </ul>
                ) : <p className="text-[16px] text-muted">{w("noAlerts", l)}</p>}
              </Card>
            </div>
            <p className="text-center text-[13px] text-muted">{w("estimates", l)}</p>
          </>
        )}
      </div>

      <AgentBar lang={l} reply={reply || w("tryVoice", l) + ": “" + SAY.tickets[l] + "”"} ai={ai} chips={chips} busy={busy} listening={listening} error=""
        onMic={() => void mic()} onSend={(t) => void send(t)} onLang={(x) => void send({ en: "switch to english", hi: "हिंदी में बोलो", mr: "मराठी मध्ये बोला" }[x])}
        onReset={() => router.push("/")} sid={sid} />
    </main>
  );
}

export default function Page() {
  return <Suspense fallback={null}><DashboardPage /></Suspense>;
}
