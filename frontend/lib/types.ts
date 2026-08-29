export interface User {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export interface TradingPair {
  id: string;
  symbol: string;
  base_asset: string;
  quote_asset: string;
  price_precision: number;
  qty_precision: number;
  status: string;
}

export interface Ticker {
  pair: string;
  base_asset: string;
  quote_asset: string;
  last: number;
  open_24h: number;
  high_24h: number;
  low_24h: number;
  change_24h: number;
  volume_24h: number;
}

export interface MarketStats {
  pair: string;
  base_asset: string;
  quote_asset: string;
  last: number;
  open_24h: number;
  high_24h: number;
  low_24h: number;
  close_24h: number;
  change_24h: number;
  volume_24h: number;
  volume_base_24h: number;
  trades_24h: number;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Order {
  id: string;
  pair: string;
  side: "buy" | "sell";
  type: string;
  price: number | null;
  qty: number;
  filled_qty: number;
  avg_fill_price: number | null;
  status: string;
  created_at: string;
}

export interface Trade {
  id: string;
  order_id: string;
  pair: string;
  side: "buy" | "sell";
  price: number;
  qty: number;
  notional: number;
  created_at: string;
}

export interface BalanceItem {
  asset_symbol: string;
  wallet_type?: string;
  balance: number;
  available: number;
  frozen: number;
}

export interface BalanceResponse {
  items: BalanceItem[];
}

export interface Transaction {
  id: string;
  type: string;
  status: string;
  amount: number;
  delta: number;
  asset_symbol: string | null;
  note: string | null;
  created_at: string;
}

export interface PortfolioItem {
  asset: string;
  balance: number;
  usd_price: number;
  value_usd: number;
  pnl_usd: number;
}

export interface PortfolioResponse {
  total_usd: number;
  items: PortfolioItem[];
}

export interface PortfolioHistoryPoint {
  time: string;
  value: number;
}

export interface RecentTrade {
  id: string;
  pair: string;
  side: "buy" | "sell";
  price: number;
  qty: number;
  notional: number;
  created_at: string;
}

export interface PriceMessage {
  type: "price";
  pair: string;
  price: number;
  ts: string;
}

export interface BookLevel {
  bid: number;
  bid_qty: number;
  ask: number;
  ask_qty: number;
}

export interface BookSnapshot {
  pair: string;
  timestamp: string;
  best_bid: number;
  best_ask: number;
  spread: number;
  levels: BookLevel[];
}

export interface BookMessage {
  type: "book";
  pair: string;
  timestamp: string;
  best_bid: number;
  best_ask: number;
  spread: number;
  levels: BookLevel[];
}

export type ServerMessage =
  | { type: "hello"; user: string; pairs: string[] }
  | PriceMessage
  | BookMessage
  | { type: "error"; detail: string }
  | { type: string; [key: string]: unknown };

export interface VolumePairReport {
  pair: string;
  buy_notional: number;
  sell_notional: number;
  volume_notional: number;
  buy_qty: number;
  sell_qty: number;
  trades: number;
}

export interface VolumeReport {
  days: number;
  total_notional: number;
  total_qty: number;
  total_trades: number;
  pairs: VolumePairReport[];
}

export interface Notification {
  id: string;
  kind: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

export interface UnreadCount {
  count: number;
}

export interface AdminUserListItem {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
  total_usd: number;
  order_count: number;
  trade_count: number;
}

export interface AdminUserList {
  total: number;
  users: AdminUserListItem[];
}

export interface AdminWallet {
  asset: string;
  type: string;
  balance: number;
  available: number;
  frozen: number;
}

export interface AdminUserDetail {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  total_usd: number;
  order_count: number;
  trade_count: number;
  wallets: AdminWallet[];
}

export interface AdminUserUpdate {
  role?: string;
  is_active?: boolean;
}

export interface AdminOrderItem {
  id: string;
  user_email: string;
  user_username: string;
  pair: string;
  side: string;
  type: string;
  price: number | null;
  qty: number;
  filled_qty: number;
  avg_fill_price: number | null;
  status: string;
  created_at: string;
}

export interface AdminOrderList {
  total: number;
  orders: AdminOrderItem[];
}

export interface AdminTradeItem {
  id: string;
  order_id: string;
  user_email: string;
  user_username: string;
  pair: string;
  side: string;
  price: number;
  qty: number;
  notional: number;
  created_at: string;
}

export interface AdminTradeList {
  total: number;
  trades: AdminTradeItem[];
}