"use client";

import { useMemo, useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader, Input, Button, Badge, Alert, Select } from "@/components/ui";
import { formatDateTime, formatUsd } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AdminUserDetail } from "@/lib/types";

const ROLES = ["user", "trader", "manager", "admin"];

function roleTone(role: string): "default" | "green" | "red" | "amber" | "blue" {
  if (role === "admin") return "blue";
  if (role === "manager") return "amber";
  if (role === "trader") return "green";
  return "default";
}

function DetailPanel({
  detail,
  isSelf,
  onUpdate,
}: {
  detail: AdminUserDetail;
  isSelf: boolean;
  onUpdate: (body: { role?: string; is_active?: boolean }) => Promise<void>;
}) {
  const [roleDraft, setRoleDraft] = useState(detail.role);
  const [busy, setBusy] = useState(false);

  return (
    <Card>
      <CardHeader
        title={detail.username}
        subtitle={`${detail.email} · id ${detail.id}`}
      />
      <div className="grid gap-4 p-5 sm:grid-cols-2">
        <div>
          <div className="flex items-center gap-2">
            <Badge tone={roleTone(detail.role)}>{detail.role}</Badge>
            {detail.is_active ? (
              <Badge tone="green">active</Badge>
            ) : (
              <Badge tone="red">blocked</Badge>
            )}
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt className="text-zinc-500">Total USD</dt>
            <dd className="text-right font-mono text-zinc-100">
              {formatUsd(detail.total_usd)}
            </dd>
            <dt className="text-zinc-500">Orders</dt>
            <dd className="text-right font-mono text-zinc-100">
              {detail.order_count}
            </dd>
            <dt className="text-zinc-500">Trades</dt>
            <dd className="text-right font-mono text-zinc-100">
              {detail.trade_count}
            </dd>
            <dt className="text-zinc-500">Registered</dt>
            <dd className="text-right font-mono text-zinc-100">
              {formatDateTime(detail.created_at)}
            </dd>
          </dl>
        </div>

        <div className="space-y-3">
          <Select
            label="Role"
            value={roleDraft}
            disabled={isSelf}
            onChange={(e) => setRoleDraft(e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </Select>
          <div className="flex gap-2 pt-1">
            <Button
              size="sm"
              variant={detail.is_active ? "danger" : "success"}
              disabled={isSelf || busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await onUpdate({ is_active: !detail.is_active });
                } finally {
                  setBusy(false);
                }
              }}
            >
              {detail.is_active ? "Block" : "Unblock"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={isSelf || busy || roleDraft === detail.role}
              onClick={async () => {
                setBusy(true);
                try {
                  await onUpdate({ role: roleDraft });
                } finally {
                  setBusy(false);
                }
              }}
            >
              Save role
            </Button>
          </div>
          {isSelf && (
            <p className="text-xs text-zinc-500">
              You cannot change your own role or block yourself.
            </p>
          )}
        </div>
      </div>

      <div className="overflow-x-auto border-t border-zinc-800">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-xs text-zinc-500">
              <th className="px-5 py-2 font-medium">Asset</th>
              <th className="px-5 py-2 font-medium">Type</th>
              <th className="px-5 py-2 text-right font-medium">Balance</th>
              <th className="px-5 py-2 text-right font-medium">Available</th>
              <th className="px-5 py-2 text-right font-medium">Frozen</th>
            </tr>
          </thead>
          <tbody>
            {detail.wallets.map((w) => (
              <tr key={`${w.asset}-${w.type}`} className="border-b border-zinc-800/60 last:border-0">
                <td className="px-5 py-2.5 font-semibold text-zinc-100">{w.asset}</td>
                <td className="px-5 py-2.5 text-zinc-300">{w.type}</td>
                <td className="px-5 py-2.5 text-right font-mono text-zinc-200">
                  {w.balance}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-zinc-300">
                  {w.available}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-zinc-300">
                  {w.frozen}
                </td>
              </tr>
            ))}
            {detail.wallets.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-6 text-center text-sm text-zinc-500">
                  No wallets yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function UsersManager({ currentUser }: { currentUser: { id: string; role: string } }) {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const list = useFetch(
    () => api.adminListUsers({ search: search || undefined, limit: 100 }),
    [search],
  );
  const detail = useFetch(
    () => (selectedId ? api.adminGetUser(selectedId) : Promise.resolve(null as unknown as AdminUserDetail)),
    [selectedId],
  );

  const onUpdate = async (body: { role?: string; is_active?: boolean }) => {
    if (!selectedId) return;
    try {
      await api.adminUpdateUser(selectedId, body);
      list.refetch();
      detail.refetch();
    } catch {
      // surface via detail fetch next time; keep simple
    }
  };

  const selected = detail.data;
  const isSelf = selectedId === currentUser.id;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Users" subtitle={`${list.data?.total ?? 0} total`} />
        <div className="p-5">
          <Input
            placeholder="Search by email or username…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                <th className="px-5 py-2 font-medium">User</th>
                <th className="px-5 py-2 font-medium">Role</th>
                <th className="px-5 py-2 font-medium">Status</th>
                <th className="px-5 py-2 text-right font-medium">Total USD</th>
                <th className="px-5 py-2 text-right font-medium">Trades</th>
              </tr>
            </thead>
            <tbody>
              {(list.data?.users ?? []).map((u) => (
                <tr
                  key={u.id}
                  onClick={() => setSelectedId(u.id)}
                  className={cn(
                    "cursor-pointer border-b border-zinc-800/60 transition-colors last:border-0 hover:bg-zinc-800/40",
                    selectedId === u.id && "bg-zinc-800/50",
                  )}
                >
                  <td className="px-5 py-2.5">
                    <p className="font-medium text-zinc-100">{u.username}</p>
                    <p className="text-xs text-zinc-500">{u.email}</p>
                  </td>
                  <td className="px-5 py-2.5">
                    <Badge tone={roleTone(u.role)}>{u.role}</Badge>
                  </td>
                  <td className="px-5 py-2.5">
                    {u.is_active ? (
                      <Badge tone="green">active</Badge>
                    ) : (
                      <Badge tone="red">blocked</Badge>
                    )}
                  </td>
                  <td className="px-5 py-2.5 text-right font-mono text-zinc-200">
                    {formatUsd(u.total_usd)}
                  </td>
                  <td className="px-5 py-2.5 text-right font-mono text-zinc-300">
                    {u.trade_count}
                  </td>
                </tr>
              ))}
              {list.data && list.data.users.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-sm text-zinc-500">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {selected && (
        <DetailPanel detail={selected} isSelf={isSelf} onUpdate={onUpdate} />
      )}
    </div>
  );
}

export default function AdminUsersPage() {
  const { user } = useAuth();
  const isAdmin = useMemo(() => user?.role === "admin", [user]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-zinc-50">Admin · Users</h1>
        <p className="text-sm text-zinc-400">
          Manage accounts: view balances, block/unblock, and change roles.
        </p>
      </div>
      {!isAdmin ? (
        <Alert tone="error">Access denied. Admins only.</Alert>
      ) : (
        user && <UsersManager currentUser={user} />
      )}
    </div>
  );
}
