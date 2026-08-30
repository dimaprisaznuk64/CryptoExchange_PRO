import type { Metadata } from "next";
import type { CSSProperties } from "react";
import { JetBrains_Mono, IBM_Plex_Sans } from "next/font/google";
import { AuthProvider } from "@/contexts/AuthContext";
import { Navbar } from "@/components/Navbar";
import { site } from "@/lib/site";
import "./globals.css";

// Terminal identity: monospace carries the whole UI (headers, nav, data,
// buttons) — not just numbers. Plex Sans is reserved for longer prose
// (empty states, help text) where mono would hurt readability.
const mono = JetBrains_Mono({
  variable: "--font-mono-primary",
  subsets: ["latin"],
  weight: ["400", "500", "700", "800"],
});

const sansBody = IBM_Plex_Sans({
  variable: "--font-sans-body",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: `${site.name} | Crypto Exchange`,
  description: site.description,
};

/**
 * Push the white-label palette as inline CSS custom properties on <html>.
 * globals.css declares the tokens as var(--bg), var(--amber), …; inline
 * styles win over the :root block, so the whole UI restyles from site.ts.
 */
const brandStyle: CSSProperties = {
  "--bg": site.colors.bg,
  "--surface": site.colors.surface,
  "--surface-2": site.colors.surface2,
  "--ink": site.colors.ink,
  "--amber": site.colors.amber,
  "--bull": site.colors.bull,
  "--bear": site.colors.bear,
  "--hairline": site.colors.hairline,
  "--hairline-strong": site.colors.hairlineStrong,
} as CSSProperties;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      style={brandStyle}
      className={`${mono.variable} ${sansBody.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-bg text-ink">
        <AuthProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}