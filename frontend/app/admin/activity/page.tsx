"use client";

import { useMemo, useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader, Input, Badge, Alert, Select } from "@/components/ui";
import { formatDateTime, formatNumber, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

type Tab = "orders" | "trades";

const ORDER_STATUSES = [
  { value: "", label: "All statuses" },
  { value: "open", label: "Open" },
  { value: "filled", label: "Filled" },
  { value: "partially_filled", label: "Partially filled" },
  { value: "cancelled", label: "Cancelled" },
  { value: "rejected", label: "Rejected" },
];

const ORDER_TYPES = [
  { value: "", label: "All types" },
  { value: "market", label: "Market" },
  { value: "limit", label: "Limit" },
  { value: "take_profit", label: "Take profit" },
  { value: "stop_loss", label: "Stop loss" },
];

function sideTone(side: string): "default" | "green" | "red" {
  return side === "buy" ? "green" : "red";
}

function statusTone(
  status: string,
): "default" | "green" | "red" | "amber" | "blue" {
  if (status === "filled") return "green";
  if (status === "open") return "blue";
  if (status === "partially_filled") return "amber";
  if (status === "rejected") return "red";
  return "default";
}

function ActivityTabs({ tab, onChange }: { tab: Tab; onChange: (t: Tab) => void }) {
  const tabs: { key: Tab; label: string }[] = [
    { key: "orders", label: "Orders" },
    { key: "trades", label: "Trades" },
  ];
  return (
    <div className="inline-flex rounded-lg border border-zinc-800 bg-zinc-900 p-1">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={cn(
            "rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
            tab === t.key
              ? "bg-indigo-600 text-white"
              : "text-zinc-400 hover:text-zinc-200",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function ActivityManager() {
  const [tab, setTab] = useState<Tab>("orders");
  const [user, setUser] = useState("");
  const [pair, setPair] = useState("");
  const [side, setSide] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");

  const orders = useFetch(
    () =>
      api.adminListOrders({
        user: user || undefined,
        pair: pair || undefined,
        side: side || undefined,
        status: status || undefined,
        type: type || undefined,
        limit: 200,
      }),
    [user, pair, side, status, type],
  );
  const trades = useFetch(
    () =>
      api.adminListTrades({
        user: user || undefined,
        pair: pair || undefined,
        side: side || undefined,
        limit: 200,
      }),
    [user, pair, side],
  );

  const renderTitle = (label: string, total: number) => (
    <CardHeader title={label} subtitle={`${total} total`} />
  );

  return (
    <div className="space-y-6">
      <ActivityTabs tab={tab} onChange={setTab} />

      <Card>
        <CardHeader title="Filters" />
        <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
          <Input
            placeholder="User (email / username)…"
            value={user}
            onChange={(e) => setUser(e.target.value)}
          />
          <Input
            placeholder="Pair, e.g. BTC/USDT"
            value={pair}
            onChange={(e) => setPair(e.target.value)}
          />
          <Select
            value={side}
            onChange={(e) => setSide(e.target.value)}
          >
            <option value="">All sides</option>
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </Select>
          {tab === "orders" && (
            <Select
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              {ORDER_TYPES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          )}
          {tab === "orders" ? (
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              {ORDER_STATUSES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          ) : (
            <div className="hidden lg:block" />
          )}
        </div>
      </Card>

      {tab === "orders" ? (
        <Card>
          {orders.data && renderTitle("Orders", orders.data.total)}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                  <th className="px-5 py-2 font-medium">User</th>
                  <th className="px-5 py-2 font-medium">Pair</th>
                  <th className="px-5 py-2 font-medium">Side</th>
                  <th className="px-5 py-2 font-medium">Type</th>
                  <th className="px-5 py-2 text-right font-medium">Price</th>
                  <th className="px-5 py-2 text-right font-medium">Filled</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                  <th className="px-5 py-2 text-right font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {(orders.data?.orders ?? []).map((o) => (
                  <tr key={o.id} className="border-b border-zinc-800/60 last:border-0">
                    <td className="px-5 py-2.5">
                      <p className="font-medium text-zinc-100">{o.user_username}</p>
                      <p className="text-xs text-zinc-500">{o.user_email}</p>
                    </td>
                    <td className="px-5 py-2.5 font-mono text-zinc-200">{o.pair}</td>
                    <td className="px-5 py-2.5">
                      <Badge tone={sideTone(o.side)}>{o.side}</Badge>
                    </td>
                    <td className="px-5 py-2.5 text-zinc-300">{o.type}</td>
                    <td className="px-5 py-2.5 text-right font-mono text-zinc-200">
                      {o.price == null ? "—" : formatPrice(o.price)}
                    </td>
                    <td className="px-5 py-2.5 text-right font-mono text-zinc-300">
                      {formatNumber(o.filled_qty, 6)} / {formatNumber(o.qty, 6)}
                    </td>
                    <td className="px-5 py-2.5">
                      <Badge tone={statusTone(o.status)}>{o.status}</Badge>
                    </td>
                    <td className="px-5 py-2.5 text-right text-zinc-400">
                      {formatDateTime(o.created_at)}
                    </td>
                  </tr>
                ))}
                {orders.data && orders.data.orders.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-5 py-8 text-center text-sm text-zinc-500">
                      No orders found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card>
          {trades.data && renderTitle("Trades", trades.data.total)}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                  <th className="px-5 py-2 font-medium">User</th>
                  <th className="px-5 py-2 font-medium">Pair</th>
                  <th className="px-5 py-2 font-medium">Side</th>
                  <th className="px-5 py-2 text-right font-medium">Price</th>
                  <th className="px-5 py-2 text-right font-medium">Qty</th>
                  <th className="px-5 py-2 text-right font-medium">Notional</th>
                  <th className="px-5 py-2 text-right font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {(trades.data?.trades ?? []).map((t) => (
                  <tr key={t.id} className="border-b border-zinc-800/60 last:border-0">
                    <td className="px-5 py-2.5">
                      <p className="font-medium text-zinc-100">{t.user_username}</p>
                      <p className="text-xs text-zinc-500">{t.user_email}</p>
                    </td>
                    <td className="px-5 py-2.5 font-mono text-zinc-200">{t.pair}</td>
                    <td className="px-5 py-2.5">
                      <Badge tone={sideTone(t.side)}>{t.side}</Badge>
                    </td>
                    <td className="px-5 py-2.5 text-right font-mono text-zinc-200">
                      {formatPrice(t.price)}
                    </td>
                    <td className="px-5 py-2.5 text-right font-mono text-zinc-200">
                      {formatNumber(t.qty, 6)}
                    </td>
                    <td className="px-5 py-2.5 text-right font-mono text-zinc-200">
                      {formatNumber(t.notional, 2)}
                    </td>
                    <td className="px-5 py-2.5 text-right text-zinc-400">
                      {formatDateTime(t.created_at)}
                    </td>
                  </tr>
                ))}
                {trades.data && trades.data.trades.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-5 py-8 text-center text-sm text-zinc-500">
                      No trades found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

export default function AdminActivityPage() {
  const { user } = useAuth();
  const isAdmin = useMemo(() => user?.role === "admin", [user]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-zinc-50">Admin · Activity</h1>
        <p className="text-sm text-zinc-400">
          Browse all orders and trades across every user.
        </p>
      </div>
      {!isAdmin ? (
        <Alert tone="error">Access denied. Admins only.</Alert>
      ) : (
        <ActivityManager />
      )}
    </div>
  );
}
