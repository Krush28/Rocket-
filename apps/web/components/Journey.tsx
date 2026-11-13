"use client";

import type { Lang } from "@/lib/i18n";
import { rupees, type SaleOrder } from "@/lib/ops";

const STEPS: { key: string; en: string; hi: string; mr: string }[] = [
  { key: "created", en: "Order created", hi: "ऑर्डर बना", mr: "ऑर्डर तयार" },
  { key: "transport_requested", en: "Truck requested", hi: "ट्रक माँगा", mr: "ट्रक मागवला" },
  { key: "transport_accepted", en: "Truck accepted", hi: "ट्रक स्वीकार", mr: "ट्रक स्वीकारला" },
  { key: "in_transit", en: "On the way", hi: "रास्ते में", mr: "वाटेत" },
  { key: "delivered", en: "Delivered", hi: "पहुँच गया", mr: "पोहोचला" },
  { key: "sale_confirmed", en: "Sale closed", hi: "बिक्री पूरी", mr: "विक्री पूर्ण" },
];
const L = (s: { en: string; hi: string; mr: string }, l: Lang) => s[l] || s.en;
const T = {
  token: { en: "Booking token", hi: "बुकिंग टोकन", mr: "बुकिंग टोकन" },
  driver: { en: "Transporter", hi: "ट्रांसपोर्टर", mr: "वाहतूकदार" },
  waiting: { en: "waiting for a transporter to accept", hi: "ट्रांसपोर्टर के स्वीकार करने का इंतज़ार", mr: "वाहतूकदाराच्या स्वीकृतीची प्रतीक्षा" },
  fare: { en: "Estimated fare", hi: "अनुमानित किराया", mr: "अंदाजे भाडे" },
  sayPrice: { en: "Delivered. Tell the AI the price you got, e.g. \"I sold at 4100\".", hi: "पहुँच गया। जो भाव मिला वह AI को बताइए, जैसे \"4100 में बेचा\"।",
    mr: "पोहोचला. मिळालेला भाव AI ला सांगा, उदा. \"4100 ला विकले\"." },
};

// Farmer's order journey: one line per step, live from the transporter's actions (polled by the page).
export default function Journey({ order, lang }: { order: SaleOrder; lang: Lang }) {
  const idx = STEPS.findIndex((s) => s.key === order.status);
  const tr = order.transport;
  if (order.status === "cancelled") return <p className="mt-2 text-[16px] text-loss">Cancelled</p>;
  return (
    <div className="mt-3">
      {tr && (
        <div className="mb-3 rounded-2xl bg-paper p-3 text-[15px]">
          <p>{L(T.token, lang)}: <b className="font-display text-[18px]">{tr.id}</b></p>
          <p>{L(T.driver, lang)}: <b>{tr.transporter || L(T.waiting, lang)}</b>{tr.vehicle ? ` · ${tr.vehicle}` : ""}</p>
          {tr.est_fare != null && <p>{L(T.fare, lang)}: <b>{rupees(tr.est_fare)}</b></p>}
        </div>
      )}
      <ol className="grid gap-1.5">
        {STEPS.map((s, i) => (
          <li key={s.key} className="flex items-center gap-3 text-[16px]">
            <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-[13px] font-bold ${i <= idx ? "bg-forest text-cream" : "bg-[#ECEAE0] text-muted"}`}>
              {i < idx || order.status === "sale_confirmed" ? "✓" : i + 1}</span>
            <span className={i <= idx ? "font-semibold" : "text-muted"}>{L(s, lang)}</span>
          </li>
        ))}
      </ol>
      {order.status === "delivered" && <p className="mt-3 rounded-xl bg-note p-3 text-[15px]">{L(T.sayPrice, lang)}</p>}
    </div>
  );
}

const D = {
  title: { en: "Sale complete", hi: "बिक्री पूरी हुई", mr: "विक्री पूर्ण झाली" },
  got: { en: "You received (net)", hi: "आपको मिला (शुद्ध)", mr: "तुम्हाला मिळाले (निव्वळ)" },
  exp: { en: "We had estimated", hi: "हमारा अनुमान था", mr: "आमचा अंदाज होता" },
  again: { en: "Start a new task with the AI", hi: "AI के साथ नया काम शुरू करें", mr: "AI सोबत नवीन काम सुरू करा" },
  close: { en: "Back to my results", hi: "मेरे नतीजों पर वापस", mr: "माझ्या निकालांकडे परत" },
};

export function DoneCard({ order, lang, onAgain, onClose }: { order: SaleOrder; lang: Lang; onAgain: () => void; onClose: () => void }) {
  const f = order.payload.final;
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-ink/60 p-4" role="dialog" aria-modal>
      <div className="w-full max-w-md rounded-[26px] bg-forest p-6 text-cream shadow-2xl">
        <p className="text-[13px] font-semibold uppercase tracking-widest text-mint">{order.id}</p>
        <h2 className="mt-1 font-display text-[30px] font-bold">{L(D.title, lang)}</h2>
        {f && (
          <>
            <p className="mt-3 text-[15px] text-sage">{L(D.got, lang)}</p>
            <p className="font-display text-[40px] font-extrabold">{rupees(f.net_earnings)}</p>
            <p className="text-[15px] text-sage">{L(D.exp, lang)}: {rupees(f.expected_net)} · ₹{Math.round(f.actual_price).toLocaleString("en-IN")}/q</p>
          </>
        )}
        <button onClick={onAgain} className="mt-6 min-h-[54px] w-full rounded-2xl bg-mustard text-[18px] font-bold text-ink">{L(D.again, lang)}</button>
        <button onClick={onClose} className="mt-2 min-h-[44px] w-full rounded-2xl text-[15px] text-sage">{L(D.close, lang)}</button>
      </div>
    </div>
  );
}
