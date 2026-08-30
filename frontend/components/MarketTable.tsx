"use client";

import Link from "next/link";
import type { Ticker } from "@/lib/types";
import { formatPercent, formatPrice } from "@/lib/format";
import { FlashValue } from "@/components/FlashValue";
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
          <tr className="border-b border-hairline text-xs text-ink/50">
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
                className="border-b border-hairline/60 transition-colors hover:bg-surface-2/40"
              >
                <td className="px-4 py-2 font-semibold text-ink">
                  {t.base_asset}
                  <span className="text-ink/50">/{t.quote_asset}</span>
                </td>
                <td className="px-4 py-2 text-right font-mono text-ink/90">
                  {live != null ? (
                    <FlashValue value={live} format={formatPrice} />
                  ) : (
                    formatPrice(price)
                  )}
                </td>
                <td
                  className={cn(
                    "px-4 py-2 text-right font-mono",
                    up ? "text-bull" : "text-bear",
                  )}
                >
                  {formatPercent(t.change_24h)}
                </td>
                {!compact && (
                  <td className="px-4 py-2 text-right font-mono text-ink/60">
                    {formatPrice(t.high_24h)}
                  </td>
                )}
                {!compact && (
                  <td className="px-4 py-2 text-right font-mono text-ink/60">
                    {formatPrice(t.low_24h)}
                  </td>
                )}
                {!compact && (
                  <td className="px-4 py-2 text-right font-mono text-ink/60">
                    {t.volume_24h.toLocaleString("en-US", {
                      maximumFractionDigits: 2,
                    })}
                  </td>
                )}
                <td className="px-4 py-2 text-right">
                  <Link
                    href={`/trade?pair=${encodeURIComponent(t.pair)}`}
                    className="inline-flex rounded-[2px] border border-hairline px-3 py-1 text-xs font-medium text-amber hover:border-amber hover:bg-amber hover:text-bg transition-colors"
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