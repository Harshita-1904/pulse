"""Compose watchlist membership, stored market data, and change intelligence."""

from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist
from app.services.change_engine import ChangeSummary, calculate_change
from app.services.state_manager import get_user_watchlist


def get_overview(
    database: Session,
    user_id: str,
    watchlist_id: str,
) -> tuple[Watchlist, list[ChangeSummary]]:
    """Return an owned watchlist and its per-stock intelligence summaries."""

    watchlist = get_user_watchlist(
        database,
        user_id,
        watchlist_id,
    )

    summaries = [
        calculate_change(
            database,
            user_id,
            entry.stock.symbol,
        )
        for entry in watchlist.entries
    ]

    return watchlist, summaries