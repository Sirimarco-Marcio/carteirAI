import type { Config } from "tailwindcss";

/**
 * Design system "Warm Ledger" — espelha stitch/warm_ledger/DESIGN.md e docs/07.
 * Ink & Paper: papel quente, tinta de alto contraste, verde de marca, valores em mono tabular.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f7faf7", // fundo (Level 0)
        surface: "#ffffff", // cards (Level 1)
        "surface-2": "#f1f4f1", // washes suaves
        line: "#e0e3e0", // hairline border
        ink: "#181c1b", // texto primário
        muted: "#5c6661", // texto secundário
        brand: "#1e6f5c", // marca / ativo
        "brand-dark": "#005645", // botões primários
        "brand-soft": "#d6e6e0", // washes/chips de marca
        "brand-fg": "#ffffff",
        entrada: "#1f7a5c", // receita (verde)
        saida: "#c0493d", // despesa (tijolo quente)
        alerta: "#c8852e", // fatura/aviso (ocre)
        // paleta estável de categorias (corrige a inconsistência do Stitch)
        "cat-moradia": "#2f6f5e",
        "cat-mercado": "#d4a017",
        "cat-transporte": "#3b82c4",
        "cat-educacao": "#d97b35",
        "cat-lazer": "#8a5cd1",
        "cat-saude": "#d1495b",
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-sans-serif", "system-ui"],
        body: ["var(--font-body)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "0.25rem",
        DEFAULT: "0.5rem",
        md: "0.75rem",
        lg: "1rem",
        xl: "1.5rem",
      },
      boxShadow: {
        // Level 2: sombra ambiente suave (tinta a 4%)
        float: "0 4px 12px rgba(24,28,27,0.04)",
      },
      letterSpacing: {
        caps: "0.05em",
      },
    },
  },
  plugins: [],
};

export default config;
