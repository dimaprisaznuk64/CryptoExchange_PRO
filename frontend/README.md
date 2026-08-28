# CryptoExchange_PRO — Frontend

Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind CSS v4 SPA for the CryptoExchange_PRO simulator.

## Pages

| Route        | Description                                       |
|--------------|---------------------------------------------------|
| `/`          | Landing + market overview with live prices        |
| `/login`     | Sign in                                           |
| `/register`  | Create account                                    |
| `/dashboard` | Portfolio: total value, unrealized P&L, trades    |
| `/trade`     | OHLC chart, order book, market orders, history    |
| `/wallets`   | Balances, deposit/withdraw, transaction ledger    |

## Stack

- **Next.js 16** — App Router, `"use client"` components for interactive pages
- **TypeScript** — types in `lib/types.ts` mirror backend Pydantic schemas
- **Tailwind v4** — dark exchange theme
- **Fetch API** — `lib/api.ts` with Bearer tokens + silent refresh on 401
- **WebSocket** — `hooks/useRealtime.ts` streams prices + order book from `/ws/prices`

## Setup

```bash
npm install
cp .env.example .env.local   # adjust URLs if backend differs
npm run dev                  # http://localhost:3000
```

Environment:

- `NEXT_PUBLIC_API_URL` — REST API base (default `http://localhost:8000`)
- `NEXT_PUBLIC_WS_URL` — WebSocket base (default `ws://localhost:8000`)

## QA

```bash
npm run lint
npm run build
```