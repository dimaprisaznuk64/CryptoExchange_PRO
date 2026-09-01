"use client";

import { memo } from "react";
import type { MarketTrade } from "@/lib/types";
import { formatNumber, formatPrice, formatTime } from "@/lib/format";

interface MarketTradesPanelProps {
  trades: MarketTrade[];
}

export const MarketTradesPanel = memo(function MarketTradesPanel({
  trades,
}: MarketTradesPanelProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between text-xs font-medium text-ink/50">
        <span>Price</span>
        <span>Qty</span>
        <span>Time</span>
      </div>
      <div className="flex max-h-64 flex-col gap-[2px] overflow-y-auto">
        {trades.length === 0 ? (
          <span className="py-6 text-center text-sm text-ink0">
            No trades yet.
          </span>
        ) : (
          trades.slice(0, 40).map((t, i) => (
            <div
              key={`${t.time}-${i}`}
              className="flex items-center justify-between px-2 py-[2px] text-[11px] font-mono"
            >
              <span className={t.side === "buy" ? "text-bull" : "text-bear"}>
                {formatPrice(t.price)}
              </span>
              <span className="text-ink/60">{formatNumber(t.qty)}</span>
              <span className="text-ink0">{formatTime(t.time)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
});