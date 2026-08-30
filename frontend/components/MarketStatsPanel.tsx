"use client";

import { memo } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";
import { formatNumber, formatPercent, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

interface MarketStatsPanelProps {
  pair: string;
}

export const MarketStatsPanel = memo(function MarketStatsPanel({ pair }: MarketStatsPanelProps) {
  const { data: stats } = useFetch(() => api.getMarketStats(pair), [pair]);

  if (!stats) return null;

  const up = stats.change_24h >= 0;
  const rangePct = stats.high_24h > stats.low_24h
    ? ((stats.high_24h - stats.low_24h) / stats.low_24h) * 100
    : 0;

  const items: { label: string; value: string; tone?: "up" | "down" }[] = [
    { label: "Open", value: formatPrice(stats.open_24h) },
    { label: "High", value: formatPrice(stats.high_24h) },
    { label: "Low", value: formatPrice(stats.low_24h) },
    {
      label: "24h change",
      value: formatPercent(stats.change_24h),
      tone: up ? "up" : "down",
    },
    { label: "Volume (quote)", value: formatNumber(stats.volume_24h) },
    { label: "Volume (base)", value: formatNumber(stats.volume_base_24h) },
    { label: "Trades", value: formatNumber(stats.trades_24h) },
    { label: "24h range", value: `${formatNumber(rangePct)}%` },
  ];

  return (
    <Card>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 p-5 sm:grid-cols-4">
        {items.map((it) => (
          <div key={it.label}>
            <div className="text-xs text-ink/50">{it.label}</div>
            <div
              className={cn(
                "mt-0.5 font-mono text-sm font-semibold text-ink",
                it.tone === "up" && "text-bull",
                it.tone === "down" && "text-bear",
              )}
            >
              {it.value}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
});
