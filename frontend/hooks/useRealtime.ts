"use client";

import { useEffect, useRef, useState } from "react";
import { api, getWsUrl, tokenStore } from "@/lib/api";
import type { BookSnapshot, PriceMessage } from "@/lib/types";

export type RealtimeMode = "ws" | "polling";

export interface RealtimeState {
  connected: boolean;
  mode: RealtimeMode;
  hello: string | null;
  prices: Record<string, number>;
  book: BookSnapshot | null;
  lastUpdate: number;
}

// Backend streams price ticks every ~50ms (20/sec). Re-rendering the whole
// trade page that often (heavy SVG candlestick chart, order book, forms)
// overloads the DOM/CPU on mobile within seconds and crashes the tab.
// We buffer incoming messages in a ref and flush to React state on a fixed
// interval instead, so the UI updates smoothly without a render storm.
const FLUSH_INTERVAL_MS = 250;

// Render free kills long-lived WebSockets, so after a bounded number of failed
// connection attempts we degrade to REST polling of tickers + order book.
const MAX_RECONNECTS = 3;
const POLL_INTERVAL_MS = 2000;

export function useRealtimePrices(pairs: string[]) {
  const [state, setState] = useState<RealtimeState>({
    connected: false,
    mode: "ws",
    hello: null,
    prices: {},
    book: null,
    lastUpdate: 0,
  });

  const pairsKey = pairs.join(",");
  const [reconnect, setReconnect] = useState(0);
  const hasToken = typeof window !== "undefined" && Boolean(tokenStore.getAccess());

  // Survives effect restarts (setReconnect re-runs the effect), so MAX_RECONNECTS
  // is actually honoured instead of resetting to 0 on every reconnect and
  // spinning up an endless WebSocket loop that crashes the tab.
  const connectAttemptsRef = useRef(0);

  // Polling is driven from inside the effect via an interval; we keep a ref so
  // the cleanup can always tear it down regardless of which mode is active.
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Pending updates buffered between flushes.
  const pendingRef = useRef<{
    connected?: boolean;
    mode?: RealtimeMode;
    hello?: string;
    prices?: Record<string, number>;
    book?: BookSnapshot;
    dirty: boolean;
  }>({ dirty: false });

  useEffect(() => {
    if (pairs.length === 0) return;
    if (!tokenStore.getAccess()) return;

    let ws: WebSocket | null = null;
    let closed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const stopPolling = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    const startPolling = () => {
      stopPolling();
      pendingRef.current.connected = true;
      pendingRef.current.mode = "polling";
      pendingRef.current.dirty = true;

      const tick = async () => {
        try {
          const tickers = await api.getTickers();
          const prices: Record<string, number> = {};
          for (const t of tickers) {
            if (pairs.includes(t.pair)) prices[t.pair] = t.last;
          }
          if (Object.keys(prices).length > 0) {
            pendingRef.current.prices = {
              ...pendingRef.current.prices,
              ...prices,
            };
            pendingRef.current.dirty = true;
          }
        } catch {
          /* transient network error — retry next tick */
        }

        // Rest the order book ladder too.
        if (pairs.length > 0) {
          try {
            const book = await api.getDepth(pairs[0]);
            pendingRef.current.book = book;
            pendingRef.current.dirty = true;
          } catch {
            /* retry next tick */
          }
        }
      };

      void tick();
      pollRef.current = setInterval(tick, POLL_INTERVAL_MS);
    };

    const flushTimer = setInterval(() => {
      const pending = pendingRef.current;
      if (!pending.dirty) return;
      setState((s) => ({
        connected: pending.connected ?? s.connected,
        mode: pending.mode ?? s.mode,
        hello: pending.hello ?? s.hello,
        prices: pending.prices ? { ...s.prices, ...pending.prices } : s.prices,
        book: pending.book ?? s.book,
        lastUpdate: Date.now(),
      }));
      pendingRef.current = { dirty: false };
    }, FLUSH_INTERVAL_MS);

    const connect = async () => {
      if (closed) return;
      connectAttemptsRef.current += 1;
      if (connectAttemptsRef.current > MAX_RECONNECTS) {
        // Give up on WS for good and fall back to REST polling.
        setState((s) => ({ ...s, connected: false }));
        startPolling();
        return;
      }
      // Fetch a short-lived, single-use ticket instead of putting the JWT
      // in the WebSocket URL (which would leak into logs/history).
      let url: string | null;
      try {
        url = await getWsUrl(pairs);
      } catch {
        url = null;
      }
      if (!url) {
        startPolling();
        return;
      }
      let socket: WebSocket;
      try {
        socket = new WebSocket(url);
      } catch {
        // Invalid/blocked WebSocket URL — never reachable, so stop retrying
        // and fall back to REST polling immediately.
        startPolling();
        return;
      }
      ws = socket;

      ws.onopen = () => {
        connectAttemptsRef.current = 0;
        stopPolling();
        pendingRef.current.connected = true;
        pendingRef.current.mode = "ws";
        pendingRef.current.dirty = true;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as {
            type: string;
            [key: string]: unknown;
          };
          if (msg.type === "hello") {
            pendingRef.current.hello = String(msg.user ?? "");
            pendingRef.current.dirty = true;
          } else if (msg.type === "price") {
            const price = msg as unknown as PriceMessage;
            pendingRef.current.prices = {
              ...pendingRef.current.prices,
              [price.pair]: price.price,
            };
            pendingRef.current.dirty = true;
          } else if (msg.type === "book") {
            pendingRef.current.book = msg as unknown as BookSnapshot;
            pendingRef.current.dirty = true;
          }
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (
          !closed &&
          !reconnectTimer &&
          connectAttemptsRef.current < MAX_RECONNECTS
        ) {
          const delay = Math.min(1000 * 2 ** (connectAttemptsRef.current - 1), 15000);
          reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            setReconnect((r) => r + 1);
          }, delay);
        } else if (!closed) {
          // Connection was never established; stop retrying and poll instead.
          startPolling();
        }
      };

      ws.onerror = () => {
        try {
          ws?.close();
        } catch {
          /* ignore */
        }
      };
    };

    void connect();

    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      clearInterval(flushTimer);
      stopPolling();
      ws?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pairsKey, reconnect, hasToken]);

  return { ...state, hasToken };
}
