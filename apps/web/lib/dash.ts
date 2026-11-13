import { API } from "./api";
import type { Lang } from "./i18n";
import type { Booking, Note, SaleOrder } from "./ops";

// Farmer dashboard data (GET /api/dashboard/{device}): one call, everything the farmer has done and what the plan says.
export type FPoint = { days: number; date: string; predicted: number; lo: number; hi: number; confidence?: string };
export type CropCard = {
  crop: string; label: string; qty_kg: number; original_qty: number; original_unit: string;
  best: null | { label: string; destination: string; net: number; gross_revenue: number; total_deductions: number; price: number; distance_km: number;
    type: string; hold_days?: number | null; verification: string; deductions: Record<string, number> };
  no_best_reason: string | null;
  decision: null | { action: string; reason: string; factors?: string[]; reconsider_on?: string | null; expected_incremental?: number };
  confidence: null | { score: number; label: string; contributors: string[]; detractors: string[] };
  forecast: null | { mandi: string; current: number; points: FPoint[]; change_pct: number | null; note: string };
  options: { label: string; destination: string; net: number; price: number; distance_km: number; verification: string }[];
  storage_suggestion: null | { id: string; name: string; type: string; distance_km: number; rate_qtl_day: number; est_cost_7d: number; availability: string; verification: string };
  transport: null | { destination: string; distance_km: number; est_hours?: number;
    options: { transporter: string; vehicle: string; total: number; per_qtl: number; verification: string; quote_status: string; phone: string | null }[] };
};
export type DashOrder = SaleOrder & { contact: null | { name: string; phone: string; note: string } };
export type Turn = { u: string; a: string; at?: string; lang?: string };
export type Dash = {
  device: string; lang: Lang; ai: string; data_mode: "LIVE" | "DEMO" | null; labels: string | null;
  farmer: null | { location: { name: string }; ready: boolean; can_store: boolean; crops: { crop: string; label: string; qty: number; unit: string }[] };
  crops: CropCard[]; orders: DashOrder[]; storage: Booking[]; alerts: Note[]; chat: Turn[];
  totals: { expected_net: number; qty_kg: number; open_tickets: number; sold_net: number };
};

export async function dashboard(device: string, lang: Lang): Promise<Dash> {
  const r = await fetch(`${API}/api/dashboard/${encodeURIComponent(device)}?lang=${lang}`);
  if (!r.ok) throw new Error(`Server error (${r.status}).`);
  return r.json();
}

// codes the backend keeps for provenance -> is this a real, verified record?
// Presentation rule: no "sample" badges or banners in the UI (provenance stays in the API's verification codes for developers).
export const isSample = (_v?: string | null) => false;
