"use client";

import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";
import { formatUsd } from "@/lib/format";
import { cn } from "@/lib/utils";

const RANGES = [7, 30, 90];

export function VolumeReportPanel() {
  const [days, setDays] = useState(7);
  const { data, loading } = useFetch(() => api.getVolumeReport(days), [days]);

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-hairline px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-ink">
            Volume report
          </h2>
          <p className="mt-0.5 text-xs text-ink/50">
            Traded volume by pair over the selected period
          </p>
        </div>
        {!loading && data && (
          <div className="text-right text-sm text-ink/60">
            <span className="font-mono text-base font-semibold text-ink">
              {formatUsd(data.total_notional)}
            </span>{" "}
            total · {data.total_trades} trades
          </div>
        )}
      </div>

      <div className="flex items-center gap-1 px-5 py-3">
        {RANGES.map((r) => (
          <button
            key={r}
            onClick={() => setDays(r)}
            className={cn(
              "cursor-pointer rounded-[2px] px-3 py-1 text-xs font-medium transition-colors",
              days === r
                ? "bg-amber text-bg"
                : "text-ink/60 hover:text-ink",
            )}
          >
            {r}d
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-hairline text-xs text-ink/50">
              <th className="px-5 py-2 font-medium">Pair</th>
              <th className="px-5 py-2 font-medium">Trades</th>
              <th className="px-5 py-2 text-right font-medium">Buy volume</th>
              <th className="px-5 py-2 text-right font-medium">Sell volume</th>
              <th className="px-5 py-2 text-right font-medium">Total volume</th>
            </tr>
          </thead>
          <tbody>
            {(data?.pairs ?? []).map((p) => (
              <tr
                key={p.pair}
                className="border-b border-hairline/60 last:border-0"
              >
                <td className="px-5 py-2.5 font-semibold text-ink">
                  {p.pair}
                </td>
                <td className="px-5 py-2.5 font-mono text-ink/80">
                  {p.trades}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-bull">
                  {formatUsd(p.buy_notional)}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-bear">
                  {formatUsd(p.sell_notional)}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-ink">
                  {formatUsd(p.volume_notional)}
                </td>
              </tr>
            ))}
            {(data?.pairs ?? []).length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-5 py-8 text-center text-sm text-ink/50"
                >
                  No volume in the selected period yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
