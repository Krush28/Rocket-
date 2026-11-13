"use client";

import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { series } from "@/lib/api";
import { t, type Lang } from "@/lib/i18n";

export default function PriceChart({ crop, mandiKey, lang }: { crop: string; mandiKey: string; lang: Lang }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof series>> | undefined>(undefined);
  useEffect(() => { series(crop, mandiKey).then(setData); }, [crop, mandiKey]);
  if (data === undefined) return <p className="text-[16px] text-muted">{t("loading", lang)}</p>;
  if (!data || data.history.length < 2) return <p className="text-[16px] text-muted">{t("noHistory", lang, { n: data?.history.length ?? 0 })}</p>;
  const rows = data.history.map(([d, v]) => ({ d, v }));
  return (
    <figure>
      <div className="h-56 w-full">
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <XAxis dataKey="d" tick={{ fontSize: 12 }} minTickGap={40} />
            <YAxis tick={{ fontSize: 12 }} width={56} domain={["auto", "auto"]} />
            <Tooltip formatter={(v) => [`₹${Number(v).toLocaleString("en-IN")}${t("qtl", lang)}`, t("modal", lang)]} />
            <Line type="monotone" dataKey="v" stroke="#0F3D2E" strokeWidth={2.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-1 text-[13px] text-muted">{data.label}</figcaption>
    </figure>
  );
}
