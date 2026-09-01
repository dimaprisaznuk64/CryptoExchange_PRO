"use client";

import { useEffect } from "react";
import type { CSSProperties } from "react";
import { site } from "@/lib/site";

// Last-resort boundary: fires when even the root layout crashes. global-error
// renders its own <html>/<body> and does NOT get globals.css, so the brand
// palette is pushed inline (mirrors layout.tsx) and layout is inline-styled.
const brandStyle: CSSProperties = {
  "--bg": site.colors.bg,
  "--surface": site.colors.surface,
  "--ink": site.colors.ink,
  "--amber": site.colors.amber,
  "--bear": site.colors.bear,
  "--hairline": site.colors.hairline,
} as unknown as CSSProperties;

const pageStyle: CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "24px",
  backgroundColor: "var(--bg)",
  color: "var(--ink)",
  fontFamily: "ui-monospace, 'JetBrains Mono', SFMono-Regular, Menlo, monospace",
};

export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error("Fatal app error:", error);
  }, [error]);

  return (
    <html lang="en" style={brandStyle}>
      <body style={pageStyle}>
        <main
          style={{
            maxWidth: 420,
            width: "100%",
            border: "1px solid var(--hairline)",
            background: "var(--surface)",
            borderRadius: 2,
            padding: 24,
            textAlign: "center",
          }}
        >
          <span
            style={{
              display: "inline-block",
              background: "rgba(255,77,77,0.1)",
              color: "var(--bear)",
              padding: "2px 8px",
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: 2,
              borderRadius: 2,
            }}
          >
            Fatal error
          </span>
          <h1 style={{ marginTop: 12, fontSize: 20, fontWeight: 700 }}>
            {site.name} hit a problem
          </h1>
          <p style={{ marginTop: 8, fontSize: 13, opacity: 0.65 }}>
            The application failed to start. Reload the page or try again.
          </p>
          {error.digest && (
            <p style={{ marginTop: 10, fontSize: 10, opacity: 0.5 }}>
              digest: {error.digest}
            </p>
          )}
          <button
            type="button"
            onClick={() => retry()}
            style={{
              marginTop: 20,
              padding: "8px 16px",
              fontSize: 12,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: 1,
              background: "var(--amber)",
              color: "var(--bg)",
              border: "none",
              borderRadius: 2,
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}