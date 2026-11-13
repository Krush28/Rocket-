"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

type Day = { date: string; kind: string; tmax: number; tmin: number; rain_mm: number; rain_pct: number; wind: number };
type W = { current: { temp: number; kind: string; humidity: number | null; wind: number }; days: Day[]; advice: { key: string; day?: string }[] };

const ICON: Record<string, string> = { clear: "☀️", partly: "⛅", cloudy: "☁️", fog: "🌫️", drizzle: "🌦️", rain: "🌧️", storm: "⛈️" };
const DESC: Record<Lang, Record<string, string>> = {
  en: { clear: "Clear sky", partly: "Partly cloudy", cloudy: "Cloudy", fog: "Foggy", drizzle: "Light rain", rain: "Rain", storm: "Thunderstorm" },
  hi: { clear: "साफ़ आसमान", partly: "हल्के बादल", cloudy: "बादल", fog: "कोहरा", drizzle: "हल्की बारिश", rain: "बारिश", storm: "आंधी-तूफ़ान" },
  mr: { clear: "स्वच्छ आकाश", partly: "थोडे ढग", cloudy: "ढगाळ", fog: "धुके", drizzle: "हलका पाऊस", rain: "पाऊस", storm: "वादळी पाऊस" },
};
const ADV: Record<Lang, Record<string, string>> = {
  en: { rain: "Rain likely on {day}: cover your produce and avoid open trucks that day.", heat: "Very hot days ahead: move perishable crops early in the morning.",
    wind: "Strong wind expected: tie down covers on loaded trucks.", clear: "Good dry weather for harvest and transport." },
  hi: { rain: "{day} को बारिश की संभावना: माल ढककर रखें और उस दिन खुले ट्रक से न भेजें।", heat: "आगे बहुत गर्मी है: जल्दी खराब होने वाली फसल सुबह जल्दी भेजें।",
    wind: "तेज़ हवा की संभावना: लदे ट्रक पर तिरपाल कसकर बाँधें।", clear: "कटाई और ढुलाई के लिए अच्छा सूखा मौसम है।" },
  mr: { rain: "{day} ला पावसाची शक्यता: माल झाकून ठेवा आणि त्या दिवशी उघड्या ट्रकने पाठवू नका.", heat: "पुढे खूप ऊन आहे: लवकर खराब होणारे पीक सकाळी लवकर पाठवा.",
    wind: "जोरदार वाऱ्याची शक्यता: भरलेल्या ट्रकवरील ताडपत्री घट्ट बांधा.", clear: "काढणी आणि वाहतुकीसाठी चांगले कोरडे हवामान आहे." },
};
const T = { title: { en: "Weather at your farm", hi: "आपके खेत का मौसम", mr: "तुमच्या शेताचे हवामान" }, today: { en: "Today", hi: "आज", mr: "आज" },
  hum: { en: "Humidity", hi: "नमी", mr: "आर्द्रता" }, wind: { en: "Wind", hi: "हवा", mr: "वारा" } };
const LOCALE: Record<Lang, string> = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

// Visual 7-day farm weather (Open-Meteo via our API): big "now" panel, a day strip with icons and rain chance, and one piece of selling advice.
export default function Weather({ lat, lon, place, lang }: { lat: number; lon: number; place: string; lang: Lang }) {
  const [w, setW] = useState<W | null>(null);
  useEffect(() => {
    fetch(`${API}/api/weather?lat=${lat}&lon=${lon}`).then((r) => r.json()).then((d) => setW(d && d.days ? d : null)).catch(() => setW(null));
  }, [lat, lon]);
  if (!w) return null;
  const day = (iso: string, short = true) => new Date(iso + "T12:00:00").toLocaleDateString(LOCALE[lang], { weekday: short ? "short" : "long" });
  const a = w.advice[0];
  const tone = a.key === "clear" ? "bg-okbg text-[#1C5A43]" : "bg-note text-[#6B4A00]";
  return (
    <section id="sec-weather" className="overflow-hidden rounded-[22px] border border-rule bg-gradient-to-br from-[#E8F3FB] via-cream to-[#FFF6DD]">
      <div className="flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-widest text-muted">{T.title[lang]} · {place}</p>
          <div className="mt-1 flex items-center gap-3">
            <span className="text-[56px] leading-none" aria-hidden>{ICON[w.current.kind]}</span>
            <div>
              <p className="font-display text-[44px] font-bold leading-none">{w.current.temp}°</p>
              <p className="text-[16px] text-[#33433A]">{DESC[lang][w.current.kind]}</p>
            </div>
          </div>
        </div>
        <div className="flex gap-2 text-[14px]">
          {w.current.humidity != null && <span className="rounded-full bg-white/70 px-3 py-1.5">💧 {T.hum[lang]} {w.current.humidity}%</span>}
          <span className="rounded-full bg-white/70 px-3 py-1.5">🌬️ {T.wind[lang]} {w.current.wind} km/h</span>
        </div>
      </div>
      <div className="flex gap-2 overflow-x-auto px-5 pb-4">
        {w.days.map((d, i) => (
          <div key={d.date} className={`flex min-w-[82px] flex-col items-center rounded-2xl px-2 py-3 ${i === 0 ? "bg-forest text-cream" : "bg-white/75"}`}>
            <span className="text-[13px] font-semibold">{i === 0 ? T.today[lang] : day(d.date)}</span>
            <span className="my-1 text-[28px]" aria-hidden>{ICON[d.kind]}</span>
            <span className="text-[15px] font-bold">{d.tmax}°<span className={`font-normal ${i === 0 ? "text-sage" : "text-muted"}`}> / {d.tmin}°</span></span>
            <span className={`mt-1 text-[12px] ${d.rain_pct >= 50 ? "font-bold text-[#1D5FA8]" : i === 0 ? "text-sage" : "text-muted"}`}>💧 {d.rain_pct}%</span>
          </div>
        ))}
      </div>
      <p className={`mx-5 mb-5 rounded-2xl p-3 text-[15px] font-semibold ${tone}`}>{ADV[lang][a.key].replace("{day}", a.day ? day(a.day, false) : "")}</p>
    </section>
  );
}
