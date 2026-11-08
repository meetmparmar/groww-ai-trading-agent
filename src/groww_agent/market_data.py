from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


class MarketDataError(ValueError):
    """Raised when local market data is missing or invalid."""


@dataclass(frozen=True, slots=True)
class DailyBar:
    symbol: str
    exchange: str
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


_REQUIRED_COLUMNS = {
    "date",
    "symbol",
    "exchange",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def _decimal(value: str | None, *, field: str, line: int) -> Decimal:
    if value is None:
        raise MarketDataError(f"CSV line {line}: {field} is missing.")
    try:
        parsed = Decimal(value.strip())
    except (InvalidOperation, ValueError) as error:
        raise MarketDataError(f"CSV line {line}: {field} must be numeric.") from error
    if not parsed.is_finite() or parsed <= 0:
        raise MarketDataError(f"CSV line {line}: {field} must be finite and positive.")
    return parsed


def load_daily_bars(path: Path) -> tuple[DailyBar, ...]:
    """Load validated, completed daily OHLCV bars from a local CSV file."""
    if not path.is_file():
        raise MarketDataError(f"Market-data CSV does not exist: {path}")

    bars: list[DailyBar] = []
    seen: set[tuple[str, str, date]] = set()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise MarketDataError("Market-data CSV is empty or has no header.")
            headers = [header.strip().lower() for header in reader.fieldnames]
            if len(headers) != len(set(headers)):
                raise MarketDataError("Market-data CSV contains duplicate column names.")
            missing = _REQUIRED_COLUMNS.difference(headers)
            if missing:
                raise MarketDataError(
                    "Market-data CSV is missing columns: " + ", ".join(sorted(missing))
                )
            reader.fieldnames = headers

            for line, row in enumerate(reader, start=2):
                if None in row:
                    raise MarketDataError(f"CSV line {line}: unexpected extra fields.")
                symbol = (row.get("symbol") or "").strip().upper()
                exchange = (row.get("exchange") or "").strip().upper()
                if not symbol:
                    raise MarketDataError(f"CSV line {line}: symbol is required.")
                if exchange not in {"NSE", "BSE"}:
                    raise MarketDataError(f"CSV line {line}: exchange must be NSE or BSE.")
                try:
                    session_date = date.fromisoformat((row.get("date") or "").strip())
                except ValueError as error:
                    raise MarketDataError(
                        f"CSV line {line}: date must use YYYY-MM-DD format."
                    ) from error

                values = {
                    field: _decimal(row.get(field), field=field, line=line)
                    for field in ("open", "high", "low", "close")
                }
                if values["high"] < max(values["open"], values["low"], values["close"]):
                    raise MarketDataError(f"CSV line {line}: high is below an OHLC value.")
                if values["low"] > min(values["open"], values["high"], values["close"]):
                    raise MarketDataError(f"CSV line {line}: low is above an OHLC value.")
                raw_volume = (row.get("volume") or "").strip()
                try:
                    volume = int(raw_volume)
                except ValueError as error:
                    raise MarketDataError(
                        f"CSV line {line}: volume must be a non-negative integer."
                    ) from error
                if volume < 0:
                    raise MarketDataError(
                        f"CSV line {line}: volume must be a non-negative integer."
                    )

                key = (symbol, exchange, session_date)
                if key in seen:
                    raise MarketDataError(
                        f"CSV line {line}: duplicate bar for {symbol} {exchange} "
                        f"on {session_date}."
                    )
                seen.add(key)
                bars.append(
                    DailyBar(
                        symbol=symbol,
                        exchange=exchange,
                        session_date=session_date,
                        open=values["open"],
                        high=values["high"],
                        low=values["low"],
                        close=values["close"],
                        volume=volume,
                    )
                )
    except OSError as error:
        raise MarketDataError(f"Could not read market-data CSV: {error}") from error
    except csv.Error as error:
        raise MarketDataError(f"Invalid market-data CSV: {error}") from error
    except UnicodeError as error:
        raise MarketDataError("Market-data CSV must use UTF-8 encoding.") from error

    if not bars:
        raise MarketDataError("Market-data CSV contains no daily bars.")
    return tuple(sorted(bars, key=lambda bar: (bar.session_date, bar.exchange, bar.symbol)))
