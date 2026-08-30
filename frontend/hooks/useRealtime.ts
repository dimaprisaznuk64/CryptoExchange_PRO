"use client";

import { useEffect, useState } from "react";
import { getWsUrl, tokenStore } from "@/lib/api";
import type { BookSnapshot, PriceMessage } from "@/lib/types";

export interface RealtimeState {
  connected: boolean;
  hello: string | null;
  prices: Record<string, number>;
  book: BookSnapshot | null;
  lastUpdate: number;
}

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

  useEffect(() => {
    if (pairs.length === 0) return;
    if (!tokenStore.getAccess()) return;

    const url = getWsUrl(pairs);
    let ws: WebSocket | null = null;
    let closed = false;
    let connectAttempts = 0;
    const MAX_RECONNECTS = 5;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (closed) return;
      connectAttempts += 1;
      if (connectAttempts > MAX_RECONNECTS) {
        setState((s) => ({ ...s, connected: false }));
        return;
      }
      ws = new WebSocket(url);

      ws.onopen = () => {
        setState((s) => ({ ...s, connected: true }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as {
            type: string;
            [key: string]: unknown;
          };
          if (msg.type === "hello") {
            setState((s) => ({ ...s, hello: String(msg.user ?? "") }));
          } else if (msg.type === "price") {
            const price = msg as unknown as PriceMessage;
            setState((s) => ({
              ...s,
              prices: { ...s.prices, [price.pair]: price.price },
              lastUpdate: Date.now(),
            }));
          } else if (msg.type === "book") {
            setState((s) => ({
              ...s,
              book: msg as unknown as BookSnapshot,
              lastUpdate: Date.now(),
            }));
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
      ws?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pairsKey, reconnect, hasToken]);

  return { ...state, hasToken };
}