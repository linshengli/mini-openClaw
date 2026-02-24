import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#f7f8fa",
        panel: "rgba(255,255,255,0.76)",
        line: "rgba(10,18,38,0.10)",
        ink: "#0d1b2a",
        accent: "#0033a0",
        accent2: "#ff7a18"
      },
      boxShadow: {
        frosty: "0 12px 40px rgba(12, 23, 45, 0.08)"
      },
      borderRadius: {
        xl2: "1.25rem"
      },
      fontFamily: {
        sans: ["'Avenir Next'", "ui-sans-serif", "system-ui"],
        display: ["'Bodoni Moda'", "serif"]
      }
    }
  },
  plugins: []
};

export default config;

