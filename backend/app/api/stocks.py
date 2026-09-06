"""Stock catalogue and market-data endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DatabaseSession
from app.models.market import Stock
from app.schemas.market import PriceHistoryPointResponse, QuoteResponse, StockCreateRequest, StockResponse
from app.services.market_data import MarketDataError, fetch_historical_prices, get_or_refresh_quote


router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=list[StockResponse])
def list_stocks(_: CurrentUser, database: DatabaseSession) -> list[StockResponse]:
    return list(database.scalars(select(Stock).order_by(Stock.symbol.asc())))


@router.post("", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
def create_stock(payload: StockCreateRequest, _: CurrentUser, database: DatabaseSession) -> StockResponse:
    symbol = payload.symbol
    existing = database.scalar(select(Stock).where(Stock.symbol == symbol))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stock already exists")
    stock = Stock(symbol=symbol, name=payload.name, exchange=payload.exchange)
    database.add(stock)
    database.commit()
    database.refresh(stock)
    return StockResponse.model_validate(stock)


@router.get("/{symbol}/quote", response_model=QuoteResponse)
def get_quote(symbol: str, _: CurrentUser, database: DatabaseSession, refresh: bool = False) -> QuoteResponse:
    try:
        stored = get_or_refresh_quote(database, symbol, force_refresh=refresh)
    except MarketDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    observation = stored.observation
    return QuoteResponse(
        symbol=stored.stock.symbol,
        price=observation.price,
        volume=observation.volume,
        source=observation.source,
        provider_timestamp=observation.provider_timestamp,
        captured_at=observation.captured_at,
        is_cached=stored.is_cached,
    )


@router.get("/{symbol}/history", response_model=list[PriceHistoryPointResponse])
def get_price_history(
    symbol: str,
    _: CurrentUser,
    database: DatabaseSession,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PriceHistoryPointResponse]:
    normalized = symbol.strip().upper()
    stock = database.scalar(select(Stock).where(Stock.symbol == normalized))
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")

    try:
        points = fetch_historical_prices(normalized, stock, limit=limit)
    except MarketDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    return [
        PriceHistoryPointResponse(
            price=point.price,
            volume=point.volume,
            recorded_at=point.timestamp,
        )
        for point in points
    ]


@router.post("/{symbol}/refresh", response_model=QuoteResponse)
def refresh_quote(symbol: str, _: CurrentUser, database: DatabaseSession) -> QuoteResponse:
    try:
        stored = get_or_refresh_quote(database, symbol, force_refresh=True)
    except MarketDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    observation = stored.observation
    return QuoteResponse(
        symbol=stored.stock.symbol,
        price=observation.price,
        volume=observation.volume,
        source=observation.source,
        provider_timestamp=observation.provider_timestamp,
        captured_at=observation.captured_at,
        is_cached=False,
    )
