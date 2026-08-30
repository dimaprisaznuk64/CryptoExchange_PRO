"use client";

import { memo, useMemo } from "react";
import type { BookLevel } from "@/lib/types";
import { formatNumber, formatPrice } from "@/lib/format";

interface OrderBookProps {
  levels: BookLevel[];
  bestBid?: number;
  bestAsk?: number;
  spread?: number;
}

export const OrderBook = memo(function OrderBook({
  levels,
  bestBid,
  bestAsk,
  spread,
}: OrderBookProps) {
  const { bids, asks, maxQty } = useMemo(() => {
    const bids = [...levels].sort((a, b) => b.bid - a.bid);
    const asks = [...levels].sort((a, b) => a.ask - b.ask);
    let max = 0.0001;
    for (const l of levels) max = Math.max(max, l.bid_qty, l.ask_qty);
    return { bids, asks, maxQty: max };
  }, [levels]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-xs font-medium text-zinc-500">
        <span>Price</span>
        <span>Amount</span>
      </div>

      <div className="flex flex-col justify-end gap-[2px]">
        {asks.map((l, i) => (
          <div
            key={`ask-${i}`}
            className="relative flex items-center justify-between overflow-hidden rounded px-2 py-[2px] text-[11px] font-mono"
          >
            <div
              className="absolute inset-y-0 right-0 bg-rose-500/10"
              style={{ width: `${(l.ask_qty / maxQty) * 100}%` }}
            />
            <span className="relative text-rose-400">
              {formatPrice(l.ask)}
            </span>
            <span className="relative text-zinc-400">
              {formatNumber(l.ask_qty)}
            </span>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-center">
        {bestBid && bestAsk ? (
          <div className="flex items-center justify-between text-xs">
            <span className="text-emerald-400">
              B {formatPrice(bestBid)}
            </span>
            <span className="text-zinc-500">
              spread {spread != null ? formatPrice(spread) : "-"}
            </span>
            <span className="text-rose-400">A {formatPrice(bestAsk)}</span>
          </div>
        ) : (
          <span className="text-xs text-zinc-500">No book yet</span>
        )}
      </div>

      <div className="flex flex-col gap-[2px]">
        {bids.map((l, i) => (
          <div
            key={`bid-${i}`}
            className="relative flex items-center justify-between overflow-hidden rounded px-2 py-[2px] text-[11px] font-mono"
          >
            <div
              className="absolute inset-y-0 right-0 bg-emerald-500/10"
              style={{ width: `${(l.bid_qty / maxQty) * 100}%` }}
            />
            <span className="relative text-emerald-400">
              {formatPrice(l.bid)}
            </span>
            <span className="relative text-zinc-400">
              {formatNumber(l.bid_qty)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
});