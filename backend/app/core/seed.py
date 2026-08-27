import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.trading_pair import TradingPair, PairStatus

logger = logging.getLogger(__name__)

ASSETS = [
    {"symbol": "USD", "name": "US Dollar", "decimals": 2, "is_fiat": True},
    {"symbol": "USDT", "name": "Tether", "decimals": 6, "is_fiat": False},
    {"symbol": "BTC", "name": "Bitcoin", "decimals": 8, "is_fiat": False},
    {"symbol": "ETH", "name": "Ethereum", "decimals": 8, "is_fiat": False},
]

PAIRS = [
    {"base": "BTC", "quote": "USDT", "price_precision": 2, "qty_precision": 6},
    {"base": "ETH", "quote": "USDT", "price_precision": 2, "qty_precision": 4},
    {"base": "BTC", "quote": "USD", "price_precision": 2, "qty_precision": 6},
    {"base": "ETH", "quote": "USD", "price_precision": 2, "qty_precision": 4},
]


async def seed_catalog(db: AsyncSession) -> None:
    asset_ids: dict[str, str] = {}

    for a in ASSETS:
        res = await db.execute(select(Asset).where(Asset.symbol == a["symbol"]))
        asset = res.scalar_one_or_none()
        if asset is None:
            asset = Asset(
                symbol=a["symbol"],
                name=a["name"],
                decimals=a["decimals"],
                is_fiat=a["is_fiat"],
            )
            db.add(asset)
            await db.flush()
            asset_ids[a["symbol"]] = asset.id
        else:
            asset_ids[a["symbol"]] = asset.id

    for p in PAIRS:
        symbol = f"{p['base']}/{p['quote']}"
        res = await db.execute(select(TradingPair).where(TradingPair.symbol == symbol))
        pair = res.scalar_one_or_none()
        if pair is None:
            pair = TradingPair(
                symbol=symbol,
                base_asset_id=asset_ids[p["base"]],
                quote_asset_id=asset_ids[p["quote"]],
                price_precision=p["price_precision"],
                qty_precision=p["qty_precision"],
                status=PairStatus.active,
                is_active=True,
            )
            db.add(pair)

    await db.commit()
    logger.info("Market catalog seeded")
