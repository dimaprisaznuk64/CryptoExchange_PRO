import type {
  AccessTokenResponse,
  BalanceResponse,
  Candle,
  Order,
  PortfolioResponse,
  RecentTrade,
  Ticker,
  TokenResponse,
  Trade,
  TradingPair,
  Transaction,
  User,
} from "@/lib/types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "cx_access_token";
const REFRESH_KEY = "cx_refresh_token";

export const tokenStore = {
  getAccess: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  },
  setTokens: (access: string, refresh?: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  getRefresh: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_KEY);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

interface ApiOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  retry?: boolean;
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return null;
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as AccessTokenResponse;
    tokenStore.setTokens(data.access_token, refresh);
    return data.access_token;
  } catch {
    return null;
  }
}

async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, auth = false, retry = true } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = tokenStore.getAccess();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && auth && retry) {
    refreshPromise ??= refreshAccessToken();
    const newToken = await refreshPromise;
    refreshPromise = null;
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(`${API_URL}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    }
  }

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) {
        detail = data.detail
          .map(
            (d: { msg?: string; loc?: unknown[] }) =>
              `${d.loc?.join(".") ?? ""}: ${d.msg ?? ""}`.trim(),
          )
          .join("; ");
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // auth
  register: (email: string, username: string, password: string) =>
    apiFetch<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: { email, username, password },
    }),
  login: (email: string, password: string) =>
    apiFetch<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),
  logout: (refreshToken: string) =>
    apiFetch<void>("/api/v1/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),
  me: () => apiFetch<User>("/api/v1/auth/me", { auth: true }),

  // market
  getPairs: () => apiFetch<TradingPair[]>("/api/v1/market/pairs"),
  getTickers: () => apiFetch<Ticker[]>("/api/v1/market/tickers"),
  getTicker: (symbol: string) =>
    apiFetch<Ticker>(`/api/v1/market/tickers/${encodeURIComponent(symbol)}`),
  getCandles: (symbol: string, interval = 5, limit = 100) =>
    apiFetch<Candle[]>(
      `/api/v1/market/candles/${encodeURIComponent(symbol)}?interval=${interval}&limit=${limit}`,
    ),

  // wallets
  getBalances: () => apiFetch<BalanceResponse>("/api/v1/wallets/balances", { auth: true }),
  deposit: (asset_symbol: string, amount: number) =>
    apiFetch<BalanceResponse>("/api/v1/wallets/deposit", {
      method: "POST",
      auth: true,
      body: { asset_symbol, amount },
    }),
  withdraw: (asset_symbol: string, amount: number) =>
    apiFetch<BalanceResponse>("/api/v1/wallets/withdraw", {
      method: "POST",
      auth: true,
      body: { asset_symbol, amount },
    }),
  getTransactions: (limit = 50, offset = 0) =>
    apiFetch<Transaction[]>(
      `/api/v1/wallets/transactions?limit=${limit}&offset=${offset}`,
      { auth: true },
    ),

  // orders
  placeOrder: (
    pair: string,
    side: "buy" | "sell",
    qty: number,
    orderType: "market" | "limit" | "take_profit" | "stop_loss" = "market",
    price?: number,
  ) =>
    apiFetch<Order>("/api/v1/orders", {
      method: "POST",
      auth: true,
      body: {
        pair,
        side,
        qty,
        type: orderType,
        ...(price !== undefined ? { price } : {}),
      },
    }),
  cancelOrder: (orderId: string) =>
    apiFetch<{ id: string; status: string }>(`/api/v1/orders/${orderId}/cancel`, {
      method: "POST",
      auth: true,
    }),
  getOrders: (limit = 50, offset = 0) =>
    apiFetch<Order[]>(`/api/v1/orders?limit=${limit}&offset=${offset}`, {
      auth: true,
    }),
  getOpenOrders: (limit = 50) =>
    apiFetch<Order[]>(`/api/v1/orders?status=open&limit=${limit}`, { auth: true }),
  getOrderTrades: (limit = 50) =>
    apiFetch<Trade[]>(`/api/v1/orders/trades?limit=${limit}`, { auth: true }),

  // portfolio
  getPortfolio: () => apiFetch<PortfolioResponse>("/api/v1/portfolio", { auth: true }),
  getRecentTrades: (limit = 20) =>
    apiFetch<RecentTrade[]>(`/api/v1/portfolio/trades?limit=${limit}`, { auth: true }),
};

export const getWsUrl = (pairs: string[]): string => {
  const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
  const token = tokenStore.getAccess() ?? "";
  const params = new URLSearchParams({ token, pairs: pairs.join(",") });
  return `${base}/ws/prices?${params.toString()}`;
};