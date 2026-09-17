import type { Config } from "tailwindcss";

// 색상 토큰은 PRD.MD 5.1 / .cursorrules 1장(라이트 미니멀, Linear·Vercel 톤)을 그대로 반영.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#F8FAFC",
        foreground: "#0F172A",
        border: "#E2E8F0",
        muted: "#64748B",
        status: {
          new: "#3B82F6",
          active: "#22C55E",
          inactive: "#64748B",
        },
      },
      borderRadius: {
        DEFAULT: "6px",
      },
    },
  },
  plugins: [],
};

export default config;
