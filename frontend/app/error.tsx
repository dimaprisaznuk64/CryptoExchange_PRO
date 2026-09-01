"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Button, Card } from "@/components/ui";

// Next.js App Router error boundary: renders in place of any route segment
// (page + nested layouts) that throws during render. Lives inside the root
// layout, so the Navbar and session stay alive — no more white page.
export default function Error({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error("Page render error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <Card className="w-full max-w-md p-6 text-center">
        <span className="inline-block rounded-[2px] bg-bear/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-bear">
          Error
        </span>
        <h1 className="mt-3 text-xl font-bold text-ink">
          Something went wrong
        </h1>
        <p className="mt-2 font-body text-sm text-ink/60">
          An unexpected error crashed this page. Your session is intact — try
          again, or go back to the market overview.
        </p>
        {error.digest && (
          <p className="mt-3 font-mono text-[10px] text-ink0">
            digest: {error.digest}
          </p>
        )}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Button onClick={() => retry()}>Try again</Button>
          <Link
            href="/"
            className="inline-flex items-center rounded-[2px] border border-hairline px-3.5 py-1.5 text-xs font-semibold uppercase tracking-wide text-ink transition-colors hover:border-hairline-strong hover:bg-surface"
          >
            Back to home
          </Link>
        </div>
      </Card>
    </div>
  );
}