"use client";

import { useEffect, useRef, useState } from "react";
import { api, getWsUrl, tokenStore } from "@/lib/api";
import type { BookSnapshot, MarketTrade, PriceMessage } from "@/lib/types";

export type RealtimeMode = "ws" | "polling";

export interface RealtimeState {
  connected: boolean;
  mode: RealtimeMode;
  hello: string | null;
  prices: Record<string, number>;
  book: BookSnapshot | null;
  trades: Record<string, MarketTrade[]>;
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

// Heartbeat: the backend sends {"type":"ping"} every ~15s and drops sockets
// that don't answer. We also keep a client-side staleness watch — if a server
// fails to deliver anything for STALE_AFTER_MS (half-open TCP on free-tier
// hosts), we close the socket ourselves so reconnect logic kicks in.
const PONG_RESPONSE = JSON.stringify({ type: "pong" });
const STALE_AFTER_MS = 20000;
const STALE_CHECK_MS = 10000;

export function useRealtimePrices(pairs: string[]) {
  const [state, setState] = useState<RealtimeState>({
    connected: false,
    mode: "ws",
    hello: null,
    prices: {},
    book: null,
    trades: {},
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
    trades?: Record<string, MarketTrade[]>;
    dirty: boolean;
  }>({ dirty: false });

  // Timestamp of the last frame received over the socket; used by the
  // staleness watcher to detect silently-dead connections.
  const lastMessageRef = useRef(0);

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
          try {
            const marketTrades = await api.getMarketTrades(pairs[0], 30);
            pendingRef.current.trades = {
              ...pendingRef.current.trades,
              [pairs[0]]: marketTrades,
            };
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
        trades: pending.trades ? { ...s.trades, ...pending.trades } : s.trades,
        lastUpdate: Date.now(),
      }));
      pendingRef.current = { dirty: false };
    }, FLUSH_INTERVAL_MS);

    // Client-side staleness watch: if an open socket delivers nothing for a
    // while, force it closed so the reconnect/backoff path takes over instead
    // of leaving the UI frozen on a half-open connection.
    const staleTimer = setInterval(() => {
      if (
        ws &&
        !closed &&
        ws.readyState === WebSocket.OPEN &&
        Date.now() - lastMessageRef.current > STALE_AFTER_MS
      ) {
        lastMessageRef.current = Date.now();
        ws.close();
      }
    }, STALE_CHECK_MS);

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
          lastMessageRef.current = Date.now();
          if (msg.type === "ping") {
            // Answer the backend heartbeat so it doesn't drop us as dead.
            ws?.send(PONG_RESPONSE);
          } else if (msg.type === "hello") {
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
          } else if (msg.type === "trades") {
            const trades = msg as unknown as {
              pair: string;
              trades: MarketTrade[];
            };
            pendingRef.current.trades = {
              ...pendingRef.current.trades,
              [trades.pair]: trades.trades,
            };
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
      clearInterval(staleTimer);
      stopPolling();
      ws?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pairsKey, reconnect, hasToken]);

  return { ...state, hasToken };
}
