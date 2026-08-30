"use client";

import { useEffect, useRef, useState } from "react";
import { getWsUrl, tokenStore } from "@/lib/api";
import type { BookSnapshot, PriceMessage } from "@/lib/types";

export interface RealtimeState {
  connected: boolean;
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

export function useRealtimePrices(pairs: string[]) {
  const [state, setState] = useState<RealtimeState>({
    connected: false,
    hello: null,
    prices: {},
    book: null,
    lastUpdate: 0,
  });

  const pairsKey = pairs.join(",");
  const [reconnect, setReconnect] = useState(0);
  const hasToken = typeof window !== "undefined" && Boolean(tokenStore.getAccess());

  // Pending updates buffered between flushes.
  const pendingRef = useRef<{
    connected?: boolean;
    hello?: string;
    prices?: Record<string, number>;
    book?: BookSnapshot;
    dirty: boolean;
  }>({ dirty: false });

  useEffect(() => {
    if (pairs.length === 0) return;
    if (!tokenStore.getAccess()) return;

    const url = getWsUrl(pairs);
    let ws: WebSocket | null = null;
    let closed = false;
    let connectAttempts = 0;
    const MAX_RECONNECTS = 5;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const flushTimer = setInterval(() => {
      const pending = pendingRef.current;
      if (!pending.dirty) return;
      setState((s) => ({
        connected: pending.connected ?? s.connected,
        hello: pending.hello ?? s.hello,
        prices: pending.prices ? { ...s.prices, ...pending.prices } : s.prices,
        book: pending.book ?? s.book,
        lastUpdate: Date.now(),
      }));
      pendingRef.current = { dirty: false };
    }, FLUSH_INTERVAL_MS);

    const connect = () => {
      if (closed) return;
      connectAttempts += 1;
      if (connectAttempts > MAX_RECONNECTS) {
        setState((s) => ({ ...s, connected: false }));
        return;
      }
      ws = new WebSocket(url);

      ws.onopen = () => {
        pendingRef.current.connected = true;
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
        if (!closed && !reconnectTimer && connectAttempts < MAX_RECONNECTS) {
          const delay = Math.min(1000 * 2 ** (connectAttempts - 1), 15000);
          reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            setReconnect((r) => r + 1);
          }, delay);
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

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      clearInterval(flushTimer);
      ws?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pairsKey, reconnect, hasToken]);

  return { ...state, hasToken };
}