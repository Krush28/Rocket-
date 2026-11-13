import { API } from "./api";

// Portals client: role login token (X-User-Token) or the farmer's device id (X-Device).
export type Role = "farmer" | "fpo" | "transporter" | "warehouse" | "admin";
export type User = { id: number; phone: string; name: string | null; role: Role; state: string | null };
export type Note = { id: number; title: string; body: string; link: string | null; read: boolean; at: string | null };
export type Point = { name: string; lat: number | null; lon: number | null };
export type Job = {
  id: string; order_id: string; status: string; pickup: Point; drop: Point; crop: string; crop_label: string; qty_kg: number; vehicle: string | null;
  distance_km: number | null; est_fare: number | null; transporter: string | null; next: string[]; created: string | null;
  log: { at: string; status: string; note: string }[];
};
export type Warehouse = { id: string; name: string; type: string; temp: string; district: string; state: string; rate_qtl_day: number; min_days: number;
  declared_capacity_qtl: number; free_qtl: number; distance_km?: number };
export type Booking = { id: string; status: string; crop: string; crop_label: string; qty_kg: number; days: number; est_cost: number; warehouse: Warehouse | null;
  next: string[]; created: string | null; device: string };
export type SaleOrder = { id: string; status: string; created: string | null; payload: { option: { label: string; net: number; destination: string };
  profile: { crop: string; qty_kg: number; location: Point }; final: null | { actual_price: number; net_earnings: number; expected_net: number } };
  log: { at: string; event: string; status: string; note: string }[]; next_events: string[]; transport: Job | null };

const TOKEN = "kxToken", USER = "kxUser";

export function session(): { token: string; user: User } | null {
  try {
    const token = localStorage.getItem(TOKEN), user = localStorage.getItem(USER);
    return token && user ? { token, user: JSON.parse(user) } : null;
  } catch { return null; }
}

export function logout() {
  try { localStorage.removeItem(TOKEN); localStorage.removeItem(USER); } catch { /* private mode */ }
}

async function req<T>(method: string, path: string, body?: unknown, headers: Record<string, string> = {}): Promise<T> {
  const s = session();
  const r = await fetch(`${API}/api${path}`, {
    method, headers: { "Content-Type": "application/json", ...(s ? { "X-User-Token": s.token } : {}), ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
  return r.json();
}

export async function login(phone: string, role: Role, name: string, state: string) {
  const r = await req<{ token: string; user: User }>("POST", "/login", { phone, role, name: name || null, state: state || null });
  try { localStorage.setItem(TOKEN, r.token); localStorage.setItem(USER, JSON.stringify(r.user)); } catch { /* memory only */ }
  return r;
}

export const notes = (device?: string) => req<Note[]>("GET", `/notifications${device ? `?device=${encodeURIComponent(device)}` : ""}`);
export const notesRead = (device?: string) => req("POST", `/notifications/read${device ? `?device=${encodeURIComponent(device)}` : ""}`);
export const jobs = (scope: "open" | "mine") => req<Job[]>("GET", `/transport/jobs?scope=${scope}`);
export const jobAct = (id: string, action: string) => req<Job>("POST", `/transport/jobs/${id}/${action}`);
export const bookings = () => req<Booking[]>("GET", "/storage/bookings");
export const myWarehouses = () => req<Warehouse[]>("GET", "/storage/mine");
export const bookAct = (id: string, action: string, device?: string) => req<Booking>("POST", `/storage/bookings/${id}/${action}`, undefined, device ? { "X-Device": device } : {});
export const farmer = (device: string) => req<{ orders: SaleOrder[]; storage: Booking[] }>("GET", `/farmer/${encodeURIComponent(device)}`);
export const confirmSale = (id: string, device: string, price: number) => req<SaleOrder>("POST", `/sale/${id}/confirm`, { actual_price: price }, { "X-Device": device });
export const fpo = () => req<{ members_produce: { crop: string; crop_label: string; farmers: number; qty_kg: number; trucks_10t: number }[];
  orders_by_status: Record<string, number>; sales_closed: number; net_earnings_total: number; recent_orders: SaleOrder[] }>("GET", "/fpo/summary");
export const adminOverview = () => req<Record<string, number | Record<string, unknown>>>("GET", "/admin/overview");

export const rupees = (n: number | null | undefined) => (n == null ? "—" : "₹" + Math.round(n).toLocaleString("en-IN"));
export const kg = (n: number) => (n >= 1000 ? `${(n / 1000).toLocaleString("en-IN", { maximumFractionDigits: 1 })} t` : `${Math.round(n)} kg`);
export const short = (k: string) => k.split(", ")[0];
