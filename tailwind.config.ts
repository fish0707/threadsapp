import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#111827",
          accent: "#6366f1",
          accentHover: "#4f46e5",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "PingFang TC",
          "Noto Sans TC",
          "Microsoft JhengHei",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
