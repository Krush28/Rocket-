export const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type Meta = { source: string; verification: string; last_updated: string; freshness_days: number; error?: string | null; note?: string | null };
export type Option = {
  type: string; label: string; destination: string; price: number; gross_revenue: number; deductions: Record<string, number>;
  total_deductions: number; net: number; distance_km: number; verification: string; risks: string[]; rank: number;
  expected_selling_time: string; forecast_confidence: string; data_freshness_days: number; hold_days?: number | null;
};
export type Decision = { action: string; reason: string; reconsider_on: string | null; expected_incremental?: number; factors?: string[] };
export type Plan = {
  profile: Profile; data_mode: "LIVE" | "DEMO"; labels: string; options: Option[]; names?: Record<string, string>;
  mandis: { name: string; distance_km: number; distance_label: string }[] | null;
  prices: Record<string, { modal: number; min: number; max: number; latest_date: string; age_days: number; stale: boolean; meta: Meta }> | null;
  retail: { city: string; retail_price: number; note: string }[] | null;
  sell_vs_hold: { decision: Decision; holds?: Option[]; skipped?: { days: number; why: string }[] } | null;
  storage: { name: string; distance_km: number; rate_qtl_day: number; availability: string; verification: string; est_cost_7d: number; cost_label: string }[] | null;
  transport: { destination: string; distance_km: number; options: { transporter: string; vehicle: string; total: number; per_qtl: number; quote_status: string }[] }[] | null;
  recommendation: { best?: Option; decision?: Decision & { factors?: string[] }; explanation?: string; reconsider_on?: string | null; reason?: string;
    excluded?: { mandi: string; reason: string }[]; confidence?: { score: number; label: string; contributors: string[]; detractors: string[] } } | null;
  trace: { agent: string; status: string; error?: string }[];
};
export type Profile = { crop: string; qty_kg: number; original_qty: number; original_unit: string; location: { name: string }; ready: boolean; can_store: boolean };
export type Slots = { crop?: string; qty?: { original_qty: number; original_unit: string; qty_kg: number }; location?: { name: string }; ready?: boolean; can_store?: boolean };
export type ChatReply = { reply: string; lang: string; state: string; awaiting: string | null; slots: Slots; done: boolean; session_id: string; plan?: Plan; inventory_id?: number };

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(r.status === 429 ? "Too many requests. Please wait a minute." : `Server error (${r.status}).`);
  return r.json();
}

export const chat = (session_id: string, text: string, lang?: string) => post<ChatReply>("/api/chat", { session_id, text, lang });

export type Order = import("./ops").SaleOrder;
export type AgentAction = { type: "plan"; plan: Plan } | { type: "tab"; value: string } | { type: "order"; order: Order } | { type: "lang"; value: string } | { type: "reset" }
  | { type: "done" } | { type: "nav"; value: string; state?: string } | { type: "storage"; booking: unknown };
export type Crop = { crop: string; label: string; qty: number | null; unit: string; active: boolean };
export type AgentReply = { reply: string; lang: string; state: string; actions: AgentAction[]; crops: Crop[]; chips?: string[]; done?: boolean; awaiting?: string | null };
export const agent = (session_id: string, text: string, lang?: string) => post<AgentReply>("/api/agent", { session_id, text, lang });
export const createOrder = (option: Option, profile: Profile) => post<{ id: string; status: string }>("/api/orders", { option, profile });

export async function series(crop: string, mandi_key: string) {
  const r = await fetch(`${API}/api/series?${new URLSearchParams({ crop, mandi_key, days: "180" })}`);
  if (!r.ok) return null;
  return (await r.json()) as { label: string; history: [string, number][]; forecast: { status: string } };
}

export async function transcribe(audio: Blob): Promise<string> {
  const fd = new FormData();
  fd.append("file", audio, "recording.webm");
  const r = await fetch(`${API}/api/voice/transcribe`, { method: "POST", body: fd });
  if (!r.ok) throw new Error("Voice typing is not available here. Please type instead.");
  const said = (((await r.json()).transcript as string) || "").trim(); // backend: services/speech.py returns {transcript, ...}
  if (!said) throw new Error("I could not hear that. Please try again or type.");
  return said;
}
