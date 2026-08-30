export interface BrandColors {
  bg: string;
  surface: string;
  surface2: string;
  ink: string;
  amber: string;
  bull: string;
  bear: string;
  hairline: string;
  hairlineStrong: string;
}

export interface SiteConfig {
  name: string;
  shortName: string;
  tagline: string;
  description: string;
  logoText: string;
  accentLabel: string;
  url: string;
  apiUrl: string;
  colors: BrandColors;
}

/**
 * White-label entry point. Rename the exchange, swap the logo letter and
 * adjust the palette here — the whole UI (metadata, navbar, theme tokens)
 * follows. Keep values plain (no process.env) so builds stay deterministic.
 */
export const site: SiteConfig = {
  name: "CryptoX",
  shortName: "CryptoX",
  tagline: "Simulated crypto exchange",
  description:
    "Simulated cryptocurrency exchange — trade BTC, ETH and more with realtime prices and portfolio tracking.",
  logoText: "C",
  accentLabel: "X",
  url: "https://crypto-exchange-pro-two.vercel.app",
  apiUrl: "https://cryptoexchange-backend.onrender.com",
  colors: {
    bg: "#0a0a0b",
    surface: "#141416",
    surface2: "#1a1a1d",
    ink: "#e7e5dd",
    amber: "#ffae00",
    bull: "#17c979",
    bear: "#ff4d4d",
    hairline: "rgb(231 229 221 / 12%)",
    hairlineStrong: "rgb(231 229 221 / 22%)",
  },
};