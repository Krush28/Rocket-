import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KRISHI-X | Where you keep the most",
  description: "Voice-first mandi price intelligence: net earnings after costs, sell now or hold, storage and transport.",
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#0F3D2E" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
