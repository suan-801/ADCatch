import type { Config } from "tailwindcss";

// 브랜드 리디자인(2026-09): 랜딩=오렌지 우세, 제품=화이트+오렌지 포인트.
// 상태 배지 색상(new/active/inactive)은 기능 의미 유지를 위해 기존 값을 그대로 보존.
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
        brand: {
          DEFAULT: "#FF6B1A",
          dark: "#EA580C",
          light: "#FF8A42",
          cream: "#FFF4EC",
        },
      },
      fontFamily: {
        sans: ["Freesentation", "Pretendard", "system-ui", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "8px",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-14px)" },
        },
        fadeInUp: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        popIn: {
          "0%": { opacity: "0", transform: "scale(0.85)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        pulseFade: {
          "0%, 100%": { opacity: "0.15", transform: "scale(0.94)" },
          "50%": { opacity: "1", transform: "scale(1)" },
        },
        trackFill: {
          "0%, 100%": { width: "55%" },
          "50%": { width: "78%" },
        },
        tagPulse: {
          "0%, 100%": { transform: "scale(0.95)", opacity: "0.85" },
          "50%": { transform: "scale(1.05)", opacity: "1" },
        },
      },
      animation: {
        float: "float 4s ease-in-out infinite",
        "fade-in-up": "fadeInUp 0.6s ease-out both",
        "pop-in": "popIn 0.4s ease-out both",
        "pulse-fade": "pulseFade 3.2s ease-in-out infinite",
        "track-fill": "trackFill 5s ease-in-out infinite",
        "tag-pulse": "tagPulse 3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
