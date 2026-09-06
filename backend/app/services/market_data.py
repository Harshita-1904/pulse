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
from app.services.twelve_data import TwelveDataError, get_historical_prices as twelve_history, get_quote as twelve_quote


class MarketDataError(Exception):
    """A provider, validation, or upstream availability failure."""


@dataclass(frozen=True)
class ProviderQuote:
    symbol: str
    price: float
    volume: float | None
    source: str
    provider_timestamp: datetime | None


@dataclass(frozen=True)
class StoredQuote:
    stock: Stock
    observation: MarketData
    is_cached: bool


@dataclass(frozen=True)
class HistoricalPoint:
    timestamp: datetime
    price: float
    volume: float | None = None


class QuoteProvider(Protocol):
    def fetch_quote(self, symbol: str, stock: Stock | None = None) -> ProviderQuote:
        ...


def validate_quote(price: float, volume: float | None) -> None:
    if not isfinite(price) or price <= 0:
        raise MarketDataError("Provider returned an invalid price")
    if volume is not None and (not isfinite(volume) or volume < 0):
        raise MarketDataError("Provider returned an invalid volume")


class TwelveDataQuoteProvider:
    source_name = "twelve_data"

    def fetch_quote(self, symbol: str, stock: Stock | None = None) -> ProviderQuote:
        try:
            quote = twelve_quote(symbol, stock.exchange if stock else None)
            validate_quote(quote.price, quote.volume)
            return ProviderQuote(
                symbol=symbol.strip().upper(),
                price=quote.price,
                volume=quote.volume,
                source=self.source_name,
                provider_timestamp=quote.provider_timestamp,
            )
        except TwelveDataError as error:
            raise MarketDataError(str(error)) from error


class AlphaVantageQuoteProvider:
    """Alpha Vantage GLOBAL_QUOTE adapter."""

    source_name = "alpha_vantage"

    @staticmethod
    def provider_symbols(symbol: str, stock: Stock | None) -> list[str]:
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
                    params={"function": "GLOBAL_QUOTE", "symbol": provider_symbol, "apikey": settings.market_data_api_key},
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
                errors.append(f"{provider_symbol}: {message or 'no quote returned'}")
                continue
            try:
                price = float(quote["05. price"])
                raw_volume = quote.get("06. volume")
                volume = float(raw_volume) if raw_volume not in (None, "") else None
                raw_date = quote.get("07. latest trading day")
                provider_timestamp = datetime.fromisoformat(raw_date).replace(tzinfo=UTC) if raw_date else None
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"{provider_symbol}: invalid quote ({error})")
                continue
            validate_quote(price, volume)
            return ProviderQuote(symbol=symbol.strip().upper(), price=price, volume=volume, source=self.source_name, provider_timestamp=provider_timestamp)
        raise MarketDataError("Alpha Vantage did not return a quote")


class YahooFinanceQuoteProvider:
    """Yahoo Finance no-key fallback for hackathon/demo use."""

    source_name = "yahoo_finance"
    chart_url = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    @staticmethod
    def provider_symbol(symbol: str, stock: Stock | None) -> str:
        normalized = symbol.strip().upper()
        if "." in normalized:
            return normalized
        exchange = (stock.exchange or "").strip().upper() if stock else ""
        return f"{normalized}.BO" if exchange == "BSE" else f"{normalized}.NS"

    def fetch_quote(self, symbol: str, stock: Stock | None = None) -> ProviderQuote:
        provider_symbol = self.provider_symbol(symbol, stock)
        try:
            response = httpx.get(self.chart_url.format(symbol=provider_symbol), params={"range": "1d", "interval": "1m", "events": "div,splits"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=get_settings().market_data_timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise MarketDataError(f"Yahoo Finance request failed for {provider_symbol}") from error
        chart = payload.get("chart", {})
        result = chart.get("result")
        if not isinstance(result, list) or not result:
            raise MarketDataError(f"Yahoo Finance returned no data for {provider_symbol}")
        data = result[0]
        meta = data.get("meta") or {}
        price = meta.get("regularMarketPrice")
        volume = meta.get("regularMarketVolume")
        epoch = meta.get("regularMarketTime")
        if price is None:
            timestamps = data.get("timestamp") or []
            quote_rows = (data.get("indicators") or {}).get("quote") or []
            closes = quote_rows[0].get("close") if quote_rows else []
            volumes = quote_rows[0].get("volume") if quote_rows else []
            for index in range(len(timestamps) - 1, -1, -1):
                if index < len(closes) and closes[index] is not None:
                    price = closes[index]
                    if volume is None and index < len(volumes):
                        volume = volumes[index]
                    epoch = timestamps[index]
                    break
        if price is None:
            raise MarketDataError(f"Yahoo Finance returned no price for {provider_symbol}")
        normalized_price = float(price)
        normalized_volume = float(volume) if volume is not None else None
        validate_quote(normalized_price, normalized_volume)
        timestamp = datetime.fromtimestamp(int(epoch), tz=UTC) if epoch else None
        return ProviderQuote(symbol=symbol.strip().upper(), price=normalized_price, volume=normalized_volume, source=self.source_name, provider_timestamp=timestamp)


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 32 or not all(character.isalnum() or character in ".-" for character in normalized):
        raise MarketDataError("Invalid stock symbol")
    return normalized


def _fetch_with_fallback(symbol: str, stock: Stock | None) -> ProviderQuote:
    settings = get_settings()
    provider_order = [settings.market_data_provider.strip().lower()]
    for provider_name in ("twelve_data", "alpha_vantage", "yahoo_finance"):
        if provider_name not in provider_order:
            provider_order.append(provider_name)

    errors: list[str] = []
    for provider_name in provider_order:
        try:
            if provider_name == "twelve_data":
                if not settings.twelve_data_api_key:
                    continue
                return TwelveDataQuoteProvider().fetch_quote(symbol, stock)
            if provider_name == "alpha_vantage":
                if not settings.market_data_api_key:
                    continue
                return AlphaVantageQuoteProvider().fetch_quote(symbol, stock)
            if provider_name == "yahoo_finance":
                return YahooFinanceQuoteProvider().fetch_quote(symbol, stock)
        except MarketDataError as error:
            errors.append(f"{provider_name}: {error}")

    raise MarketDataError("No market-data provider returned a quote. " + " | ".join(errors))


def _get_stock(database: Session, symbol: str) -> Stock | None:
    return database.scalar(select(Stock).where(Stock.symbol == symbol))


def get_or_refresh_quote(database: Session, symbol: str, *, force_refresh: bool = False) -> StoredQuote:
    normalized_symbol = normalize_symbol(symbol)
    stock = _get_stock(database, normalized_symbol)
    latest = None
    if stock is not None:
        latest = database.scalar(select(MarketData).where(MarketData.stock_id == stock.id).order_by(MarketData.captured_at.desc()).limit(1))

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
    database.add(PriceHistory(stock_id=stock.id, price=provider_quote.price, volume=provider_quote.volume))
    database.commit()
    database.refresh(observation)
    return StoredQuote(stock=stock, observation=observation, is_cached=False)


def fetch_historical_prices(symbol: str, stock: Stock | None = None, limit: int = 100) -> list[HistoricalPoint]:
    """Fetch chart history from Twelve Data first, then configured fallbacks."""
    settings = get_settings()
    errors: list[str] = []
    providers = ["twelve_data", "alpha_vantage", "yahoo_finance"]
    for provider_name in providers:
        try:
            if provider_name == "twelve_data":
                if not settings.twelve_data_api_key:
                    continue
                rows = twelve_history(symbol, stock.exchange if stock else None, interval="1day", outputsize=limit)
                return [HistoricalPoint(r.timestamp, r.price, r.volume) for r in rows]

            if provider_name == "alpha_vantage":
                if not settings.market_data_api_key:
                    continue
                response = httpx.get(settings.market_data_base_url, params={"function": "TIME_SERIES_DAILY", "symbol": symbol.strip().upper(), "outputsize": "compact", "apikey": settings.market_data_api_key}, timeout=settings.market_data_timeout_seconds)
                response.raise_for_status()
                payload = response.json()
                series = payload.get("Time Series (Daily)")
                if not isinstance(series, dict):
                    errors.append("alpha_vantage: historical data unavailable")
                    continue
                points: list[HistoricalPoint] = []
                for raw_timestamp, values in series.items():
                    try:
                        timestamp = datetime.fromisoformat(raw_timestamp).replace(tzinfo=UTC)
                        price = float(values["4. close"])
                        raw_volume = values.get("5. volume")
                        volume = float(raw_volume) if raw_volume not in (None, "") else None
                        points.append(HistoricalPoint(timestamp, price, volume))
                    except (KeyError, TypeError, ValueError):
                        continue
                points.sort(key=lambda p: p.timestamp)
                if points:
                    return points[-limit:]
                continue

            if provider_name == "yahoo_finance":
                # Yahoo fallback provides a recent daily history without an API key.
                provider_symbol = YahooFinanceQuoteProvider.provider_symbol(symbol, stock)
                response = httpx.get(YahooFinanceQuoteProvider.chart_url.format(symbol=provider_symbol), params={"range": "1y", "interval": "1d", "events": "div,splits"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=settings.market_data_timeout_seconds)
                response.raise_for_status()
                payload = response.json()
                result = (payload.get("chart") or {}).get("result")
                if not isinstance(result, list) or not result:
                    continue
                data = result[0]
                timestamps = data.get("timestamp") or []
                quote_rows = (data.get("indicators") or {}).get("quote") or []
                quote = quote_rows[0] if quote_rows else {}
                closes = quote.get("close") or []
                volumes = quote.get("volume") or []
                points = []
                for idx, epoch in enumerate(timestamps):
                    if idx >= len(closes) or closes[idx] is None:
                        continue
                    volume = volumes[idx] if idx < len(volumes) else None
                    points.append(HistoricalPoint(datetime.fromtimestamp(int(epoch), tz=UTC), float(closes[idx]), float(volume) if volume is not None else None))
                if points:
                    return points[-limit:]
        except (httpx.HTTPError, ValueError, TwelveDataError, MarketDataError) as error:
            errors.append(f"{provider_name}: {error}")
            continue

    raise MarketDataError("Historical market data unavailable. " + " | ".join(errors))
