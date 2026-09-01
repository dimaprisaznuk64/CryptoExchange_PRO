"use client";

import { useEffect } from "react";
import { Button, Card } from "@/components/ui";

// Segment boundary for /trade: the heaviest client page (candlestick chart,
// order book, forms). If one widget crashes, only the trading terminal area
// is replaced — the navbar and the rest of the app stay interactive.
export default function TradeError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error("Trade page render error:", error);
  }, [error]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <Card className="mx-auto max-w-md p-6 text-center">
        <h2 className="text-lg font-bold text-ink">Trading terminal error</h2>
        <p className="mt-2 font-body text-sm text-ink/60">
          The chart / order book failed to render here. Try again — your
          portfolio and orders are safe.
        </p>
        {error.digest && (
          <p className="mt-2 font-mono text-[10px] text-ink0">
            digest: {error.digest}
          </p>
        )}
        <div className="mt-5">
          <Button onClick={() => retry()}>Try again</Button>
        </div>
      </Card>
    </div>
  );
}