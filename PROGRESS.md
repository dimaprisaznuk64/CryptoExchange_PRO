# CryptoExchange_PRO — Progress

> Точка збереження проєкту. Як продовжити: прочитай цей файл, потім `git log --oneline` та `git status`. Завжди оновлюй цей файл і комить після кожного завершеного блоку.

## Останнє оновлення

- Дата: 2026-08-27
- Стан: **Phase 6 — Orders / Trading завершено.**
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

## Наступний крок

- ➡️ **Phase 7 — Realtime / WebSocket** (real-time ціни, order_book feed, notifications) + потім **P&L / Portfolio**

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
| 7 | Realtime / WebSocket | ⬜ |

## Конвенції проєкту

- Python 3.12+, FastAPI, SQLAlchemy async, PostgreSQL, Redis, Docker
- Шаблони: routers / services / repositories / schemas
- Урок → перевірка → наступний урок (без стрибків)
- Усі коміти змістовні, історія чиста
