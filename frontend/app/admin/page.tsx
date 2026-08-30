"use client";

import { useMemo, useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader, Alert, Badge } from "@/components/ui";
import { formatCompact, formatUsd } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AdminStats } from "@/lib/types";

const RANGES = [7, 30, 90];

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card className="p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
        {label}
      </p>
      <p className="mt-2 text-2xl font-extrabold text-zinc-50">{value}</p>
      {hint && <p className="mt-1 text-xs text-zinc-500">{hint}</p>}
    </Card>
  );
}

function VolumeChart({ data }: { data: AdminStats["volume_timeline"] }) {
  const W = 760;
  const H = 240;
  const PAD = 12;

  const { line, area, max } = useMemo(() => {
    const values = data.map((p) => p.volume_usd);
    if (values.length === 0) return { line: "", area: "", max: 0 };
    const maxVal = Math.max(...values) || 1;
    const stepX = (W - PAD * 2) / Math.max(data.length - 1, 1);
    const linePts: string[] = [];
    const areaPts: string[] = [];
    data.forEach((p, i) => {
      const x = PAD + i * stepX;
      const y = H - PAD - (p.volume_usd / maxVal) * (H - PAD * 2);
      linePts.push(`${x.toFixed(2)},${y.toFixed(2)}`);
      areaPts.push(`${x.toFixed(2)},${y.toFixed(2)}`);
    });
    return {
      line: linePts.join(" "),
      area: `${PAD},${H - PAD} ${areaPts.join(" ")} ${W - PAD},${H - PAD}`,
      max: maxVal,
    };
  }, [data]);

  if (data.length === 0) {
    return (
      <p className="px-6 py-10 text-center text-sm text-zinc-500">
        No volume in the selected period yet.
      </p>
    );
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="mt-2 block w-full"
      role="img"
      aria-label="Traded volume over the selected period"
    >
      <defs>
        <linearGradient id="admin-volume-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#818cf8" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#818cf8" stopOpacity="0" />
        </linearGradient>
      </defs>

      {[0.25, 0.5, 0.75].map((f) => {
        const y = PAD + (H - PAD * 2) * f;
        return (
          <line
            key={f}
            x1={PAD}
            x2={W - PAD}
            y1={y}
            y2={y}
            stroke="#27272a"
            strokeDasharray="3 6"
            strokeWidth="1"
          />
        );
      })}

      <polygon points={area} fill="url(#admin-volume-fill)" />
      <polyline
        points={line}
        fill="none"
        stroke="#818cf8"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      <text x={W - PAD} y={PAD + 10} textAnchor="end" fontSize="10" fill="#a1a1aa">
        {formatCompact(max)}
      </text>
    </svg>
  );
}

function Dashboard({ currentUser }: { currentUser: { id: string; role: string } }) {
  void currentUser;
  const [days, setDays] = useState(7);
  const { data, loading, refetch } = useFetch(() => api.adminGetStats(days), [
    days,
  ]);

  const t = data?.totals;
  const timeline = data?.volume_timeline ?? [];
  const pairs = data?.volume_by_pair ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-50">Admin · Dashboard</h1>
        <div className="flex items-center gap-1">
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
      </div>

      {loading && !data ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : t ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Users"
            value={String(t.users)}
            hint={`${t.active_users} active`}
          />
          <Stat
            label="Orders"
            value={String(t.orders)}
            hint={`${t.open_orders} open`}
          />
          <Stat
            label="Trades"
            value={String(t.trades)}
            hint={`${t.today_trades} today`}
          />
          <Stat
            label="Total spot (USD)"
            value={formatUsd(t.total_spot_usd)}
          />
        </div>
      ) : null}

      <Card>
        <CardHeader
          title="Volume timeline"
          subtitle={`Traded volume per day over the last ${days} days`}
          action={
            timeline.length > 0 ? (
              <Badge tone="blue">{formatUsd(t?.today_volume_usd ?? 0)} today</Badge>
            ) : undefined
          }
        />
        <div className="px-5 pb-4">
          <VolumeChart data={timeline} />
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Volume by pair"
          subtitle={`Notional volume over the last ${days} days`}
        />
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
              {pairs.map((p) => (
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
              {pairs.length === 0 && (
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

      <div className="flex justify-end">
        <button
          onClick={() => refetch()}
          className="cursor-pointer rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800"
        >
          Refresh
        </button>
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const isAdmin = useMemo(() => user?.role === "admin", [user]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-zinc-50">Admin</h1>
        <p className="text-sm text-zinc-400">
          Platform overview: users, activity and traded volume.
        </p>
      </div>
      {!isAdmin ? (
        <Alert tone="error">Access denied. Admins only.</Alert>
      ) : (
        user && <Dashboard currentUser={user} />
      )}
    </div>
  );
}
