"""Authenticated user watchlist endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DatabaseSession
from app.models.watchlist import Watchlist, WatchlistStock
from app.schemas.watchlist import (
    WatchlistCreateRequest,
    WatchlistResponse,
    WatchlistStockMutationResponse,
    WatchlistStockRequest,
    WatchlistStockResponse,
)
from app.services.state_manager import (
    WatchlistStateError,
    add_stock,
    get_or_create_default_watchlist,
    get_user_watchlist,
    remove_stock,
)


router = APIRouter(prefix="/watchlists", tags=["watchlists"])


def to_response(watchlist: Watchlist) -> WatchlistResponse:
    """Serialize a watchlist and its instrument details."""
    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        created_at=watchlist.created_at,
        stocks=[
            WatchlistStockResponse(
                symbol=entry.stock.symbol,
                name=entry.stock.name,
                exchange=entry.stock.exchange,
                added_at=entry.added_at,
            )
            for entry in sorted(watchlist.entries, key=lambda item: item.stock.symbol)
        ],
    )


def load_response(database: DatabaseSession, user_id: str, watchlist_id: str) -> WatchlistResponse:
    """Load a fully populated, owner-scoped watchlist response."""
    return to_response(get_user_watchlist(database, user_id, watchlist_id))


@router.get("", response_model=list[WatchlistResponse])
def list_watchlists(current_user: CurrentUser, database: DatabaseSession) -> list[WatchlistResponse]:
    """List every watchlist owned by the authenticated user."""
    watchlists = database.scalars(
        select(Watchlist)
        .where(Watchlist.user_id == current_user.id)
        .options(selectinload(Watchlist.entries).selectinload(WatchlistStock.stock))
        .order_by(Watchlist.created_at)
    )
    return [to_response(watchlist) for watchlist in watchlists]


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def create_watchlist(
    payload: WatchlistCreateRequest, current_user: CurrentUser, database: DatabaseSession
) -> WatchlistResponse:
    """Create a named stock collection for the current user."""
    watchlist = Watchlist(user_id=current_user.id, name=payload.name)
    database.add(watchlist)
    database.commit()
    database.refresh(watchlist)
    return load_response(database, current_user.id, watchlist.id)


@router.get("/default", response_model=WatchlistResponse)
def get_default_watchlist(current_user: CurrentUser, database: DatabaseSession) -> WatchlistResponse:
    """Return the default watchlist, creating it when first requested."""
    watchlist = get_or_create_default_watchlist(database, current_user.id)
    return load_response(database, current_user.id, watchlist.id)


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(
    watchlist_id: str, current_user: CurrentUser, database: DatabaseSession
) -> WatchlistResponse:
    """Return a particular owned watchlist."""
    try:
        return load_response(database, current_user.id, watchlist_id)
    except WatchlistStateError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{watchlist_id}/stocks", response_model=WatchlistStockMutationResponse)
def add_stock_to_watchlist(
    watchlist_id: str,
    payload: WatchlistStockRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> WatchlistStockMutationResponse:
    """Add a catalogue stock and enter the tracked-but-unseen state."""
    try:
        entry = add_stock(database, current_user.id, watchlist_id, payload.symbol)
    except WatchlistStateError as error:
        code = status.HTTP_409_CONFLICT if "already" in str(error) else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(error)) from error
    return WatchlistStockMutationResponse(
        watchlist_id=watchlist_id,
        symbol=payload.symbol,
        state="tracked_unseen",
    )


@router.delete("/{watchlist_id}/stocks/{symbol}", response_model=WatchlistStockMutationResponse)
def remove_stock_from_watchlist(
    watchlist_id: str, symbol: str, current_user: CurrentUser, database: DatabaseSession
) -> WatchlistStockMutationResponse:
    """Remove a stock and clear stale state when it is no longer watched anywhere."""
    try:
        remove_stock(database, current_user.id, watchlist_id, symbol)
    except WatchlistStateError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return WatchlistStockMutationResponse(
        watchlist_id=watchlist_id,
        symbol=symbol.strip().upper(),
        state="untracked",
    )
