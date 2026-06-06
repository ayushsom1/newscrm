/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Editorial navy palette — newspaper masthead direction (NYT/FT/WSJ
        // tradition). `ink` is body text (warm charcoal, max legibility);
        // `nav` is the dark surface (deep navy) used on the sidebar and
        // primary buttons. We keep them separate so paragraph text stays
        // readable while chrome reads as "established institution."
        ink: "#1A1F2E",          // body text — warm-neutral charcoal
        nav: "#0F1E3E",          // primary surface: sidebar, primary buttons
        "nav-darker": "#08142B", // hover state on dark surfaces
        "nav-soft":   "#1E3A6D", // subdued variant

        brand: "#9E1B17",        // accent: active nav bar, errors, destructive
        ai: "#2563EB",           // AI features
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
