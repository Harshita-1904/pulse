"""Stock catalogue and market quote endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DatabaseSession
from app.models.market import PriceHistory, Stock
from app.schemas.market import (
    PriceHistoryPointResponse,
    QuoteResponse,
    StockCreateRequest,
    StockResponse,
)
from app.services.market_data import MarketDataError, StoredQuote, get_or_refresh_quote


router = APIRouter(prefix="/stocks", tags=["stocks"])


def to_quote_response(quote: StoredQuote) -> QuoteResponse:
    """Translate a persisted quote to its API response."""
    observation = quote.observation
    return QuoteResponse(
        symbol=quote.stock.symbol,
        price=observation.price,
        volume=observation.volume,
        source=observation.source,
        provider_timestamp=observation.provider_timestamp,
        captured_at=observation.captured_at,
        is_cached=quote.is_cached,
    )


@router.get("", response_model=list[StockResponse])
def list_stocks(_: CurrentUser, database: DatabaseSession) -> list[Stock]:
    """List instruments that have been added or collected by Pulse."""
    return list(database.scalars(select(Stock).order_by(Stock.symbol)))


@router.post("", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
def create_stock(payload: StockCreateRequest, _: CurrentUser, database: DatabaseSession) -> Stock:
    """Create a stock entry before a first market refresh."""
    existing = database.scalar(select(Stock).where(Stock.symbol == payload.symbol))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stock already exists")

    stock = Stock(symbol=payload.symbol, name=payload.name, exchange=payload.exchange)
    database.add(stock)
    database.commit()
    database.refresh(stock)
    return stock


@router.get("/{symbol}/quote", response_model=QuoteResponse)
def get_quote(
    symbol: str,
    _: CurrentUser,
    database: DatabaseSession,
    refresh: bool = Query(default=False, description="Bypass the local freshness cache"),
) -> QuoteResponse:
    """Return a recent quote, collecting a new one when the cache is stale."""
    try:
        return to_quote_response(get_or_refresh_quote(database, symbol, force_refresh=refresh))
    except MarketDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.get("/{symbol}/history", response_model=list[PriceHistoryPointResponse])
def get_price_history(
    symbol: str, _: CurrentUser, database: DatabaseSession, limit: int = Query(default=100, ge=1, le=500)
) -> list[PriceHistory]:
    """Return locally recorded observations for the stock-details chart."""
    stock = database.scalar(select(Stock).where(Stock.symbol == symbol.strip().upper()))
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock has not been collected yet")
    history = database.scalars(
        select(PriceHistory)
        .where(PriceHistory.stock_id == stock.id)
        .order_by(PriceHistory.recorded_at.desc())
        .limit(limit)
    )
    return list(reversed(list(history)))


@router.post("/{symbol}/refresh", response_model=QuoteResponse)
def refresh_quote(symbol: str, _: CurrentUser, database: DatabaseSession) -> QuoteResponse:
    """Force a new market-data collection for one instrument."""
    try:
        return to_quote_response(get_or_refresh_quote(database, symbol, force_refresh=True))
    except MarketDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
