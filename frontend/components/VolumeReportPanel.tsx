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
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-800 px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-zinc-100">
            Volume report
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            Traded volume by pair over the selected period
          </p>
        </div>
        {!loading && data && (
          <div className="text-right text-sm text-zinc-400">
            <span className="font-mono text-base font-semibold text-zinc-100">
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
              "cursor-pointer rounded-md px-3 py-1 text-xs font-medium transition-colors",
              days === r
                ? "bg-indigo-600 text-white"
                : "text-zinc-400 hover:text-zinc-200",
            )}
          >
            {r}d
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-xs text-zinc-500">
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
                className="border-b border-zinc-800/60 last:border-0"
              >
                <td className="px-5 py-2.5 font-semibold text-zinc-100">
                  {p.pair}
                </td>
                <td className="px-5 py-2.5 font-mono text-zinc-300">
                  {p.trades}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-emerald-400">
                  {formatUsd(p.buy_notional)}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-rose-400">
                  {formatUsd(p.sell_notional)}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-zinc-100">
                  {formatUsd(p.volume_notional)}
                </td>
              </tr>
            ))}
            {(data?.pairs ?? []).length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-5 py-8 text-center text-sm text-zinc-500"
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
