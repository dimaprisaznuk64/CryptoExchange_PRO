"use client";

import Link from "next/link";
import { useFetch } from "@/hooks/useFetch";
import { useRealtimePrices } from "@/hooks/useRealtime";
import { api } from "@/lib/api";
import { Card, Spinner } from "@/components/ui";
import { MarketTable } from "@/components/MarketTable";
import { useAuth } from "@/contexts/AuthContext";

export default function HomePage() {
  const { user } = useAuth();
  const { data: tickers, loading, error } = useFetch(() => api.getTickers(), []);
  const pairs = (tickers ?? []).map((t) => t.pair);
  const live = useRealtimePrices(pairs);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <section className="mb-12 grid gap-8 py-8 lg:grid-cols-2 lg:items-center">
        <div>
          <p className="mb-3 text-xs font-bold uppercase tracking-widest text-amber">
            Simulated crypto exchange
          </p>
          <h1 className="mb-4 max-w-xl text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl">
            Trade crypto with{" "}
            <span className="text-amber">realtime prices</span> and full
            portfolio analytics
          </h1>
          <p className="mb-8 max-w-lg text-lg text-ink/60">
            Practice trading BTC and ETH with synthetic market feeds, live
            order books, and a complete P&L dashboard. No real money involved.
          </p>
          <div className="flex flex-wrap gap-3">
            {user ? (
              <Link
                href="/trade"
                className="rounded-[2px] bg-amber px-6 py-3 font-medium text-bg transition-colors hover:bg-amber/90"
              >
                Go to Trading
              </Link>
            ) : (
              <>
                <Link
                  href="/register"
                  className="rounded-[2px] bg-amber px-6 py-3 font-medium text-bg transition-colors hover:bg-amber/90"
                >
                  Create account
                </Link>
                <Link
                  href="/trade?pair=BTC/USDT"
                  className="rounded-[2px] border border-hairline px-6 py-3 font-medium text-ink/80 transition-colors hover:bg-surface-2"
                >
                  View markets
                </Link>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {(tickers ?? []).slice(0, 4).map((t) => {
            const livePrice = live.prices[t.pair] ?? t.last;
            return (
              <div
                key={t.pair}
                className="rounded-[2px] border border-hairline bg-surface/60 p-4"
              >
                <p className="text-sm font-semibold text-ink/80">
                  {t.base_asset}/{t.quote_asset}
                </p>
                <p className="mt-1 font-mono text-xl font-bold text-ink">
                  {livePrice.toFixed(2)}
                </p>
                <p
                  className={
                    t.change_24h >= 0
                      ? "text-xs text-bull"
                      : "text-xs text-bear"
                  }
                >
                  {t.change_24h >= 0 ? "+" : ""}
                  {t.change_24h.toFixed(2)}%
                </p>
              </div>
            );
          })}
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-ink">Markets</h2>
          {live.connected && (
            <span className="flex items-center gap-1.5 text-xs text-bull">
              <span className="size-1.5 animate-pulse rounded-full bg-bull" />
              live
            </span>
          )}
        </div>

        <Card>
          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          ) : error ? (
            <p className="py-12 text-center text-sm text-bear">{error}</p>
          ) : (
            <MarketTable tickers={tickers ?? []} livePrices={live.prices} />
          )}
        </Card>
      </section>
    </div>
  );
}