"use client";

import { useFetch } from "@/hooks/useFetch";
import { api } from "@/lib/api";
import { Protected } from "@/components/Protected";
import { Card, CardHeader, Spinner } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { PortfolioChart } from "@/components/PortfolioChart";
import { VolumeReportPanel } from "@/components/VolumeReportPanel";
import {
  formatDateTime,
  formatNumber,
  formatUsd,
} from "@/lib/format";
import { cn } from "@/lib/utils";

function PortfolioPanel() {
  const { data, loading, error } = useFetch(() => api.getPortfolio(), []);
  const trades = useFetch(() => api.getRecentTrades(10), []);
  const history = useFetch(() => api.getPortfolioHistory(7), []);

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    );
  }

  if (error || !data) {
    return <p className="py-16 text-center text-sm text-rose-400">{error}</p>;
  }

  const nonZero = data.items.filter((i) => i.balance > 0);

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Total portfolio value
            </p>
            <p className="mt-1 text-3xl font-extrabold text-zinc-50">
              {formatUsd(data.total_usd)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Unrealized P&L
            </p>
            {nonZero.length > 0 && (
              <p
                className={cn(
                  "mt-1 text-xl font-bold",
                  nonZero.reduce((s, i) => s + i.pnl_usd, 0) >= 0
                    ? "text-emerald-400"
                    : "text-rose-400",
                )}
              >
                {formatUsd(
                  nonZero.reduce((s, i) => s + i.pnl_usd, 0),
                )}
              </p>
            )}
          </div>
        </div>
      </Card>

      {history.data && history.data.length > 0 && (
        <Card className="overflow-hidden">
          <CardHeader
            title="Portfolio history"
            subtitle="Total portfolio value over the last 7 days"
          />
          <PortfolioChart data={history.data} />
        </Card>
      )}

      <Card>
        <CardHeader
          title="Assets"
          subtitle="Current USD valuation and unrealized profit/loss"
        />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                <th className="px-5 py-2 font-medium">Asset</th>
                <th className="px-5 py-2 text-right font-medium">Balance</th>
                <th className="px-5 py-2 text-right font-medium">Price (USD)</th>
                <th className="px-5 py-2 text-right font-medium">Value (USD)</th>
                <th className="px-5 py-2 text-right font-medium">Unrealized P&L</th>
              </tr>
            </thead>
            <tbody>
              {nonZero.map((item) => (
                <tr
                  key={item.asset}
                  className="border-b border-zinc-800/60 last:border-0"
                >
                  <td className="px-5 py-2.5 font-semibold text-zinc-100">
                    {item.asset}
                  </td>
                  <td className="px-5 py-2.5 text-right font-mono text-zinc-300">
                    {formatNumber(item.balance)}
                  </td>
                  <td className="px-5 py-2.5 text-right font-mono text-zinc-300">
                    {formatNumber(item.usd_price)}
                  </td>
                  <td className="px-5 py-2.5 text-right font-mono text-zinc-200">
                    {formatUsd(item.value_usd)}
                  </td>
                  <td
                    className={cn(
                      "px-5 py-2.5 text-right font-mono",
                      item.pnl_usd >= 0 ? "text-emerald-400" : "text-rose-400",
                    )}
                  >
                    {formatUsd(item.pnl_usd)}
                  </td>
                </tr>
              ))}
              {nonZero.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-5 py-8 text-center text-sm text-zinc-500"
                  >
                    No assets yet.{" "}
                    <a href="/wallets" className="text-indigo-400">
                      Deposit funds
                    </a>{" "}
                    or{" "}
                    <a href="/trade" className="text-indigo-400">
                      place an order
                    </a>
                    .
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardHeader title="Recent trades" />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                <th className="px-5 py-2 font-medium">Time</th>
                <th className="px-5 py-2 font-medium">Pair</th>
                <th className="px-5 py-2 font-medium">Side</th>
                <th className="px-5 py-2 text-right font-medium">Price</th>
                <th className="px-5 py-2 text-right font-medium">Qty</th>
                <th className="px-5 py-2 text-right font-medium">Notional</th>
              </tr>
            </thead>
            <tbody>
              {(trades.data ?? []).map((t) => (
                <tr
                  key={t.id}
                  className="border-b border-zinc-800/60 last:border-0"
                >
                  <td className="px-5 py-2 text-xs text-zinc-500">
                    {formatDateTime(t.created_at)}
                  </td>
                  <td className="px-5 py-2 font-medium text-zinc-200">
                    {t.pair}
                  </td>
                  <td className="px-5 py-2">
                    <span
                      className={cn(
                        "rounded px-2 py-0.5 text-xs font-semibold",
                        t.side === "buy"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-rose-500/10 text-rose-400",
                      )}
                    >
                      {t.side}
                    </span>
                  </td>
                  <td className="px-5 py-2 text-right font-mono text-zinc-300">
                    {formatNumber(t.price)}
                  </td>
                  <td className="px-5 py-2 text-right font-mono text-zinc-300">
                    {formatNumber(t.qty)}
                  </td>
                  <td className="px-5 py-2 text-right font-mono text-zinc-200">
                    {formatUsd(t.notional)}
                  </td>
                </tr>
              ))}
              {(trades.data ?? []).length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-8 text-center text-sm text-zinc-500"
                  >
                    No trades yet. Visit the{" "}
                    <a href="/trade" className="text-indigo-400">
                      trading page
                    </a>{" "}
                    to place your first order.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <VolumeReportPanel />
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  return (
    <Protected>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-zinc-50">Dashboard</h1>
          <p className="text-sm text-zinc-400">
            Welcome back, {user?.username}. Here is your portfolio at a glance.
          </p>
        </div>
        <PortfolioPanel />
      </div>
    </Protected>
  );
}