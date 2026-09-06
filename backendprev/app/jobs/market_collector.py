"""Command-line collector for refreshing a defined group of market symbols."""

import sys

from app.database.session import SessionLocal
from app.services.market_data import MarketDataError, get_or_refresh_quote


def main(symbols: list[str]) -> None:
    """Refresh each requested symbol independently so one failure does not stop the batch."""
    if not symbols:
        raise SystemExit("Usage: python -m app.jobs.market_collector SYMBOL [SYMBOL ...]")

    database = SessionLocal()
    try:
        for symbol in symbols:
            try:
                quote = get_or_refresh_quote(database, symbol, force_refresh=True)
                print(f"{quote.stock.symbol}: {quote.observation.price}")
            except MarketDataError as error:
                print(f"{symbol}: failed ({error})", file=sys.stderr)
                database.rollback()
    finally:
        database.close()


if __name__ == "__main__":
    main(sys.argv[1:])
