"use client";

import { useCallback, useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/lib/api";
import { Protected } from "@/components/Protected";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Input,
  Select,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { formatDateTime, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

function WalletPanel() {
  const [mode, setMode] = useState<"deposit" | "withdraw">("deposit");
  const [asset, setAsset] = useState("USD");
  const [amount, setAmount] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const balances = useFetch(() => api.getBalances(), []);
  const transactions = useFetch(() => api.getTransactions(50), []);

  const refresh = useCallback(() => {
    balances.refetch();
    transactions.refetch();
  }, [balances, transactions]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);

    const amt = Number(amount);
    if (!Number.isFinite(amt) || amt <= 0) {
      setFormError("Enter a valid positive amount");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "deposit") await api.deposit(asset, amt);
      else await api.withdraw(asset, amt);
      setFormSuccess(
        mode === "deposit"
          ? `Deposited ${formatNumber(amt)} ${asset}`
          : `Withdrew ${formatNumber(amt)} ${asset}`,
      );
      setAmount("");
      await refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Operation failed");
    } finally {
      setSubmitting(false);
    }
  };

  const assetOptions = (balances.data?.items ?? []).map((b) => b.asset_symbol);

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <Card>
          <CardHeader title="Balances" subtitle="Spot wallet balances" />
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                  <th className="px-5 py-2 font-medium">Asset</th>
                  <th className="px-5 py-2 text-right font-medium">Balance</th>
                  <th className="px-5 py-2 text-right font-medium">Available</th>
                  <th className="px-5 py-2 text-right font-medium">Frozen</th>
                </tr>
              </thead>
              <tbody>
                {(balances.data?.items ?? []).map((b) => (
                  <tr
                    key={b.asset_symbol}
                    className="border-b border-zinc-800/60 last:border-0"
                  >
                    <td className="px-5 py-3 font-semibold text-zinc-100">
                      {b.asset_symbol}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-zinc-200">
                      {formatNumber(b.balance)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-emerald-400">
                      {formatNumber(b.available)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-amber-400">
                      {formatNumber(b.frozen)}
                    </td>
                  </tr>
                ))}
                {(balances.data?.items ?? []).length === 0 && (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-5 py-8 text-center text-sm text-zinc-500"
                    >
                      No balances.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <CardHeader title="Transactions" subtitle="Deposit / withdrawal ledger" />
          <div className="max-h-[420px] overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-zinc-900">
                <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                  <th className="px-5 py-2 font-medium">Time</th>
                  <th className="px-5 py-2 font-medium">Type</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                  <th className="px-5 py-2 text-right font-medium">Delta</th>
                  <th className="px-5 py-2 text-right font-medium">Note</th>
                </tr>
              </thead>
              <tbody>
                {(transactions.data ?? []).map((t) => {
                  const typeLabel = t.type.replace("_", " ");
                  const positive = t.delta > 0;
                  return (
                    <tr
                      key={t.id}
                      className="border-b border-zinc-800/60 last:border-0"
                    >
                      <td className="px-5 py-2 text-xs text-zinc-500">
                        {formatDateTime(t.created_at)}
                      </td>
                      <td className="px-5 py-2 text-xs capitalize text-zinc-300">
                        {typeLabel}
                      </td>
                      <td className="px-5 py-2">
                        <Badge tone={t.status === "completed" ? "green" : "amber"}>
                          {t.status}
                        </Badge>
                      </td>
                      <td
                        className={cn(
                          "px-5 py-2 text-right font-mono",
                          positive ? "text-emerald-400" : "text-rose-400",
                        )}
                      >
                        {positive ? "+" : ""}
                        {formatNumber(t.delta)} {t.asset_symbol ?? ""}
                      </td>
                      <td className="px-5 py-2 text-right text-xs text-zinc-500">
                        {t.note ?? "-"}
                      </td>
                    </tr>
                  );
                })}
                {(transactions.data ?? []).length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-5 py-8 text-center text-sm text-zinc-500"
                    >
                      No transactions yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Card className="h-fit">
        <CardHeader
          title="Transfer"
          action={
            <div className="flex rounded-lg border border-zinc-700 p-0.5">
              {(["deposit", "withdraw"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => {
                    setMode(m);
                    setFormError(null);
                    setFormSuccess(null);
                  }}
                  className={cn(
                    "cursor-pointer rounded-md px-3 py-1 text-xs font-medium capitalize transition-colors",
                    mode === m
                      ? "bg-indigo-600 text-white"
                      : "text-zinc-400 hover:text-zinc-200",
                  )}
                >
                  {m}
                </button>
              ))}
            </div>
          }
        />
        <form onSubmit={handleSubmit} className="space-y-4 p-5">
          {formError && <Alert>{formError}</Alert>}
          {formSuccess && <Alert tone="success">{formSuccess}</Alert>}

          <Select
            label="Asset"
            value={asset}
            onChange={(e) => setAsset(e.target.value)}
          >
            {assetOptions.length > 0 ? (
              assetOptions.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))
            ) : (
              <option value="USD">USD</option>
            )}
          </Select>

          <Input
            label="Amount"
            type="number"
            inputMode="decimal"
            step="any"
            min="0"
            required
            placeholder="0.00"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />

          <Button
            type="submit"
            variant={mode === "deposit" ? "success" : "danger"}
            size="lg"
            loading={submitting}
            className="w-full capitalize"
          >
            {mode}
          </Button>
        </form>
      </Card>
    </div>
  );
}

export default function WalletsPage() {
  const { user } = useAuth();
  return (
    <Protected>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-zinc-50">Wallets</h1>
          <p className="text-sm text-zinc-400">
            Manage spot balances and deposit / withdraw funds for{" "}
            {user?.username}.
          </p>
        </div>
        <WalletPanel />
      </div>
    </Protected>
  );
}