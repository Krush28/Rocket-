"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { API } from "@/lib/api";
import { isLang, type Lang } from "@/lib/i18n";

type Scheme = { id: string; level: string; state: string | null; category: string; category_label: string; name: string; benefit: string; how: string; url: string };
const STATES = ["Maharashtra", "Uttar Pradesh", "Punjab", "Madhya Pradesh", "Karnataka", "Gujarat", "Rajasthan", "Haryana", "Telangana", "Andhra Pradesh",
  "Tamil Nadu", "Kerala", "West Bengal", "Bihar", "Odisha", "Goa"];
const T = {
  title: { en: "Government schemes", hi: "सरकारी योजनाएँ", mr: "सरकारी योजना" },
  sub: { en: "Central and state schemes for selling, storage, insurance and income. Tap a card to open the official portal.",
    hi: "बिक्री, भंडारण, बीमा और आय से जुड़ी केंद्र और राज्य की योजनाएँ। आधिकारिक पोर्टल खोलने के लिए कार्ड दबाएँ।",
    mr: "विक्री, साठवण, विमा व उत्पन्नाशी संबंधित केंद्र व राज्याच्या योजना. अधिकृत पोर्टल उघडण्यासाठी कार्ड दाबा." },
  state: { en: "State", hi: "राज्य", mr: "राज्य" }, all: { en: "All", hi: "सभी", mr: "सर्व" },
  central: { en: "Central", hi: "केंद्र", mr: "केंद्र" }, how: { en: "Who and how", hi: "कौन और कैसे", mr: "कोण व कसे" },
  open: { en: "Open official portal", hi: "आधिकारिक पोर्टल खोलें", mr: "अधिकृत पोर्टल उघडा" }, back: { en: "Back to assistant", hi: "सहायक पर वापस", mr: "सहाय्यकाकडे परत" },
  check: { en: "Amounts and rules change; confirm on the official portal before applying.", hi: "राशि और नियम बदलते हैं; आवेदन से पहले आधिकारिक पोर्टल पर पुष्टि करें।",
    mr: "रक्कम व नियम बदलतात; अर्ज करण्यापूर्वी अधिकृत पोर्टलवर खात्री करा." },
};

function Schemes() {
  const q = useSearchParams(), router = useRouter();
  const lang: Lang = isLang(q.get("lang") || "") ? (q.get("lang") as Lang) : "en";
  const [state, setState] = useState(q.get("state") || "Maharashtra");
  const [cat, setCat] = useState("all");
  const [rows, setRows] = useState<Scheme[]>([]);
  useEffect(() => {
    fetch(`${API}/api/schemes?${new URLSearchParams({ state, lang })}`).then((r) => r.json()).then((d) => setRows(d.schemes || [])).catch(() => setRows([]));
  }, [state, lang]);
  const cats = useMemo(() => Array.from(new Map(rows.map((r) => [r.category, r.category_label])).entries()), [rows]);
  const shown = rows.filter((r) => cat === "all" || r.category === cat);
  const L = (k: keyof typeof T) => T[k][lang];
  return (
    <main className="min-h-screen bg-paper text-ink" lang={lang}>
      <header className="bg-forest text-cream">
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
          <Link href="/" className="text-[14px] text-sage underline">← {L("back")}</Link>
          <h1 className="mt-2 font-display text-[32px] font-bold">{L("title")}</h1>
          <p className="mt-1 text-[16px] text-sage">{L("sub")}</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <label className="text-[15px]">{L("state")}{" "}
              <select value={state} onChange={(e) => { setState(e.target.value); router.replace(`/schemes?state=${encodeURIComponent(e.target.value)}&lang=${lang}`); }}
                className="ml-1 rounded-xl bg-cream px-3 py-2 text-[16px] text-ink">{STATES.map((s) => <option key={s}>{s}</option>)}</select></label>
            <div className="flex flex-wrap gap-2">
              {[["all", L("all")] as [string, string], ...cats].map(([k, v]) => (
                <button key={k} onClick={() => setCat(k)} className={`min-h-[40px] rounded-full px-4 text-[15px] ${cat === k ? "bg-mustard font-semibold text-ink" : "bg-leaf"}`}>{v}</button>
              ))}
            </div>
          </div>
        </div>
      </header>
      <div className="mx-auto grid max-w-5xl gap-3 px-4 py-6 sm:grid-cols-2 sm:px-6">
        {shown.map((s) => (
          <a key={s.id} href={s.url} target="_blank" rel="noreferrer" className="rounded-[22px] border border-rule bg-cream p-5 hover:border-leaf">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-okbg px-3 py-1 text-[12px] font-semibold text-leaf">{s.level === "central" ? L("central") : s.state}</span>
              <span className="rounded-full bg-note px-3 py-1 text-[12px] font-semibold text-[#6B4A00]">{s.category_label}</span>
            </div>
            <h2 className="mt-2 font-display text-[20px] font-bold">{s.name}</h2>
            <p className="mt-1 text-[16px]">{s.benefit}</p>
            <p className="mt-2 text-[14px] text-muted"><b>{L("how")}:</b> {s.how}</p>
            <p className="mt-3 text-[14px] font-semibold text-leaf underline">{L("open")} ↗</p>
          </a>
        ))}
        <p className="text-[13px] text-muted sm:col-span-2">{L("check")}</p>
      </div>
    </main>
  );
}

export default function Page() {
  return <Suspense><Schemes /></Suspense>;
}
