"""Own the user-watchlist state transitions used by Pulse."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.market import Stock
from app.models.watchlist import UserStockState, Watchlist, WatchlistStock


class WatchlistStateError(Exception):
    """A watchlist transition cannot be completed safely."""


def normalize_symbol(symbol: str) -> str:
    """Normalize a stock symbol used by path and body parameters."""
    return symbol.strip().upper()


def get_user_watchlist(database: Session, user_id: str, watchlist_id: str) -> Watchlist:
    """Load a watchlist only when it belongs to the authenticated user."""
    watchlist = database.scalar(
        select(Watchlist)
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        .options(selectinload(Watchlist.entries).selectinload(WatchlistStock.stock))
    )
    if watchlist is None:
        raise WatchlistStateError("Watchlist was not found")
    return watchlist


def get_or_create_default_watchlist(database: Session, user_id: str) -> Watchlist:
    """Return a user's default watchlist, creating it on first use."""
    watchlist = database.scalar(
        select(Watchlist).where(Watchlist.user_id == user_id, Watchlist.name == "My Watchlist")
    )
    if watchlist is None:
        watchlist = Watchlist(user_id=user_id, name="My Watchlist")
        database.add(watchlist)
        database.commit()
        database.refresh(watchlist)
    return watchlist


def add_stock(database: Session, user_id: str, watchlist_id: str, symbol: str) -> WatchlistStock:
    """Transition a stock into a watchlist and initialize its unseen user state."""
    watchlist = get_user_watchlist(database, user_id, watchlist_id)
    normalized_symbol = normalize_symbol(symbol)
    stock = database.scalar(select(Stock).where(Stock.symbol == normalized_symbol))
    if stock is None:
        raise WatchlistStateError("Stock has not been added to the market catalogue")

    entry = database.scalar(
        select(WatchlistStock).where(
            WatchlistStock.watchlist_id == watchlist.id,
            WatchlistStock.stock_id == stock.id,
        )
    )
    if entry is not None:
        raise WatchlistStateError("Stock is already in this watchlist")

    entry = WatchlistStock(watchlist_id=watchlist.id, stock_id=stock.id)
    database.add(entry)
    state = database.scalar(
        select(UserStockState).where(
            UserStockState.user_id == user_id,
            UserStockState.stock_id == stock.id,
        )
    )
    if state is None:
        database.add(UserStockState(user_id=user_id, stock_id=stock.id))
    database.commit()
    database.refresh(entry)
    return entry


def remove_stock(database: Session, user_id: str, watchlist_id: str, symbol: str) -> None:
    """Remove membership and clear state only when no user watchlist still tracks it."""
    watchlist = get_user_watchlist(database, user_id, watchlist_id)
    normalized_symbol = normalize_symbol(symbol)
    entry = database.scalar(
        select(WatchlistStock)
        .join(Stock)
        .where(WatchlistStock.watchlist_id == watchlist.id, Stock.symbol == normalized_symbol)
    )
    if entry is None:
        raise WatchlistStateError("Stock is not in this watchlist")

    stock_id = entry.stock_id
    database.delete(entry)
    database.flush()

    remaining_entries = database.scalar(
        select(func.count(WatchlistStock.id))
        .join(Watchlist)
        .where(Watchlist.user_id == user_id, WatchlistStock.stock_id == stock_id)
    )
    if remaining_entries == 0:
        state = database.scalar(
            select(UserStockState).where(
                UserStockState.user_id == user_id,
                UserStockState.stock_id == stock_id,
            )
        )
        if state is not None:
            database.delete(state)
    database.commit()
