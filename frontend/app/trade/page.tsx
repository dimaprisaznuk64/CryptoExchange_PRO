"use client";

import { Suspense, useCallback, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useFetch } from "@/hooks/useFetch";
import { useRealtimePrices } from "@/hooks/useRealtime";
import { api, ApiError } from "@/lib/api";
import { Protected } from "@/components/Protected";
import { Alert, Badge, Button, Card, CardHeader, Input, Select, Spinner } from "@/components/ui";
import { OrderBook } from "@/components/OrderBook";
import { MarketTradesPanel } from "@/components/MarketTradesPanel";
import { CandleChart } from "@/components/CandleChart";
import { MarketStatsPanel } from "@/components/MarketStatsPanel";
import { FlashValue } from "@/components/FlashValue";
import { useAuth } from "@/contexts/AuthContext";
import { formatDateTime, formatPercent, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Ticker } from "@/lib/types";

function TradingView() {
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const { data: pairs } = useFetch(() => api.getPairs(), []);
  const initialPair = searchParams.get("pair") ?? "BTC/USDT";
  const [pair, setPair] = useState(initialPair);

  const [interval, setIntervalM] = useState(5);

  const { data: tickers } = useFetch(() => api.getTickers(), []);
  const ticker: Ticker | undefined = tickers?.find((t) => t.pair === pair);

  const { data: candles, loading: candlesLoading } = useFetch(
    () => api.getCandles(pair, interval, 120),
    [pair, interval],
  );

  const realtime = useRealtimePrices([pair]);

  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState<"market" | "limit">("market");
  const [qty, setQty] = useState("");
  const [limitPrice, setLimitPrice] = useState("");
  const [addTpsl, setAddTpsl] = useState(false);
  const [tpPrice, setTpPrice] = useState("");
  const [slPrice, setSlPrice] = useState("");
  const [orderError, setOrderError] = useState<string | null>(null);
  const [orderSuccess, setOrderSuccess] = useState<string | null>(null);
  const [placing, setPlacing] = useState(false);
  const [cancelling, setCancelling] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"orders" | "trades">("orders");
  const [ordersVersion, setOrdersVersion] = useState(0);
  const [orderFilter, setOrderFilter] = useState({
    pair: "",
    type: "",
    status: "",
  });
  const [tradeFilter, setTradeFilter] = useState({ pair: "", side: "" });

  const orders = useFetch(
    () => api.getOrders({ limit: 20, ...orderFilter }),
    [ordersVersion, orderFilter.pair, orderFilter.type, orderFilter.status],
  );
  const trades = useFetch(
    () => api.getOrderTrades({ limit: 20, ...tradeFilter }),
    [ordersVersion, tradeFilter.pair, tradeFilter.side],
  );

  const refreshOrders = useCallback(() => setOrdersVersion((v) => v + 1), []);

  const orderTypeBadge = (t: string) =>
    t === "take_profit" ? (
      <Badge tone="green">TP</Badge>
    ) : t === "stop_loss" ? (
      <Badge tone="red">SL</Badge>
    ) : (
      <span className="text-xs capitalize text-ink0">{t}</span>
    );

  const livePrice = realtime.prices[pair];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOrderError(null);
    setOrderSuccess(null);
    const amt = Number(qty);
    if (!Number.isFinite(amt) || amt <= 0) {
      setOrderError("Enter a valid quantity");
      return;
    }
    const price = orderType === "limit" ? Number(limitPrice) : undefined;
    if (orderType === "limit" && (!Number.isFinite(price) || (price as number) <= 0)) {
      setOrderError("Enter a valid limit price");
      return;
    }
    const tp = tpPrice !== "" ? Number(tpPrice) : NaN;
    const sl = slPrice !== "" ? Number(slPrice) : NaN;
    if (addTpsl) {
      if (Number.isNaN(tp) && Number.isNaN(sl)) {
        setOrderError("Enter at least a take-profit or stop-loss price");
        return;
      }
      if ((Number.isFinite(tp) && tp <= 0) || (Number.isFinite(sl) && sl <= 0)) {
        setOrderError("TP/SL prices must be positive");
        return;
      }
    }
    setPlacing(true);
    try {
      const order = await api.placeOrder(pair, side, amt, orderType, price);
      const extras: string[] = [];
      if (order.status === "filled" && Number(order.filled_qty) > 0 && addTpsl) {
        const opposite: "buy" | "sell" = order.side === "buy" ? "sell" : "buy";
        const q = Number(order.filled_qty);
        if (!Number.isNaN(tp)) {
          await api.placeOrder(pair, opposite, q, "take_profit", tp);
          extras.push("TP");
        }
        if (!Number.isNaN(sl)) {
          await api.placeOrder(pair, opposite, q, "stop_loss", sl);
          extras.push("SL");
        }
      }
      setOrderSuccess(
        order.status === "open"
          ? `Limit ${side} order placed: ${order.qty} ${pair} @ ${order.price}`
          : `${side === "buy" ? "Bought" : "Sold"} ${order.filled_qty} ${pair} @ ${order.avg_fill_price ?? "market"}` +
              (extras.length ? ` + ${extras.join(" + ")} order placed` : ""),
      );
      setQty("");
      if (orderType === "limit") setLimitPrice("");
      setTpPrice("");
      setSlPrice("");
      setAddTpsl(false);
      if (user) refreshOrders();
    } catch (err) {
      setOrderError(
        err instanceof ApiError ? err.detail : "Order failed, are you logged in?",
      );
    } finally {
      setPlacing(false);
    }
  };

  const handleCancel = async (orderId: string) => {
    setOrderError(null);
    setOrderSuccess(null);
    setCancelling(orderId);
    try {
      await api.cancelOrder(orderId);
      refreshOrders();
    } catch (err) {
      setOrderError(
        err instanceof ApiError ? err.detail : "Failed to cancel order",
      );
    } finally {
      setCancelling(null);
    }
  };

  const estTotal =
    Number(qty) > 0
      ? Number(qty) * (orderType === "limit" && Number(limitPrice) > 0 ? Number(limitPrice) : livePrice ?? 0)
      : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{pair}</h1>
          {ticker && (
            <div className="mt-1 flex items-center gap-3 text-sm text-ink/60">
              <span className="font-mono text-lg font-semibold">
                <FlashValue value={livePrice ?? ticker.last} format={formatPrice} />
              </span>
              <span
                className={cn(
                  "font-mono",
                  ticker.change_24h >= 0 ? "text-bull" : "text-bear",
                )}
              >
                {formatPercent(ticker.change_24h)}
              </span>
              {realtime.connected &&
                (realtime.mode === "ws" ? (
                  <span className="flex items-center gap-1 text-xs text-bull">
                    <span className="size-1.5 animate-pulse rounded-full bg-bull" />
                    live
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-amber">
                    <span className="size-1.5 animate-pulse rounded-full bg-amber" />
                    synced
                  </span>
                ))}
            </div>
          )}
        </div>

        <Select
          value={pair}
          onChange={(e) => setPair(e.target.value)}
          className="w-48"
        >
          {(pairs ?? []).map((p) => (
            <option key={p.symbol} value={p.symbol}>
              {p.symbol}
            </option>
          ))}
        </Select>
      </div>

      {!user && (
        <Alert tone="info">
          You are not logged in.{" "}
          <Link href="/login" className="font-medium underline">
            Log in
          </Link>{" "}
          to place orders and track your portfolio.
        </Alert>
      )}

      <MarketStatsPanel pair={pair} />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
            <div className="flex rounded-[2px] border border-hairline p-0.5">
              {[1, 5, 15, 60].map((m) => (
                <button
                  key={m}
                  onClick={() => {
                    setIntervalM(m);
                  }}
                  className={cn(
                    "cursor-pointer rounded-[2px] px-3 py-1 text-xs font-medium transition-colors",
                    interval === m
                      ? "bg-amber text-bg"
                      : "text-ink/60 hover:text-ink/90",
                  )}
                >
                  {m}m
                </button>
              ))}
            </div>
            <span className="text-xs text-ink0">OHLC chart</span>
          </div>
          <div className="p-4">
            {candlesLoading ? (
              <div className="flex h-64 items-center justify-center">
                <Spinner />
              </div>
            ) : (
              <CandleChart candles={candles ?? []} />
            )}
          </div>
        </Card>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Order book" subtitle="Live depth" />
            <div className="p-4">
              {realtime.book ? (
                <OrderBook
                  levels={realtime.book.levels}
                  bestBid={realtime.book.best_bid}
                  bestAsk={realtime.book.best_ask}
                  spread={realtime.book.spread}
                />
              ) : (
                <div className="flex h-64 items-center justify-center">
                  <span className="text-sm text-ink0">Connecting…</span>
                </div>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader title="Market trades" subtitle="Live tape" />
            <div className="p-4">
              <MarketTradesPanel trades={realtime.trades[pair] ?? []} />
            </div>
          </Card>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="h-fit">
          <CardHeader title="Place order" subtitle="Market or limit execution" />
          <form onSubmit={handleSubmit} className="space-y-4 p-5">
            {orderError && <Alert>{orderError}</Alert>}
            {orderSuccess && <Alert tone="success">{orderSuccess}</Alert>}

            <div className="flex rounded-[2px] border border-hairline p-0.5">
              {(["market", "limit"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setOrderType(t)}
                  className={cn(
                    "flex-1 cursor-pointer rounded-[2px] py-2 text-sm font-semibold transition-colors",
                    orderType === t
                      ? "bg-amber text-bg"
                      : "text-ink/60 hover:text-ink/90",
                  )}
                >
                  {t === "market" ? "Market" : "Limit"}
                </button>
              ))}
            </div>

            <div className="flex rounded-[2px] border border-hairline p-0.5">
              <button
                type="button"
                onClick={() => setSide("buy")}
                className={cn(
                  "flex-1 cursor-pointer rounded-[2px] py-2 text-sm font-semibold transition-colors",
                  side === "buy"
                    ? "bg-bull text-bg"
                    : "text-ink/60 hover:text-ink/90",
                )}
              >
                Buy
              </button>
              <button
                type="button"
                onClick={() => setSide("sell")}
                className={cn(
                  "flex-1 cursor-pointer rounded-[2px] py-2 text-sm font-semibold transition-colors",
                  side === "sell"
                    ? "bg-bear text-bg"
                    : "text-ink/60 hover:text-ink/90",
                )}
              >
                Sell
              </button>
            </div>

            <Input
              label="Quantity"
              type="number"
              inputMode="decimal"
              step="any"
              min="0"
              required
              placeholder="0.000000"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
            />

            {orderType === "limit" && (
              <Input
                label="Limit price"
                type="number"
                inputMode="decimal"
                step="any"
                min="0"
                required
                placeholder={livePrice ? String(livePrice) : "0.00"}
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
              />
            )}

            <div className="flex items-center justify-between rounded-[2px] border border-hairline bg-bg px-3 py-2 text-xs">
              <span className="text-ink/60">Take-profit / Stop-loss</span>
              <button
                type="button"
                onClick={() => setAddTpsl((v) => !v)}
                className={cn(
                  "cursor-pointer rounded-[2px] px-2 py-1 font-medium transition-colors",
                  addTpsl
                    ? "bg-amber text-bg"
                    : "text-amber hover:text-amber/80",
                )}
              >
                {addTpsl ? "Remove" : "Add"}
              </button>
            </div>

            {addTpsl && (
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Take-profit"
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min="0"
                  placeholder={livePrice ? String(Number(livePrice) * 1.05) : "0.00"}
                  value={tpPrice}
                  onChange={(e) => setTpPrice(e.target.value)}
                />
                <Input
                  label="Stop-loss"
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min="0"
                  placeholder={livePrice ? String(Number(livePrice) * 0.95) : "0.00"}
                  value={slPrice}
                  onChange={(e) => setSlPrice(e.target.value)}
                />
              </div>
            )}

            {estTotal > 0 && (
              <div className="flex items-center justify-between rounded-[2px] border border-hairline bg-bg px-3 py-2 text-xs">
                <span className="text-ink0">
                  Est. total ({orderType === "limit" ? "at limit" : "at market"})
                </span>
                <span className="font-mono font-medium text-ink/90">
                  {estTotal.toLocaleString("en-US", {
                    maximumFractionDigits: 2,
                  })}{" "}
                  USDT
                </span>
              </div>
            )}

            <Button
              type="submit"
              variant={side === "buy" ? "success" : "danger"}
              size="lg"
              loading={placing}
              className="w-full"
            >
              {orderType === "limit" ? "Limit" : ""} {side === "buy" ? "Buy" : "Sell"}{" "}
              {pair}
              {orderType === "limit" ? " @" + (limitPrice || "…") : ""}
            </Button>
          </form>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Activity"
            action={
              <div className="flex rounded-[2px] border border-hairline p-0.5">
                {(["orders", "trades"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setActiveTab(t)}
                    className={cn(
                      "cursor-pointer rounded-[2px] px-3 py-1 text-xs font-medium capitalize transition-colors",
                      activeTab === t
                        ? "bg-amber text-bg"
                        : "text-ink/60 hover:text-ink/90",
                    )}
                  >
                    {t}
                  </button>
                ))}
              </div>
            }
          />
          <div className="flex flex-wrap items-center gap-3 border-b border-hairline px-5 py-3">
            <Select
              value={activeTab === "orders" ? orderFilter.pair : tradeFilter.pair}
              onChange={(e) => {
                const pair = e.target.value;
                if (activeTab === "orders") setOrderFilter((f) => ({ ...f, pair }));
                else setTradeFilter((f) => ({ ...f, pair }));
              }}
              className="w-36"
            >
              <option value="">All pairs</option>
              {(pairs ?? []).map((p) => (
                <option key={p.symbol} value={p.symbol}>
                  {p.symbol}
                </option>
              ))}
            </Select>

            {activeTab === "orders" ? (
              <>
                <Select
                  value={orderFilter.type}
                  onChange={(e) =>
                    setOrderFilter((f) => ({ ...f, type: e.target.value }))
                  }
                  className="w-32"
                >
                  <option value="">All types</option>
                  <option value="market">Market</option>
                  <option value="limit">Limit</option>
                  <option value="take_profit">Take-profit</option>
                  <option value="stop_loss">Stop-loss</option>
                </Select>
                <Select
                  value={orderFilter.status}
                  onChange={(e) =>
                    setOrderFilter((f) => ({ ...f, status: e.target.value }))
                  }
                  className="w-32"
                >
                  <option value="">All statuses</option>
                  <option value="open">Open</option>
                  <option value="filled">Filled</option>
                  <option value="cancelled">Cancelled</option>
                </Select>
              </>
            ) : (
              <Select
                value={tradeFilter.side}
                onChange={(e) =>
                  setTradeFilter((f) => ({ ...f, side: e.target.value }))
                }
                className="w-32"
              >
                <option value="">All sides</option>
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </Select>
            )}

            {(activeTab === "orders"
              ? JSON.stringify(orderFilter)
              : JSON.stringify(tradeFilter)) !==
              (activeTab === "orders"
                ? JSON.stringify({ pair: "", type: "", status: "" })
                : JSON.stringify({ pair: "", side: "" })) ? (
              <button
                type="button"
                onClick={() => {
                  if (activeTab === "orders")
                    setOrderFilter({ pair: "", type: "", status: "" });
                  else setTradeFilter({ pair: "", side: "" });
                }}
                className="cursor-pointer text-xs font-medium text-amber hover:text-amber/80"
              >
                Reset
              </button>
            ) : null}
          </div>
          <div className="overflow-x-auto">
            {activeTab === "orders" ? (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-hairline text-xs text-ink0">
                    <th className="px-5 py-2 font-medium">Time</th>
                    <th className="px-5 py-2 font-medium">Pair</th>
                    <th className="px-5 py-2 font-medium">Side</th>
                    <th className="px-5 py-2 font-medium">Type</th>
                    <th className="px-5 py-2 text-right font-medium">Price</th>
                    <th className="px-5 py-2 text-right font-medium">Qty</th>
                    <th className="px-5 py-2 text-right font-medium">Filled</th>
                    <th className="px-5 py-2 font-medium">Status</th>
                    <th className="px-5 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {(orders.data ?? []).map((o) => (
                    <tr
                      key={o.id}
                      className="border-b border-hairline/60 last:border-0"
                    >
                      <td className="px-5 py-2 text-xs text-ink0">
                        {formatDateTime(o.created_at)}
                      </td>
                      <td className="px-5 py-2 text-xs text-ink/60">
                        {o.pair}
                      </td>
                      <td className="px-5 py-2">
                        <Badge tone={o.side === "buy" ? "green" : "red"}>
                          {o.side}
                        </Badge>
                      </td>
                      <td className="px-5 py-2">{orderTypeBadge(o.type)}</td>
                      <td className="px-5 py-2 text-right font-mono text-ink/80">
                        {o.price != null ? formatPrice(o.price) : "-"}
                      </td>
                      <td className="px-5 py-2 text-right font-mono text-ink/80">
                        {o.qty}
                      </td>
                      <td className="px-5 py-2 text-right font-mono text-ink/60">
                        {o.filled_qty}
                      </td>
                      <td className="px-5 py-2">
                        <Badge
                          tone={
                            o.status === "filled"
                              ? "blue"
                              : o.status === "open"
                                ? "amber"
                                : "default"
                          }
                        >
                          {o.status}
                        </Badge>
                      </td>
                      <td className="px-5 py-2 text-right">
                        {o.status === "open" && (
                          <Button
                            variant="outline"
                            size="sm"
                            loading={cancelling === o.id}
                            onClick={() => handleCancel(o.id)}
                          >
                            Cancel
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {(orders.data ?? []).length === 0 && (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-5 py-8 text-center text-sm text-ink0"
                      >
                        No orders yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-hairline text-xs text-ink0">
                    <th className="px-5 py-2 font-medium">Time</th>
                    <th className="px-5 py-2 font-medium">Pair</th>
                    <th className="px-5 py-2 font-medium">Side</th>
                    <th className="px-5 py-2 text-right font-medium">Price</th>
                    <th className="px-5 py-2 text-right font-medium">Qty</th>
                    <th className="px-5 py-2 text-right font-medium">Notional</th>
                  </tr>
                </thead>
                <tbody>
                  {(trades.data ?? []).map((t) => (
                    <tr
                      key={t.id}
                      className="border-b border-hairline/60 last:border-0"
                    >
                      <td className="px-5 py-2 text-xs text-ink0">
                        {formatDateTime(t.created_at)}
                      </td>
                      <td className="px-5 py-2 text-xs text-ink/60">
                        {t.pair}
                      </td>
                      <td className="px-5 py-2">
                        <Badge tone={t.side === "buy" ? "green" : "red"}>
                          {t.side}
                        </Badge>
                      </td>
                      <td className="px-5 py-2 text-right font-mono text-ink/80">
                        {formatPrice(t.price)}
                      </td>
                      <td className="px-5 py-2 text-right font-mono text-ink/80">
                        {t.qty}
                      </td>
                      <td className="px-5 py-2 text-right font-mono text-ink/80">
                        {t.notional.toLocaleString("en-US", {
                          maximumFractionDigits: 2,
                        })}
                      </td>
                    </tr>
                  ))}
                  {(trades.data ?? []).length === 0 && (
                    <tr>
                      <td
                        colSpan={6}
                        className="px-5 py-8 text-center text-sm text-ink0"
                      >
                        No trades yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function TradePage() {
  return (
    <Protected>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <Suspense fallback={<Spinner />}>
          <TradingView />
        </Suspense>
      </div>
    </Protected>
  );
}