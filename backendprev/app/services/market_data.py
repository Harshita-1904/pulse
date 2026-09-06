"""Provider integration, validation, caching, and persistence for market quotes."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isfinite
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.market import MarketData, PriceHistory, Stock


class MarketDataError(Exception):
    """A provider, validation, or upstream availability failure."""


@dataclass(frozen=True)
class ProviderQuote:
    """Normalized raw quote returned from a market-data provider."""

    symbol: str
    price: float
    volume: float | None
    source: str
    provider_timestamp: datetime | None


@dataclass(frozen=True)
class StoredQuote:
    """A persisted quote together with whether it came from the local cache."""

    stock: Stock
    observation: MarketData
    is_cached: bool


class QuoteProvider(Protocol):
    """Interface implemented by individual market-data vendors."""

    def fetch_quote(self, symbol: str, stock: Stock | None = None) -> ProviderQuote:
        """Fetch and normalize a current quote for one market symbol."""


class AlphaVantageQuoteProvider:
    """Alpha Vantage GLOBAL_QUOTE adapter."""

    source_name = "alpha_vantage"

    @staticmethod
    def provider_symbols(symbol: str, stock: Stock | None) -> list[str]:
        """Return Alpha Vantage symbol variants, preferring the declared exchange."""
        normalized = symbol.strip().upper()
        exchange = (stock.exchange or "").strip().upper() if stock else ""

        if "." in normalized:
            return [normalized]
        if exchange == "NSE":
            return [f"{normalized}.NSE", f"{normalized}.BSE", normalized]
        if exchange == "BSE":
            return [f"{normalized}.BSE", f"{normalized}.NSE", normalized]
        return [normalized, f"{normalized}.NSE", f"{normalized}.BSE"]

    def fetch_quote(self, symbol: str, stock: Stock | None = None) -> ProviderQuote:
        settings = get_settings()
        if not settings.market_data_api_key:
            raise MarketDataError("MARKET_DATA_API_KEY is not configured")

        errors: list[str] = []
        for provider_symbol in self.provider_symbols(symbol, stock):
            try:
                response = httpx.get(
                    settings.market_data_base_url,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": provider_symbol,
                        "apikey": settings.market_data_api_key,
                    },
                    timeout=settings.market_data_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as error:
                errors.append(f"{provider_symbol}: provider unavailable ({error})")
                continue

            quote = payload.get("Global Quote")
            if not isinstance(quote, dict) or not quote:
                message = payload.get("Note") or payload.get("Information") or payload.get("Error Message")
                if message:
                    errors.append(f"{provider_symbol}: {message}")
                else:
                    errors.append(f"{provider_symbol}: no quote returned")
                continue

            try:
                price = float(quote["05. price"])
                raw_volume = quote.get("06. volume")
                volume = float(raw_volume) if raw_volume not in (None, "") else None
                raw_date = quote.get("07. latest trading day")
                provider_timestamp = (
                    datetime.fromisoformat(raw_date).replace(tzinfo=UTC) if raw_date else None
                )
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"{provider_symbol}: invalid quote ({error})")
                continue

            validate_quote(price, volume)
            return ProviderQuote(
                symbol=symbol,
                price=price,
                volume=volume,
                source=self.source_name,
                provider_timestamp=provider_timestamp,
            )

        raise MarketDataError("Alpha Vantage did not return a quote. " + " | ".join(errors))


class YahooFinanceQuoteProvider:
    """Yahoo Finance chart endpoint adapter used as a no-key fallback for NSE/BSE.

    Yahoo Finance is used here only as a practical hackathon/demo fallback. It is
    not an official trading-data API and should be replaced by a licensed provider
    for production use.
    """

    source_name = "yahoo_finance"
    chart_url = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    @staticmethod
    def provider_symbol(symbol: str, stock: Stock | None) -> str:
        normalized = symbol.strip().upper()
        if "." in normalized:
            return normalized

        exchange = (stock.exchange or "").strip().upper() if stock else ""
        if exchange == "BSE":
            return f"{normalized}.BO"
        # NSE is the default for Indian stocks in Pulse.
        return f"{normalized}.NS"

    def fetch_quote(self, symbol: str, stock: Stock | None = None) -> ProviderQuote:
        provider_symbol = self.provider_symbol(symbol, stock)
        try:
            response = httpx.get(
                self.chart_url.format(symbol=provider_symbol),
                params={"range": "1d", "interval": "1m", "events": "div,splits"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=get_settings().market_data_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise MarketDataError(f"Yahoo Finance request failed for {provider_symbol}: {error}") from error

        chart = payload.get("chart", {})
        result = chart.get("result")
        if not isinstance(result, list) or not result:
            error = chart.get("error") or {}
            description = error.get("description") if isinstance(error, dict) else None
            raise MarketDataError(
                f"Yahoo Finance returned no data for {provider_symbol}"
                + (f": {description}" if description else "")
            )

        data = result[0]
        meta = data.get("meta") or {}
        price = meta.get("regularMarketPrice")
        volume = meta.get("regularMarketVolume")
        epoch = meta.get("regularMarketTime")

        # Fall back to the most recent one-minute close if regularMarketPrice
        # is absent from the metadata.
        if price is None:
            timestamps = data.get("timestamp") or []
            indicators = data.get("indicators") or {}
            quote_rows = indicators.get("quote") or []
            closes = quote_rows[0].get("close") if quote_rows else []
            volumes = quote_rows[0].get("volume") if quote_rows else []
            if timestamps and closes:
                for index in range(len(timestamps) - 1, -1, -1):
                    if closes[index] is not None:
                        price = closes[index]
                        if volume is None and volumes and volumes[index] is not None:
                            volume = volumes[index]
                        epoch = timestamps[index]
                        break

        if price is None:
            raise MarketDataError(f"Yahoo Finance returned no price for {provider_symbol}")

        try:
            normalized_price = float(price)
            normalized_volume = float(volume) if volume is not None else None
        except (TypeError, ValueError) as error:
            raise MarketDataError(f"Yahoo Finance returned invalid values for {provider_symbol}") from error

        provider_timestamp = datetime.fromtimestamp(int(epoch), tz=UTC) if epoch else None
        validate_quote(normalized_price, normalized_volume)

        return ProviderQuote(
            symbol=symbol,
            price=normalized_price,
            volume=normalized_volume,
            source=self.source_name,
            provider_timestamp=provider_timestamp,
        )


def validate_quote(price: float, volume: float | None) -> None:
    """Reject invalid market observations before they reach persistence."""
    if not isfinite(price) or price <= 0:
        raise MarketDataError("Provider returned an invalid price")
    if volume is not None and (not isfinite(volume) or volume < 0):
        raise MarketDataError("Provider returned an invalid volume")


def get_quote_provider() -> QuoteProvider:
    """Return the enabled primary vendor implementation."""
    provider_name = get_settings().market_data_provider.lower().strip()
    if provider_name == "alpha_vantage":
        return AlphaVantageQuoteProvider()
    if provider_name == "yahoo_finance":
        return YahooFinanceQuoteProvider()
    raise MarketDataError(f"Unsupported market-data provider: {provider_name}")


def normalize_symbol(symbol: str) -> str:
    """Normalize a symbol received through a path parameter or background job."""
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 32 or not all(
        character.isalnum() or character in ".-" for character in normalized
    ):
        raise MarketDataError("Invalid stock symbol")
    return normalized


def _fetch_with_fallback(symbol: str, stock: Stock | None) -> ProviderQuote:
    """Try configured provider, then Yahoo Finance for Indian stocks."""
    settings = get_settings()
    primary = get_quote_provider()
    try:
        return primary.fetch_quote(symbol, stock)
    except MarketDataError as primary_error:
        is_indian_stock = (stock is not None and (stock.exchange or "").strip().upper() in {"NSE", "BSE"}) or ".NSE" in symbol or ".BSE" in symbol
        if settings.market_data_provider.lower().strip() == "alpha_vantage" and is_indian_stock:
            try:
                return YahooFinanceQuoteProvider().fetch_quote(symbol, stock)
            except MarketDataError as fallback_error:
                raise MarketDataError(
                    f"Primary provider failed: {primary_error}. Yahoo Finance fallback failed: {fallback_error}"
                ) from fallback_error
        raise


def get_or_refresh_quote(database: Session, symbol: str, *, force_refresh: bool = False) -> StoredQuote:
    """Serve a fresh cached quote or collect, validate, and persist a new one."""
    normalized_symbol = normalize_symbol(symbol)
    stock = database.scalar(select(Stock).where(Stock.symbol == normalized_symbol))
    latest = None
    if stock is not None:
        latest = database.scalar(
            select(MarketData)
            .where(MarketData.stock_id == stock.id)
            .order_by(MarketData.captured_at.desc())
            .limit(1)
        )

    max_age = timedelta(seconds=get_settings().market_data_max_age_seconds)
    now = datetime.now(UTC)
    if latest is not None and not force_refresh and now - latest.captured_at <= max_age:
        return StoredQuote(stock=stock, observation=latest, is_cached=True)

    provider_quote = _fetch_with_fallback(normalized_symbol, stock)
    if stock is None:
        stock = Stock(symbol=normalized_symbol)
        database.add(stock)
        database.flush()

    observation = MarketData(
        stock_id=stock.id,
        price=provider_quote.price,
        volume=provider_quote.volume,
        source=provider_quote.source,
        provider_timestamp=provider_quote.provider_timestamp,
    )
    database.add(observation)
    database.add(
        PriceHistory(
            stock_id=stock.id,
            price=provider_quote.price,
            volume=provider_quote.volume,
        )
    )
    database.commit()
    database.refresh(observation)
    return StoredQuote(stock=stock, observation=observation, is_cached=False)
