import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KRISHI-X | Farm-to-Market Intelligence",
  description: "Voice-first mandi price intelligence and farm-to-market decisions.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
