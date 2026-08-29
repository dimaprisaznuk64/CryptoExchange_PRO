import logging
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet, WalletType
from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.models.trade import Trade
from app.models.transaction import Transaction
from app.services.market import _current_price, _price_at

logger = logging.getLogger(__name__)

USD_QUOTES = ("USD", "USDT")


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


async def _quote_cache(db: AsyncSession):
    """Map asset symbol -> quote asset symbol + live price in USD for that asset."""
    result = await db.execute(
        select(TradingPair)
        .options(selectinload(TradingPair.base_asset), selectinload(TradingPair.quote_asset))
        .where(TradingPair.is_active == True)  # noqa: E712
    )
    pairs = result.scalars().all()
    cache: dict[str, list] = {}
    for p in pairs:
        base: Asset = p.base_asset
        quote: Asset = p.quote_asset
        if quote.symbol not in USD_QUOTES:
            continue
        # prefer quote USD over USDT
        score = 0 if quote.symbol == "USD" else 1
        cache.setdefault(base.symbol, []).append((score, p.symbol, quote.symbol))
    return cache


async def _avg_cost(db: AsyncSession, user_id: str, asset_id: str) -> Decimal | None:
    """Average buy price in quote (USD) weighted by qty, from buy trades."""
    result = await db.execute(
        select(Trade).where(Trade.user_id == user_id, Trade.side == "buy")
    )
    trades = result.scalars().all()
    total_qty = Decimal("0")
    total_cost = Decimal("0")
    for t in trades:
        pair = (
            await db.execute(select(TradingPair).where(TradingPair.id == t.pair_id))
        ).scalar_one_or_none()
        if pair is None or pair.base_asset_id != asset_id:
            continue
        qty = Decimal(str(t.qty))
        total_qty += qty
        total_cost += qty * Decimal(str(t.price))
    if total_qty == 0:
        return None
    return total_cost / total_qty


async def get_portfolio(db: AsyncSession, user_id: str) -> dict:
    result = await db.execute(
        select(Wallet)
        .options(selectinload(Wallet.asset))
        .where(
            Wallet.user_id == user_id,
            Wallet.type == WalletType.spot,
            Wallet.balance > 0,
        )
    )
    wallets = list(result.scalars().all())
    prices = await _quote_cache(db)

    total_usd = Decimal("0")
    items = []
    for w in wallets:
        asset: Asset = w.asset
        balance = Decimal(str(w.balance))
        # cash (USD/USDT) valued 1:1
        if asset.symbol == "USD":
            val = balance
            usd_price = Decimal("1")
            pnl = Decimal("0")
        elif asset.symbol == "USDT":
            val = balance
            usd_price = Decimal("1")
            pnl = Decimal("0")
        else:
            candidates = prices.get(asset.symbol, [])
            if not candidates:
                continue
            candidates.sort(key=lambda c: c[0])
            _, pair_symbol, quote = candidates[0]
            usd_price = _current_price(pair_symbol)
            val = balance * usd_price
            avg_cost = await _avg_cost(db, user_id, asset.id)
            if avg_cost is not None:
                pnl = (usd_price - avg_cost) * balance
            else:
                pnl = Decimal("0")

        total_usd += val
        items.append(
            {
                "asset": asset.symbol,
                "balance": float(balance),
                "usd_price": float(usd_price),
                "value_usd": float(val),
                "pnl_usd": float(pnl),
            }
        )

    return {
        "total_usd": float(total_usd),
        "items": sorted(items, key=lambda i: i["value_usd"], reverse=True),
    }


async def get_recent_trades(db: AsyncSession, user_id: str, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.created_at.desc())
        .limit(limit)
    )
    trades = result.scalars().all()
    out = []
    for t in trades:
        pair = (
            await db.execute(select(TradingPair).where(TradingPair.id == t.pair_id))
        ).scalar_one_or_none()
        out.append(
            {
                "id": t.id,
                "pair": pair.symbol if pair else "?",
                "side": t.side,
                "price": float(t.price),
                "qty": float(t.qty),
                "notional": float(t.notional),
                "created_at": t.created_at,
            }
        )
    return out


async def get_volume_report(
    db: AsyncSession, user_id: str, days: int = 7
) -> dict:
    """Aggregate the user's traded volume (notional / qty) per pair over the
    last `days` (both buy and sell sides counted as volume)."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(
            TradingPair.symbol,
            Trade.side,
            func.coalesce(func.sum(Trade.qty), 0),
            func.coalesce(func.sum(Trade.notional), 0),
            func.count(Trade.id),
        )
        .join(TradingPair, TradingPair.id == Trade.pair_id)
        .where(Trade.user_id == user_id, Trade.created_at >= cutoff)
        .group_by(TradingPair.symbol, Trade.side)
        .order_by(TradingPair.symbol)
    )
    rows = result.all()

    pairs: dict[str, dict] = {}
    total_notional = Decimal("0")
    total_qty = Decimal("0")
    total_trades = 0

    for symbol, side, qty, notional, trades in rows:
        pair = pairs.setdefault(
            symbol,
            {
                "pair": symbol,
                "buy_notional": Decimal("0"),
                "sell_notional": Decimal("0"),
                "buy_qty": Decimal("0"),
                "sell_qty": Decimal("0"),
                "trades": 0,
            },
        )
        key_notional = f"{side}_notional"
        key_qty = f"{side}_qty"
        pair[key_notional] += Decimal(str(notional))
        pair[key_qty] += Decimal(str(qty))
        pair["trades"] += trades
        total_notional += Decimal(str(notional))
        total_qty += Decimal(str(qty))
        total_trades += trades

    pair_list = [
        {
            "pair": p["pair"],
            "buy_notional": float(p["buy_notional"]),
            "sell_notional": float(p["sell_notional"]),
            "volume_notional": float(p["buy_notional"] + p["sell_notional"]),
            "buy_qty": float(p["buy_qty"]),
            "sell_qty": float(p["sell_qty"]),
            "trades": p["trades"],
        }
        for p in pairs.values()
    ]
    pair_list.sort(key=lambda p: p["volume_notional"], reverse=True)

    return {
        "days": days,
        "total_notional": float(total_notional),
        "total_qty": float(total_qty),
        "total_trades": total_trades,
        "pairs": pair_list,
    }


async def get_portfolio_history(
    db: AsyncSession, user_id: str, days: int = 7, points_per_day: int = 12
) -> list[dict]:
    """Portfolio USD value sampled over the last `days`, reconstructed
    exactly from current balances minus all transaction deltas happened
    after each sample time."""
    wallets_res = await db.execute(
        select(Wallet)
        .options(selectinload(Wallet.asset))
        .where(Wallet.user_id == user_id, Wallet.type == WalletType.spot)
    )
    wallets = list(wallets_res.scalars().all())

    tx_res = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.asset))
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
    )
    txs = list(tx_res.scalars().all())

    prices = await _quote_cache(db)

    # balance[asset_id] = current balance; then we "unwrap" deltas going back in time
    balance: dict[str, Decimal] = {}
    asset_symbols: dict[str, str] = {}
    for w in wallets:
        balance[w.asset_id] = Decimal(str(w.balance))
        asset_symbols[w.asset_id] = w.asset.symbol
    for t in txs:
        asset_symbols.setdefault(t.asset_id, t.asset.symbol if t.asset else "?")

    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    total_points = days * points_per_day
    step = timedelta(days=days) / total_points
    end = start + step * (total_points - 1)
    if end > now:
        end = now

    def usd_value(bal: dict[str, Decimal], ts: datetime) -> float:
        total = Decimal("0")
        for asset_id, v in bal.items():
            if v == 0:
                continue
            symbol = asset_symbols.get(asset_id, "?")
            if symbol in USD_QUOTES:
                px = Decimal("1")
            else:
                candidates = prices.get(symbol, [])
                if not candidates:
                    continue
                candidates.sort(key=lambda c: c[0])
                px = _price_at(candidates[0][1], ts)
            total += v * px
        return float(total)

    current_balance = dict(balance)
    out = []
    idx = 0
    # newest -> oldest so transactions are unwrapped as we move back in time
    for i in range(total_points - 1, -1, -1):
        ts = start + step * i
        if ts > now:
            continue
        while idx < len(txs) and _utc(txs[idx].created_at) > ts:
            balance[txs[idx].asset_id] -= Decimal(str(txs[idx].delta))
            idx += 1
        out.append({"time": ts, "value": usd_value(balance, ts)})

    # final point at current time uses untouched current balances
    out.append({"time": now, "value": usd_value(current_balance, now)})

    return sorted(out, key=lambda p: p["time"])
