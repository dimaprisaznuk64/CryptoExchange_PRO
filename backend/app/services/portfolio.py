import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet, WalletType
from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.models.trade import Trade
from app.services.market import _current_price

logger = logging.getLogger(__name__)

USD_QUOTES = ("USD", "USDT")


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
