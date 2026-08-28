# CryptoExchange_PRO — Progress

> Точка збереження проєкту. Як продовжити: прочитай цей файл, потім `git log --oneline` та `git status`. Завжди оновлюй цей файл і комить після кожного завершеного блоку.

## Останнє оновлення

- Дата: 2026-08-28
- Стан: **Phase 9 — Frontend завершено.**
- Робоча папка: `C:\Users\DIMAS\Desktop\Programming\PythonPRO\CryptoExchange_PRO`

### Що зроблено в Phase 0:
- Створено структуру проєкту: `backend/`, `frontend/`, `docs/`, `docker/`, `scripts/`, `tests/`
- Backend структура: `routers / services / repositories / models / schemas / dependencies / core`
- Git проініціалізовано, `.gitignore`, `README.md`
- Virtual environment: `backend/.venv`
- Залежності: FastAPI, SQLAlchemy async, Alembic, asyncpg, Redis, Celery, JWT, pytest
- `config.py` — налаштування через `.env` + pydantic-settings
- `logging.py` — логи (stdout + RotatingFileHandler)
- `database.py` — async engine / session / Base
- Перший FastAPI server + `GET /api/v1/health`

### Що зроблено в Phase 2:
- `docker-compose.yml` — Postgres 16 (порт 5433) + Redis 7 (порт 6380), unique до InternetShop_PRO
- `.env` / `.env.example` / `.env.docker` оновлено під нові порти
- Моделі: `User` (ролі user/trader/manager/admin), `Asset`, `TradingPair`, `Wallet` (spot/funding, balance/available/frozen)
- Alembic налаштовано (async env.py)
- Міграція `f45ed1946413` — initial schema, застосовано до Postgres
- Health перевірено: `200 {"status":"ok", "database":"connected"}`

### Що зроблено в Phase 3:
- `core/cache.py` — Redis (init/get/set/delete)
- `core/security.py` — хешування bcrypt, JWT access/refresh, token blacklist через Redis
- `dependencies/auth.py` — `get_current_user` + RBAC (`require_trader/manager/admin`)
- `schemas/user.py`, `schemas/auth.py` — Pydantic схеми
- `routers/auth.py` — register / login / refresh / logout / me
- `main.py` — lifespan (redis init/close), підключено auth router
- Тести: `tests/test_auth.py` — 13 тестів (register, login, blocked, me, refresh, logout/blacklist, 401/403/409)
- QA: backend `13 passed`, hermetic (sqlite + in-memory redis mock, `asyncio_default_*_loop_scope=session`)

### Що зроблено в Phase 4:
- Модель `Transaction` (ledger): type (deposit/withdrawal/trade_buy/trade_sell/fee/adjustment), status, amount, signed `delta`, ref_id
- Міграція `25b5fa1e1723` — таблиця `transactions` (застосовано)
- `services/wallet.py` — atomic-операції: `credit`/`debit` з row-lock (`SELECT ... FOR UPDATE`), захист від negative balance, запис ledger на кожну операцію
- `routers/wallets.py` — `GET /balances`, `GET /transactions`, `POST /deposit`, `POST /withdraw` (потребують auth)
- `schemas/wallet.py` — Balance/Transaction/Deposit/Withdraw
- Тести: `tests/test_wallets.py` — 7 тестів (deposit, withdraw, insufficient 400, negative 422, unknown asset 404, auth 401, ledger history)
- Реєстрація в `main.py`
- QA: backend `20 passed` (13 auth + 7 wallet)

### Що зроблено в Phase 5:
- `core/seed.py` — seed каталогу: 4 assets (USD, USDT, BTC, ETH) + 4 пари (BTC/USDT, ETH/USDT, BTC/USD, ETH/USD), викликається в lifespan
- `services/market.py` — симуляція ринкових цін (детермінована за хвилину), ticker з 24h статистикою (open/high/low/change/volume), OHLC свічки
- `routers/market.py` — `GET /pairs`, `GET /tickers`, `GET /tickers/{symbol}`, `GET /candles/{symbol}` (symbol з `/` через `{symbol:path}`)
- `schemas/market.py` — Pair/Ticker/Candle
- Тести: `tests/test_market.py` — 6 тестів (seed, pairs, ticker, all tickers, candles, 404)
- Live smoke: seed + pairs проти реального Postgres (docker) — ок
- QA: backend `26 passed` (13 auth + 7 wallet + 6 market)

### Що зроблено в Phase 6:
- Моделі `Order` (side buy/sell, type market/limit, price, qty, filled_qty, avg_fill_price, status) і `Trade` (кожна угода записується для P&L)
- Міграція `f534bdc35207` — `orders` + `trades` (застосовано)
- `services/trading.py` — `place_market_order`: атомарне виконання (row-lock обох гаманців), buy (USDT→BTC) / sell (BTC→USDT), перевірка балансу, запис Trade + ledger
- `routers/orders.py` — `POST /orders`, `GET /orders`, `GET /orders/trades`
- `schemas/order.py` — PlaceMarketOrder/Order/Trade
- Тести: `tests/test_orders.py` — 7 тестів (buy, sell, insufficient 400, bad side 422, unknown pair 404, history/trades, auth 401)
- Реєстрація в `main.py`
- QA: backend `33 passed` (13 auth + 7 wallet + 6 market + 7 orders)

### Що зроблено в Phase 7:
- `services/market.py` — додано `_live_price()` (гладка посекундна варіація ціни для realtime)
- `services/depth.py` — синтетичний order book (bid/ask рівні, best_bid/best_ask, spread, детермінований за секунду)
- `routers/ws.py` — WebSocket `/ws/prices?token=...&pairs=BTC/USDT,ETH/USDT`:
  - auth через query-токен (decode_token + blacklist + user lookup)
  - потік `{type:"price", pair, price, ts}` кожні ~50 мс
  - періодичний снапшот `{type:"book", ...}` (order book)
  - код 1008 при відмові авторизації
- Тести: `tests/test_realtime.py` — 2 тести (стрімінг цін/hello, відхилення неавторизованого)
- QA: backend `35 passed` (13 auth + 7 wallet + 6 market + 7 orders + 2 realtime)

### Що зроблено в Phase 8:
- Зв'язок `Wallet.asset → Asset` (relationship, ORM-level, без міграції)
- `services/portfolio.py`:
  - `get_portfolio` — вартість кожного активу в USD (cash 1:1; крипта через поточну ціну пари, перевага quote USD над USDT), сумарний `total_usd`
  - нереалізований P&L `(usd_price - avg_cost) * balance`, де `avg_cost` — середньозважена ціна входу з buy-угод
  - `get_recent_trades` — останні угоди
- `routers/portfolio.py` — `GET /portfolio`, `GET /portfolio/trades`
- `schemas/portfolio.py` — Portfolio/Item/RecentTrade
- Реєстрація в `main.py`
- Тести: `tests/test_portfolio.py` — 4 тести (empty, after buy, recent trades, auth 401)
- QA: backend `39 passed` (13 auth + 7 wallet + 6 market + 7 orders + 2 realtime + 4 portfolio)

### Що зроблено в Phase 9:
- Scaffold: Next.js 16.3 (Turbopack, App Router, TypeScript, Tailwind v4), у `frontend/`
- `lib/types.ts` — TS-типи, що відповідають усім backend-схемам (auth/market/order/wallet/portfolio/ws)
- `lib/api.ts` — API-клієнт: Bearer-токени з localStorage, авто-refresh (silent) по 401, 204-обробка
- `lib/format.ts` — форматування чисел/цін/USD/відсотків/дати
- `contexts/AuthContext.tsx` — провайдер: login/register/logout/me, bootstrap-відновлення сесії
- `components/` — Navbar (desktop + mobile), Protected-екран, Card/Button/Input/Select/Badge/Alert/Spinner
- Сторінки:
  - `/` — landing: hero + топ-4 пари + таблиця ринку з живими цінами (WS)
  - `/login`, `/register` — форми авторизації
  - `/dashboard` — портфель: total value, P&L, активи, останні угоди
  - `/trade` — торгівля: OHLC-графік (SVG, без залежностей), стакан, ордер (market buy/sell), історія orders/trades, вибір пари та інтервалу
  - `/wallets` — баланси, deposit/withdraw, лог транзакцій
- `hooks/useRealtime.ts` — WebSocket `/ws/prices`: стрімінг цін (~50ms) + снапшоти стакана, авто-reconnect
- `.env.local` / `.env.example` — `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`
- QA: `npm run lint` чистий, `npm run build` успішний (6 сторінок, статичний prerender), smoke 200 на всіх роутах
- Інтеграцію з живим backend перевірити після `docker compose up` + `uvicorn`

### Що зроблено в Phase 9 (венеджмент):
- **Інтеграційний тест frontend ↔ живий backend** — пройдено покроково:
  - `GET /health` → ok, `database: connected`; каталог: 4 пари засіяні
  - CORS для `http://localhost:3001` ✓ (preflight 200, allow-origin)
  - Auth flow: register 201, me 200, logout 204, login 200, дублікат 409, невірний пароль 401
  - Wallet: deposit 200 ×2, balances коректні, овер-вивід → 400, ledger 2 записи
  - Portfolio: total = 15000 USD, items (USD/USDT)
  - Orders: buy 201 (0.02 BTC @ 57760), sell 201, історія, overbuy → 400
  - P&L: після buy/sell BTC unrealized +67.78 USD (avg cost)
  - WebSocket: hello + 10 цін/с + стакан (10 рівнів, best_bid), no-auth → close 1008 ✓
- **UX-фікс**: `hooks/useRealtime.ts` — незалогінені користувачі більше не підключають WS (раніше → безкінечний reconnect після 1008)
- QA: `npm run lint` чистий, `npm run build` 6 сторінок ✓

### Примітка щодо портів (2026-08-28, тимчасово)
- Docker auto-restore підняв контейнери іншого проєкту (InternetShop_PRO), які зайняли **8000** (backend) і **3000** (frontend)
- Тому наш стек працює на **backend `:8001`**, **frontend `:3001`**:
  - `backend/.env` → `CORS_ORIGINS=http://localhost:3000,http://localhost:3001`
  - `frontend/.env.local` → `NEXT_PUBLIC_API_URL=http://localhost:8001`
- Обидва файли в `.gitignore`. Коли InternetShop зупинено — повернути стандартні порти 8000/3000

## Наступний крок

- ➡️ **Phase 10** (ідеї): ордери limit/TP-SL, історія угод з фільтрами, сповіщення, деплой (Vercel + Docker)

## Roadmap (фази)

| Phase | Назва | Статус |
|-------|-------|--------|
| 0 | Створення проєкту | ✅ |
| 1 | Architecture | ✅ (частково) |
| 2 | PostgreSQL | ✅ |
| 3 | Authentication | ✅ |
| 4 | Wallet / Balances | ✅ |
| 5 | Market | ✅ |
| 6 | Orders / Trading | ✅ |
| 7 | Realtime / WebSocket | ✅ |
| 8 | P&L / Portfolio | ✅ |
| 9 | Frontend | ✅ |

## Як запустити frontend

```bash
# термінал 1 — інфраструктура
docker compose up -d

# термінал 2 — backend (http://localhost:8000)
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# термінал 3 — frontend (http://localhost:3000)
cd frontend
npm install
npm run dev
```

## Конвенції проєкту

- Python 3.12+, FastAPI, SQLAlchemy async, PostgreSQL, Redis, Docker
- Шаблони: routers / services / repositories / schemas
- Урок → перевірка → наступний урок (без стрибків)
- Усі коміти змістовні, історія чиста
