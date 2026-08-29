"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { formatDateTime } from "@/lib/format";
import type { Notification } from "@/lib/types";
import { cn } from "@/lib/utils";

export function NotificationsBell() {
  const { isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);

  const load = useCallback(async () => {
    try {
      const [notif, cnt] = await Promise.all([
        api.getNotifications(12),
        api.getUnreadCount(),
      ]);
      setItems(notif);
      setUnread(cnt.count);
    } catch {
      // ignore transient fetch errors
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    const refreshUnread = () => {
      api
        .getUnreadCount()
        .then((c) => setUnread(c.count))
        .catch(() => undefined);
    };
    refreshUnread();
    const t = setInterval(refreshUnread, 15000);
    return () => clearInterval(t);
  }, [isAuthenticated]);

  const handleToggle = async () => {
    const next = !open;
    setOpen(next);
    if (next) {
      await load();
      if (unread > 0) {
        await api.markAllNotificationsRead().catch(() => undefined);
        setUnread(0);
      }
    }
  };

  return (
    <div className="relative">
      <button
        onClick={handleToggle}
        aria-label="Notifications"
        className="relative cursor-pointer rounded-lg p-2 text-zinc-400 transition-colors hover:text-zinc-200"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900 shadow-xl">
          <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
            <h3 className="text-sm font-semibold text-zinc-100">Notifications</h3>
            <Link href="/notifications" className="text-xs font-medium text-indigo-400">
              View all
            </Link>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-zinc-500">
                No notifications yet.
              </p>
            ) : (
              items.map((n) => (
                <div
                  key={n.id}
                  className={cn(
                    "border-b border-zinc-800/60 px-4 py-3 last:border-0",
                    !n.is_read && "bg-zinc-800/40",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-zinc-100">{n.title}</p>
                    <span className="text-[10px] text-zinc-500">
                      {formatDateTime(n.created_at)}
                    </span>
                  </div>
                  {n.body && (
                    <p className="mt-0.5 text-xs text-zinc-500">{n.body}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
