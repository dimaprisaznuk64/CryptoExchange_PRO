# CryptoExchange_PRO — Progress

> Точка збереження проєкту. Як продовжити: прочитай цей файл, потім `git log --oneline` та `git status`. Завжди оновлюй цей файл і комить після кожного завершеного блоку.

## Останнє оновлення

- Дата: 2026-08-29
- Стан: **Phase 25 (Адмін-кабінет part 1: керування користувачами) — завершено.**
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

### Що зроблено в Phase 10 (стовп 1 — backend limit orders):
- `schemas/order.py` — `PlaceOrderRequest` тепер з `type` (market|limit) та опційним `price` (обов'язковий для limit, gt 0); додано `CancelOrderResponse`
- `models/order.py` — relationship `Order.pair → TradingPair` (ORM-level, без міграції); тип/ціна/статус вже були в схемі БД
- `services/trading.py`:
  - `place_order(...)` — единий вхід: market виконується одразу (як раніше), limit спершу заморожує кошти
  - freeze/unfreeze: buy-limit заморожує quote (`qty × price`, balance не змінюється), sell-limit заморожує base; інваріант `balance = available + frozen`
  - `_sweep_open_orders()` — після кожного ордера сканує відкриті limit-ордери користувача і виповнює ті, які перетнули поточну ринкову ціну (crossed) — філл за ціною ліміта
  - `cancel_order()` — розморожує кошти + статус `cancelled` (повторний cancel → 400, чужий/невідомий → 404)
  - умова перетину: buy заповнюється якщо `market ≤ limit`; sell якщо `market ≥ limit`
- `routers/orders.py` — `POST /orders/{id}/cancel`, фільтр `GET /orders?status=open|filled|cancelled`
- Тести: `tests/test_orders.py` +10 тестів (open+freeze buy/sell, миттєвий філл buy/sell, cancel buy/sell + повторний 400 + невідомий 404, price обов'язковий 422, недостатньо коштів 400, фільтр за статусом)
- QA: backend `49 passed` (13 auth + 7 wallet + 6 market + 17 orders + 2 realtime + 4 portfolio)

### Що зроблено в Phase 10 (стовп 2 — frontend limit orders):
- `lib/api.ts` — `placeOrder(...)` приймає `type` (market|limit) та опційну `price`; додано `cancelOrder(id)`, `getOpenOrders()` (фільтр `status=open`)
- `app/trade/page.tsx`:
  - форма ордера: перемикач **Market / Limit**, для limit — поле ціни (placeholder = live price), "Est. total" рахується за limit-ціною, кнопка показує `Limit Buy/Sell @ ...`
  - таблиця Orders: нові колонки **Type**, **Price** (лімітна/виконавча ціна), **Filled**; для open-ордерів кнопка **Cancel**
  - після limit-ордера показ повідомлення "Limit buy order placed: QTY PAIR @ PRICE"; refresh історії після place/cancel
  - виправлено дубль заголовка "Time" у вкладці Trades
- QA: `npm run lint` чистий, `npm run build` успішний (6 сторінок)
- Інтеграція з живим backend (перезапущено uvicorn під новим кодом), скрипт `test_limit_orders.mjs` — **27/27 passed**:
  - open buy @1000 → frozen 20, available 9980, balance 10000 (незмінний)
  - cancel → розмороження, повторний cancel → 400, missing price → 422
  - buy @100000 → миттєвий філл за лімітом (USDT −2000, BTC +0.02)
  - insufficient → 400; sell open → freeze base (frozen 0.02, available 0)
  - sell @1000 → миттєвий філл (BTC −0.01, USDT +10); фільтри `?status=open|filled` ✓

### Що зроблено в Phase 11 (стовп 1 — backend TP/SL):
- `models/order.py` — `OrderType` розширено: `take_profit`, `stop_loss`
- Міграція `2ffbf4af1389` — `ALTER TYPE ordertype ADD VALUE take_profit/stop_loss` (застосовано до Postgres; downgrade перебудовує enum)
- `services/trading.py`:
  - `_conditional_triggered(order, live)` — TP спрацьовує при сприятливому русі (sell: live ≥ price, buy: live ≤ price), SL — при несприятливому
  - `check_conditional_orders(db, user_id=None)` — сканує відкриті TP/SL за **live-ціною** (посекундна), виповнює за тригерною ціною (той самий механізм `_execute_limit_fill`)
  - `place_order` приймає типи take_profit/stop_loss; включено в перевірку тригерів після кожного ордера
  - ledger-нотатки тепер відображають тип («limit buy», «take profit sell»)
- `main.py` — фоновий асинхронний монітор `_conditional_monitor_loop()` (інтервал `CONDITIONAL_CHECK_INTERVAL_SECONDS`, default 5): кожні N сек перевіряє всі TP/SL і автовиконує перетнуті; запускається в lifespan, скасовується при shutdown
- `config.py` — новий параметр `CONDITIONAL_CHECK_INTERVAL_SECONDS`
- Тести: `tests/test_orders.py` +5 (TP sell open+freeze+cancel, TP sell миттєвий філл, SL sell через монітор, TP buy через монітор, price обов'язковий 422)
- QA: backend `54 passed` (49 + 5)
- Live-інтеграція: скрипти `test_tpsl.mjs` (9/9), `test_monitor.mjs` (9/9) — монітор самостійно виконав відкритий sell stop_loss через ~46с без дій користувача (BTC frozen → filled, USDT зараховано за тригерною ціною)

### Що зроблено в Phase 11 (стовп 2 — frontend TP/SL):
- `app/trade/page.tsx`:
  - у формі ордера блок **"Take-profit / Stop-loss"** (Add/Remove): два поля TP/SL (placeholders ≈ live ×1.05 / ×0.95)
  - після виконання базового ордера (filled) автоматично створюються умовні ордери: TP/SL протилежної сторони на `filled_qty`; TP/SL повідомлення в успіху («Bought … + TP + SL order placed»)
  - валідація: хоча б один із TP/SL обов'язковий, ціни > 0
  - таблиця Orders: бейджі **TP** (green) / **SL** (red) у колонці Type; Cancel працює для всіх open (у т.ч. умовних)
  - після place/cancel скидаються поля TP/SL
- `lib/api.ts` — `placeOrder` type тепер включає `take_profit | stop_loss`
- QA: `npm run lint` чистий, `npm run build` успішний (6 сторінок)
- Live E2E (симуляція фронт-флоу): buy 0.05 BTC → TP sell @200000 (open) + SL sell @50000 (open) → frozen 0.05, available 0; rows у списку; cancel SL (frozen 0.03) → cancel TP (frozen 0) — **13/13 passed**

### Що зроблено в Phase 12 (стовп 1 — backend фільтри історії):
- `GET /orders` — нові фільтри: `pair`, `side`, `type`, `status` (вже був), `from`/`to` (datetime), plus `limit`/`offset`; валідація через `Literal` → невалідне значення дає **422**
- `GET /orders/trades` — фільтри `pair`, `side`, `from`/`to`; відповідь тепер містить **`pair`** (symbol через JOIN з TradingPair)
- `services/trading.py` — `list_orders`/`list_trades` з опційними фільтрами (JOIN TradingPair для символу)
- Тести: +2 (orders-фільтри: status/side/type/pair/date + 422; trades-фільтри + поле pair)
- QA: backend `56 passed` (54 + 2)
- Live: `test_filters.mjs` — **22/22 passed** (комбінації фільтрів, дати, 422 на невалідних значеннях)
- Frontend (`/trade` Activity): панель фільтрів — Order: Pair/Type/Status, Trades: Pair/Side, кнопка Reset; колонка **Pair** у таблицях ордерів і угод; `api.ts` `getOrders`/`getOrderTrades` приймають об'єкти фільтрів; `Trade.pair` у типах
- QA frontend: ESLint ✓, `next build` ✓, живість :3001 → 200, регресія live: limit 27/27, TP/SL 9/9
- Коміти: `74aff8c` backend; frontend-коміт див. у git log (Phase 12)

### Що зроблено в Phase 13 (стовп 1 — backend, історія портфеля):
- `GET /portfolio/history?days=7` — семпли вартості портфеля (USDT) за N днів (за замовч. 12 точок/день + фінальна точка на `now`)
- Точна «розмотка назад»: поточна рівновага − сума `delta` транзакцій (депозити/зняття/угоди), що сталися після часу семплу; ціна активів через `_price_at` (детермінований price engine), USDT/USD = 1
- Нова relationship `Transaction.asset` (модель)
- Тести: +2 (реконструкція до-депозиту = 0, остання точка = поточна вартість ±1; auth 401)
- QA: backend `58 passed`; live `test_history.mjs` **9/9** (13 точок, 85 точок для 7d, збіг з total_usd, 422)
- Коміт: `e38c381` (backend Phase 13)
- Frontend (дашборд): графік «Portfolio history» (SVG-лінія + площа, без залежностей), значення «Value now» + зміна − 7 днів; `PortfolioChart` компонент, `getPortfolioHistory(days)` в API
- QA frontend: ESLint ✓, `next build` ✓, :3001/dashboard → 200; регресія live limit orders 27/27
- Коміт frontend: див. git log (Phase 13)

### Що зроблено в Phase 14 (стовп 1 — backend, фільтри транзакцій):
- `GET /wallets/transactions` — фільтри: `type` (deposit/withdrawal/trade_buy/trade_sell/fee/adjustment), `status`, `asset` (символ), `from`/`to` (datetime), + `limit`/`offset`; невалідний type/status → 422 (Literal)
- `services/wallet.py` `get_transactions` — фільтри через JOIN Asset (символ), enum-конвертація
- Тести: +1 (тип/актив/комбінації/дати/422) → **59 passed**
- Live: `test_tx_filters.mjs` **13/13** (депозити/зняття/buy-fills, фільтри, дати, 422, 401)
- Коміт: `1f1ef19` (backend Phase 14)
- Frontend (`/wallets`): панель фільтрів транзакцій — Asset/Type/Status + Reset; `getTransactions` приймає об'єкт фільтрів; таблиця оновлена (ledger incl. trade_buy/trade_sell/fee)
- QA frontend: ESLint ✓, `next build` ✓, :3001/wallets → 200; live tx-фільтри 13/13; backend без помилок (лише benign bcrypt warning)
- Коміт frontend: див. git log (Phase 14)

### Що зроблено в Phase 15 (офіц. PHASE 8 — Redis; інфраструктура була в scaffold, додано реальне використання):
- Раніше: `app/core/cache.py` (клієнт + graceful fallback) ініціалізувався в lifespan, але **ніде не використовувався**
- Тепер: кешування в Redis ринкових даних — `market:tickers` та `market:ticker:{symbol}` (TTL 30s через `cache_get`/`cache_set`); при недоступному Redis — автоматичний fallback на обчислення
- `/health` тепер повертає статус **`redis`: connected/disabled/error** (+ping)
- Тести: +3 (ticker реально пишеться в кеш-мок; health-поля; health-report) → **62 passed**
- Live (реальний Redis `cryptoexchange_pro-redis-1` на :6380): `/health` → `"redis":"connected"`, ключі `market:tickers`/`market:ticker:BTC/USDT` заповнені (TTL 29s), регресія 80/80 (limit/TP-SL/filters/history/tx)
- Коміт: `03f4a05` (Phase 15)

### Що зроблено в Phase 16 (офіц. PHASE 9 — Celery):
- `app/core/celery_app.py` — Celery з broker/backend Redis (db `/1`), JSON, beat_schedule
- `app/tasks/__init__.py` — таски: `refresh_market_stats` (beat 60s, прогрів Redis-кешу), `cleanup_stale_transactions` (beat щодня), `run_conditional_orders` (НЕ auto-sched — щоб не задвоювати з in-process монітором TP/SL)
- Кожна таска створює свій async-engine (dispose після) — обхід Windows-обмеження asyncio.run + asyncpg loop affinity
- `app/services/wallet.py` — `purge_stale_transactions(days)` (видалення pending/failed старше N днів)
- Конфіг: `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`/`CELERY_TASK_ALWAYS_EAGER`; `.env` → 6380/1
- Тести: +2 (config/beat/реєстрація тасок; purge видаляє лише старі) → **64 passed**
- Live: eager-виконання всіх 3 тасок (refresh {'pairs':4}, cleanup {'removed':0}, cond {'executed':0}); **celery worker запустився**: `Connected to redis://localhost:6380/1` → `celery@Dimas ready`
- Коміт: див. git log (Phase 16)

### Що зроблено в Phase 25 (Адмін-кабінет part 1: керування користувачами):
- **Backend**:
  - `services/admin.py`: `list_users` (batch-агрегація: total USD spot за поточними цінами, # ордерів, # тредів; пошук email/username), `get_user_detail` (профіль + гаманці + підсумки), `update_user` (роль/is_active) із **self-protection** (адмін не може змінити власну роль чи заблокувати себе)
  - `routers/admin.py`: `GET /admin/users`, `GET /admin/users/{id}`, `PATCH /admin/users/{id}` — захист `require_admin` на рівні роутера + per-user rate_limit; `schemas/admin.py`
  - Зареєстровано роутер у main.py
- **Frontend**: сторінка `/admin/users` (role-gate, пошук, таблиця користувачів, детальна панель з гаманцями + block/unblock + зміна ролі), посилання «Admin» у Navbar (видиме тільки адміну); `api.adminListUsers/adminGetUser/adminUpdateUser`, типи `AdminUser*`
- Тести: +8 (403 не-адмін, 401 без токена, список, пошук, блок→403 у користувача, зміна ролі, self-protection, деталі+404) → **96 passed**; frontend lint+build green
- Коміт: див. git log (Phase 25)

### Що зроблено в Phase 24 (Деплой: Docker backend + Vercel frontend):
- **Backend (Docker)**:
  - `backend/Dockerfile` (python:3.13-slim, requirements, `alembic upgrade head && uvicorn --port 8001`) + `backend/.dockerignore`
  - `docker-compose.yml` розширено: сервіси `backend`, `worker`, `beat` (Celery) поверх postgres+redis; env через anchor `x-backend-env` (хости = імена сервісів)
  - `backend/.env.example` — шаблон env-змінних
- **Frontend (Vercel)**: у `lib/api.ts` дефолтні `NEXT_PUBLIC_API_URL/WS_URL` приведено до `:8001`; на Vercel задаються через env (Root Directory = `frontend`)
- `docs/DEPLOYMENT.md` — детальна інструкція: збірка/push образу, запуск на VPS, env-таблиця, міграції (включно з необхідністю застосувати `3a9f2c77d1b4` + `f0a1b2c3d4e5`), Vercel-налаштування, перевірка після деплою
- `scripts/build-backend.sh` — хелпер збірки/push образу
- README оновлено (розділи «Запуск» і «Деплой»); frontend lint green
- Коміт: див. git log (Phase 24). Деплой сам не запускався (нема креда / Docker вимкнений) — конфіги + документація готові.

### Що зроблено в Phase 23 (Сповіщення користувача):
- **Backend**:
  - Модель `Notification` (id, user_id FK, kind, title, body, is_read, created_at) + Alembic міграція `f0a1b2c3d4e5_add_notifications` (на live-Postgres застосувати через Docker)
  - `services/notifications.py`: `create_notification`, `list_notifications`, `mark_read`, `mark_all_read`, `unread_count`
  - Хуки в `trading.py`: сповіщення `order_filled` (market/limit/TP/SL захоплюються в `_place_market` та `_execute_limit_fill`) та `order_cancelled`
  - `routers/notifications.py`: `GET /notifications`, `GET /notifications/unread-count`, `POST /notifications/{id}/read`, `POST /notifications/read-all` (all per-user rate_limit)
  - WS-пуш: `GET /ws/notifications` — періодичний снапшот нових сповіщень + unread-count
- **Frontend**: `NotificationsBell` у Navbar (бейдж unread, dropdown, mark-all-read, посилання на сторінку), сторінка `/notifications` (список + індивідуальне mark-read + mark-all); `api.getNotifications/getUnreadCount/markNotificationRead/markAllNotificationsRead`, типи `Notification`/`UnreadCount`
- Тести: +4 (spовiщення про fill/cancel, unread+mark-read, 401) → **88 passed**; frontend lint+build green
- Коміт: див. git log (Phase 23)

### Що зроблено в Phase 22 (Звіт за обсягом):
- `portfolio.get_volume_report(db, user_id, days)` — GROUP BY-агрегація тредів користувача за період по парах (buy/sell notional, qty, count) + загальні підсумки (total_notional/qty/trades)
- `GET /api/v1/portfolio/volume?days=N` (1–90, дефолт 7) → `VolumeReport` (per-user rate_limit 30/60s, 401 без авторизації)
- Frontend: `VolumeReportPanel` на `/dashboard` з перемикачем 7/30/90d та таблицею volume по парах; `api.getVolumeReport`, типи `VolumeReport`/`VolumePairReport`
- Тести: +3 (данi звіту, порожній звіт, 401) → **84 passed**; frontend lint+build green
- Коміт: див. git log (Phase 22)

### Що зроблено в Phase 21 (24h-статистика ринку):
- `app/services/market.py` — `get_stats_24h(pair)` + `get_stats_24h_cached(...)`: OHLC, change %, volume (quote і base), count тредів; Redis-кеш `market:stats24:{symbol}` TTL 30s (graceful fallback)
- `GET /api/v1/market/stats/{symbol}` → `MarketStatsResponse` (public, per-IP rate_limit 120/60s, 404 для невідомої пари)
- Frontend: `MarketStatsPanel` (новий компонент) на сторінці `/trade` — сітка 24h статистики (Open/High/Low/Change/Volume quote+base/Trades/24h range); `api.getMarketStats`, тип `MarketStats`
- Тести: +3 (данi stats, Redis-кеш, 404) → **81 passed**; frontend lint+build green
- Коміт: див. git log (Phase 21)

### Що зроблено в Phase 20 (Переказ між гаманцями):
- `app/services/wallet.py` — `transfer(db, user_id, symbol, from_type, to_type, amount)`: атомарно (row-lock обох гаманців) дебетує available джерела → кредитує balance+available цілі; валідація amount>0, from!=to, типи spot/funding, достатність; заборона переказу в той самий тип
- Леджер: 2 транзакції типу `transfer` (джерело −delta, ціль +delta), зв'язані спільним `ref_id` (`<from_wallet>:<to_wallet>`)
- `TransactionType` — додано `transfer`; Alembic-міграція `3a9f2c77d1b4` (`ALTER TYPE transactiontype ADD VALUE 'transfer'`) для Postgres
- `POST /api/v1/wallets/transfer` (rate_limit_user 10/60s), схема `TransferRequest` (Literal spot/funding)
- `get_balances` тепер повертає `wallet_type` (розрізнення spot/funding у відповіді)
- Frontend: режим "transfer" у картці гаманців (from/to selects), колонка "Wallet" у таблиці балансів (fix duplicate key), фільтр "transfer" у транзакціях; `api.transfer(...)`
- Тести: +5 (переказ, леджер 2 записів, недостатність 400, same-wallet 400, bad-type 422) → **78 passed**; frontend lint+build green
- Live: застосувати міграцію після запуску Docker (`alembic upgrade head`)
- Коміт: див. git log (Phase 20)

### Що зроблено в Phase 19 (Security — rate-limit на read-ендпоінти):
- Публічні (per-IP): `/market/pairs`, `/market/tickers`, `/market/tickers/{symbol}`, `/market/candles` (rate_limit 60–120/60s)
- Автентифіковані (per-user через `rate_limit_user`): `/portfolio`, `/portfolio/trades`, `/portfolio/history`; `/wallets/balances`, `/wallets/transactions`; `/orders`, `/orders/trades` (30–60/60s)
- Тести: +2 (per-IP 429 на market, per-user 429 на portfolio) → **73 passed**
- Коміт: див. git log (Phase 19)
- Станом на цей коміт покриті rate-limit: всі **write** і всі **read** ендпоінти (market/wallets/orders/portfolio/auth). Security-фази завершено.

### Що зроблено в Phase 18 (Security harden — account lockout + rate-limit на мутації):
- `app/core/ratelimit.py` — account lockout: `record_failed_login(email)` (лічильник на акаунт `auth:failed:<email>`, на порозі `FAILED_LOGIN_THRESHOLD=5` ставить `auth:lock:<email>` TTL 15хв), `is_account_locked(email)` (повертає залишок секунд через `ttl`), `reset_failed_logins(email)` (очистка успішним логіном); виняток `AccountLocked` (423 + `Retry-After`)
- `rate_limit_user(scope, limit, window)` — rate-limit **на автентифікованого користувача** (ключі `user.id` + IP), через `get_current_user`
- `app/routers/auth.py` — login перевіряє lockout перед валідацією пароля (423), на невдачу рекордить і per-IP і per-account, на успіх `reset_failed_logins`; audit-подія `auth.login_locked`
- `app/main.py` — exception-handler для `AccountLocked` (423 + Retry-After)
- `app/routers/wallets.py` — `rate_limit_user` на `/deposit` і `/withdraw` (10/60s)
- `app/routers/orders.py` — `rate_limit_user` на place order і cancel (20/60s)
- Redis mock: додано `ttl`; тести — lockout після 5 невдалих, reset успішним логіном, per-user 429 на ордери → **71 passed**
- Коміт: див. git log (Phase 18)

### Що зроблено в Phase 17 (Security — rate limit + audit + security headers):
- `app/core/ratelimit.py` — fixed-window rate limit на Redis (pipeline incr+expire nx), fail-open якщо Redis недоступний, `RateLimitExceeded` (429 + `Retry-After`)
- `app/core/audit.py` — структурований JSON audit-лог (event, UTC, без секретів, обрізання довгих полів) → `logs/audit.log` (Rotating 5MB×3, `audit` logger окремо від app)
- `app/routers/auth.py` — rate limit на `/register` і `/login` (20/60s на IP), лічильник невдалих логінів у Redis (key `auth:failed:<ip>`, TTL 5хв, поріг 5 → подія `suspicious_login_activity`), audit-події register/login/login_failed
- `app/main.py` — security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP), exception-handler для 429
- Фікс багів: `_ip_of` викликався без `await` (RunTimeWarning); `from app.core.cache import redis_client` біндився на import-time `None` → rate-limit і fail-counter **не працювали в рантаймі** (виправлено на динамічний `cache.redis_client` у ratelimit.py та auth.py)
- Redis mock розширено (`incr`/`expire`/`pipeline` sync-ланцюжок) — реальна перевірка rate limit у тестах
- Тести: `tests/test_security.py` → +4 (security headers, register 429, login 429, failed-login counter+suspicious) → **68 passed**
- Коміт: див. git log (Phase 17)

### Примітка щодо портів (2026-08-28, тимчасово)
- Docker auto-restore підняв контейнери іншого проєкту (InternetShop_PRO), які зайняли **8000** (backend) і **3000** (frontend)
- Тому наш стек працює на **backend `:8001`**, **frontend `:3001`**:
  - `backend/.env` → `CORS_ORIGINS=http://localhost:3000,http://localhost:3001`
  - `frontend/.env.local` → `NEXT_PUBLIC_API_URL=http://localhost:8001`
- Обидва файли в `.gitignore`. Коли InternetShop зупинено — повернути стандартні порти 8000/3000

## Наступний крок

- ➡️ Кандидати на Phase 26+: адмін part 2 (ордери/трейди всіх юзерів), адмін part 3 (дашборд/статистика), фактичний запуск деплою
- ➡️ Майбутнє (ideas): сповіщення, деплой (Vercel + Docker)

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
| 10 | Limit orders | ✅ |
| 11 | TP/SL | ✅ |
| 12 | Фільтри історії (orders/trades) | ✅ (додано) |
| 13 | 7-денна історія портфеля | ✅ (додано) |
| 14 | Фільтри транзакцій | ✅ (додано) |
| 15 | Redis (реальне використання: кеш) | ✅ (додано) |
| 16 | Celery (фонова черга) | ✅ (додано) |
| 17 | Security (rate limit, audit, headers) | ✅ (додано) |
| 18 | Security harden (lockout, per-user rate limit) | ✅ (додано) |
| 19 | Security: rate-limit на read-ендпоінти | ✅ (додано) |
| 20 | Переказ між гаманцями (spot↔funding) | ✅ (додано) |
| 21 | 24h-статистика ринку (/market/stats) | ✅ (додано) |
| 22 | Звіт за обсягом (/portfolio/volume) | ✅ (додано) |
| 23 | Сповіщення користувача (/notifications + WS) | ✅ (додано) |
| 24 | Деплой: Docker backend + Vercel frontend | ✅ (конфіги + docs) |
| 25 | Адмін-кабінет part 1: керування користувачами | ✅ (додано) |

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
