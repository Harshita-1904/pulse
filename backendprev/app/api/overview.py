"""Frontend-oriented aggregate endpoints for a smart watchlist screen."""

from fastapi import APIRouter, HTTPException, status

from app.api.changes import to_response
from app.api.deps import CurrentUser, DatabaseSession
from app.schemas.overview import (
    BatchRefreshItem,
    BatchRefreshResponse,
    MissedAlertResponse,
    WatchlistOverviewResponse,
)
from app.services.change_engine import ChangeIntelligenceError, mark_seen
from app.services.market_data import MarketDataError, get_or_refresh_quote
from app.services.state_manager import WatchlistStateError, get_user_watchlist
from app.services.watchlist_overview import get_overview


router = APIRouter(prefix="/watchlists", tags=["watchlist intelligence"])


@router.get("/{watchlist_id}/overview", response_model=WatchlistOverviewResponse)
def get_watchlist_overview(
    watchlist_id: str, current_user: CurrentUser, database: DatabaseSession
) -> WatchlistOverviewResponse:
    """Return every stock's change summary in one dashboard-ready response."""
    try:
        watchlist, summaries = get_overview(database, current_user.id, watchlist_id)
    except (WatchlistStateError, ChangeIntelligenceError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    changed = [summary for summary in summaries if summary.direction in {"up", "down"}]
    response = WatchlistOverviewResponse(
        watchlist_id=watchlist.id,
        watchlist_name=watchlist.name,
        total_stocks=len(summaries),
        changed_count=len(changed),
        up_count=sum(summary.direction == "up" for summary in summaries),
        down_count=sum(summary.direction == "down" for summary in summaries),
        unseen_count=sum(summary.direction == "first_view" for summary in summaries),
        items=[to_response(summary) for summary in summaries],
    )
    # Preserve the calculated snapshot in the response, then make its prices the
    # next baseline. This prevents a view from ever comparing a quote to itself.
    for summary in summaries:
        if summary.data_status != "unavailable":
            mark_seen(database, current_user.id, summary.symbol)
    return response


@router.post("/{watchlist_id}/refresh", response_model=BatchRefreshResponse)
def refresh_watchlist(
    watchlist_id: str, current_user: CurrentUser, database: DatabaseSession
) -> BatchRefreshResponse:
    """Force refresh every stock while allowing individual provider failures."""
    try:
        watchlist = get_user_watchlist(database, current_user.id, watchlist_id)
    except WatchlistStateError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    items: list[BatchRefreshItem] = []
    for entry in watchlist.entries:
        symbol = entry.stock.symbol
        try:
            get_or_refresh_quote(database, symbol, force_refresh=True)
            items.append(BatchRefreshItem(symbol=symbol, status="refreshed"))
        except MarketDataError as error:
            database.rollback()
            items.append(BatchRefreshItem(symbol=symbol, status="failed", detail=str(error)))

    failed_count = sum(item.status == "failed" for item in items)
    return BatchRefreshResponse(
        watchlist_id=watchlist.id,
        refreshed_count=len(items) - failed_count,
        failed_count=failed_count,
        items=items,
    )
