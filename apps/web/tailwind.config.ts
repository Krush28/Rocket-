import type { Config } from "tailwindcss";

// Palette from Rocket's "settlement-slip" redesign (design/krishimitra-redesign).
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        forest: "#0F3D2E", leaf: "#1C5A43", moss: "#2D6A52", mint: "#7BD389", sage: "#A9C9B4",
        cream: "#F3F1E8", paper: "#EEEDE4", ink: "#11221A", mustard: "#F2B01E", rule: "#DAD7C6",
        muted: "#55635B", note: "#F9E3A6", loss: "#B03A2E", okbg: "#DCEBDD",
      },
      fontFamily: {
        display: ["'Bricolage Grotesque'", "system-ui", "sans-serif"],
        body: ["'Instrument Sans'", "'Noto Sans Devanagari'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
