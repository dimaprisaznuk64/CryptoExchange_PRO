"use client";

import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/lib/api";
import { Protected } from "@/components/Protected";
import { Card, CardHeader } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

function NotificationsPanel() {
  const { data, loading, refetch } = useFetch(() => api.getNotifications(100), []);
  const [busy, setBusy] = useState(false);

  const markRead = async (id: string) => {
    setBusy(true);
    try {
      await api.markNotificationRead(id);
      refetch();
    } finally {
      setBusy(false);
    }
  };

  const markAll = async () => {
    setBusy(true);
    try {
      await api.markAllNotificationsRead();
      refetch();
    } finally {
      setBusy(false);
    }
  };

  const items = data ?? [];
  const unreadCount = items.filter((n) => !n.is_read).length;

  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardHeader
          title="Notifications"
          subtitle={
            unreadCount > 0
              ? `${unreadCount} unread`
              : "All caught up"
          }
        />
        {unreadCount > 0 && (
          <button
            onClick={markAll}
            disabled={busy}
            className="mr-4 cursor-pointer rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800 disabled:opacity-50"
          >
            Mark all read
          </button>
        )}
      </div>
      <div className="max-h-[70vh] overflow-y-auto">
        {loading ? (
          <p className="px-5 py-8 text-center text-sm text-zinc-500">Loading…</p>
        ) : items.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-zinc-500">
            No notifications yet.
          </p>
        ) : (
          items.map((n) => (
            <div
              key={n.id}
              className={cn(
                "flex items-start justify-between gap-3 border-b border-zinc-800/60 px-5 py-3 last:border-0",
                !n.is_read && "bg-zinc-800/40",
              )}
            >
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-zinc-100">{n.title}</p>
                  {!n.is_read && (
                    <span className="rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-rose-400">
                      new
                    </span>
                  )}
                </div>
                {n.body && (
                  <p className="mt-0.5 text-xs text-zinc-500">{n.body}</p>
                )}
                <p className="mt-1 text-[11px] text-zinc-600">
                  {formatDateTime(n.created_at)}
                </p>
              </div>
              {!n.is_read && (
                <button
                  onClick={() => markRead(n.id)}
                  disabled={busy}
                  className="mt-0.5 shrink-0 cursor-pointer rounded-md border border-zinc-700 px-2 py-1 text-[11px] font-medium text-zinc-300 transition-colors hover:bg-zinc-800 disabled:opacity-50"
                >
                  Mark read
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

export default function NotificationsPage() {
  const { user } = useAuth();
  return (
    <Protected>
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-zinc-50">Notifications</h1>
          <p className="text-sm text-zinc-400">
            Activity on your orders, for {user?.username}.
          </p>
        </div>
        <NotificationsPanel />
      </div>
    </Protected>
  );
}
