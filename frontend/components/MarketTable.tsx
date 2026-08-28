"use client";

import Link from "next/link";
import type { Ticker } from "@/lib/types";
import { formatPercent, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

interface MarketTableProps {
  tickers: Ticker[];
  livePrices?: Record<string, number>;
  compact?: boolean;
}

export function MarketTable({
  tickers,
  livePrices,
  compact = false,
}: MarketTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-xs text-zinc-500">
            <th className="px-4 py-2 font-medium">Pair</th>
            <th className="px-4 py-2 text-right font-medium">Last price</th>
            <th className="px-4 py-2 text-right font-medium">24h change</th>
            {!compact && (
              <th className="px-4 py-2 text-right font-medium">24h high</th>
            )}
            {!compact && (
              <th className="px-4 py-2 text-right font-medium">24h low</th>
            )}
            {!compact && (
              <th className="px-4 py-2 text-right font-medium">24h volume</th>
            )}
            <th className="px-4 py-2 text-right font-medium">Trade</th>
          </tr>
        </thead>
        <tbody>
          {tickers.map((t) => {
            const live = livePrices?.[t.pair];
            const price = live ?? t.last;
            const up = t.change_24h >= 0;
            return (
              <tr
                key={t.pair}
                className="border-b border-zinc-800/60 transition-colors hover:bg-zinc-800/40"
              >
                <td className="px-4 py-2 font-semibold text-zinc-100">
                  {t.base_asset}
                  <span className="text-zinc-500">/{t.quote_asset}</span>
                </td>
                <td className="px-4 py-2 text-right font-mono text-zinc-200">
                  {formatPrice(price)}
                </td>
                <td
                  className={cn(
                    "px-4 py-2 text-right font-mono",
                    up ? "text-emerald-400" : "text-rose-400",
                  )}
                >
                  {formatPercent(t.change_24h)}
                </td>
                {!compact && (
                  <td className="px-4 py-2 text-right font-mono text-zinc-400">
                    {formatPrice(t.high_24h)}
                  </td>
                )}
                {!compact && (
                  <td className="px-4 py-2 text-right font-mono text-zinc-400">
                    {formatPrice(t.low_24h)}
                  </td>
                )}
                {!compact && (
                  <td className="px-4 py-2 text-right font-mono text-zinc-400">
                    {t.volume_24h.toLocaleString("en-US", {
                      maximumFractionDigits: 2,
                    })}
                  </td>
                )}
                <td className="px-4 py-2 text-right">
                  <Link
                    href={`/trade?pair=${encodeURIComponent(t.pair)}`}
                    className="inline-flex rounded-lg border border-zinc-700 px-3 py-1 text-xs font-medium text-indigo-300 transition-colors hover:bg-indigo-600 hover:border-indigo-600 hover:text-white"
                  >
                    Trade
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}