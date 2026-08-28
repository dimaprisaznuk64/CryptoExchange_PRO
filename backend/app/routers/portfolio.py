from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioResponse,
    PortfolioItem,
    RecentTrade,
    PortfolioHistoryPoint,
)
from app.services import portfolio as portfolio_service

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
async def my_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await portfolio_service.get_portfolio(db, current_user.id)
    return PortfolioResponse(
        total_usd=data["total_usd"],
        items=[PortfolioItem(**i) for i in data["items"]],
    )


@router.get("/trades", response_model=list[RecentTrade])
async def recent_trades(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trades = await portfolio_service.get_recent_trades(db, current_user.id, limit)
    return [RecentTrade(**t) for t in trades]


@router.get("/history", response_model=list[PortfolioHistoryPoint])
async def portfolio_history(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    points = await portfolio_service.get_portfolio_history(
        db, current_user.id, days=days
    )
    return [PortfolioHistoryPoint(**p) for p in points]
