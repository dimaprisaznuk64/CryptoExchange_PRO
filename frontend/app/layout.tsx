import type { Metadata } from "next";
import { JetBrains_Mono, IBM_Plex_Sans } from "next/font/google";
import { AuthProvider } from "@/contexts/AuthContext";
import { Navbar } from "@/components/Navbar";
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
  title: "CryptoX | Crypto Exchange",
  description:
    "Simulated cryptocurrency exchange — trade BTC, ETH and more with realtime prices and portfolio tracking.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
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