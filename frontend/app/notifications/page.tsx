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
            className="mr-4 cursor-pointer rounded-[2px] border border-hairline px-3 py-1.5 text-xs font-medium text-ink/80 transition-colors hover:bg-surface-2 disabled:opacity-50"
          >
            Mark all read
          </button>
        )}
      </div>
      <div className="max-h-[70vh] overflow-y-auto">
        {loading ? (
          <p className="px-5 py-8 text-center text-sm text-ink/50">Loading…</p>
        ) : items.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-ink/50">
            No notifications yet.
          </p>
        ) : (
          items.map((n) => (
            <div
              key={n.id}
              className={cn(
                "flex items-start justify-between gap-3 border-b border-hairline/60 px-5 py-3 last:border-0",
                !n.is_read && "bg-surface-2/40",
              )}
            >
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-ink">{n.title}</p>
                  {!n.is_read && (
                    <span className="rounded bg-bear/15 px-1.5 py-0.5 text-[10px] font-semibold text-bear">
                      new
                    </span>
                  )}
                </div>
                {n.body && (
                  <p className="mt-0.5 text-xs text-ink/50">{n.body}</p>
                )}
                <p className="mt-1 text-[11px] text-ink/40">
                  {formatDateTime(n.created_at)}
                </p>
              </div>
              {!n.is_read && (
                <button
                  onClick={() => markRead(n.id)}
                  disabled={busy}
                  className="mt-0.5 shrink-0 cursor-pointer rounded-[2px] border border-hairline px-2 py-1 text-[11px] font-medium text-ink/80 transition-colors hover:bg-surface-2 disabled:opacity-50"
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
          <h1 className="text-2xl font-bold text-ink">Notifications</h1>
          <p className="text-sm text-ink/60">
            Activity on your orders, for {user?.username}.
          </p>
        </div>
        <NotificationsPanel />
      </div>
    </Protected>
  );
}
