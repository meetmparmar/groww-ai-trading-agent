from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TradingStyle(str, Enum):
    """Valid trading styles for the paper-trading MVP."""

    INTRADAY = "intraday"
    SWING = "swing"


class InstrumentCategory(str, Enum):
    """Allowed instrument categories for the initial v1 market universe."""

    EQUITY = "equity"
    ETF = "etf"


@dataclass(frozen=True, slots=True)
class Instrument:
    """Metadata for each permitted market instrument in the India cash-equity universe."""

    symbol: str
    name: str
    exchange: str = "NSE"
    country: str = "IN"
    category: InstrumentCategory = InstrumentCategory.EQUITY
    allowed_styles: tuple[TradingStyle, ...] = (
        TradingStyle.INTRADAY,
        TradingStyle.SWING,
    )

    def supports_style(self, style: TradingStyle | str) -> bool:
        """Return True when the instrument is valid for a style."""
        normalized = TradingStyle(style) if isinstance(style, str) else style
        return normalized in self.allowed_styles


EXCLUDED_ASSET_CLASSES: tuple[str, ...] = (
    "FUTURES",
    "OPTIONS",
    "INDEX",
    "COMMODITY",
    "CURRENCY",
    "MUTUAL_FUND",
    "ETF",
    "UNLISTED",
    "DERIVATIVE",
)

SUPPORTED_STOCK_EXCHANGES: tuple[str, ...] = ("NSE", "BSE")


@dataclass(frozen=True, slots=True)
class MarketUniverse:
    """Scope and loaded listing catalog for the approved paper-trading universe."""

    name: str
    market: str
    country: str
    instruments: tuple[Instrument, ...] = ()
    exchanges: tuple[str, ...] = SUPPORTED_STOCK_EXCHANGES
    excluded_asset_classes: tuple[str, ...] = EXCLUDED_ASSET_CLASSES
    allowed_styles: tuple[TradingStyle, ...] = (
        TradingStyle.INTRADAY,
        TradingStyle.SWING,
    )
    notes: str = "All listed cash equities on NSE and BSE; the listing catalog must be loaded from a verified source."

    def __post_init__(self) -> None:
        known_listings = {(instrument.exchange, instrument.symbol) for instrument in self.instruments}
        if len(known_listings) != len(self.instruments):
            raise ValueError("Instrument listings must be unique by exchange and symbol.")
        for instrument in self.instruments:
            if instrument.exchange not in self.exchanges:
                raise ValueError(
                    f"{instrument.exchange} is not an allowed exchange in this universe."
                )
            if instrument.category is not InstrumentCategory.EQUITY:
                raise ValueError("Only cash-equity instruments are allowed in this universe.")

    def get_instrument(self, symbol: str, exchange: str | None = None) -> Instrument | None:
        normalized = symbol.upper()
        matches = tuple(
            instrument
            for instrument in self.instruments
            if instrument.symbol == normalized
            and (exchange is None or instrument.exchange == exchange.upper())
        )
        if len(matches) > 1:
            raise ValueError(
                f"{normalized} is listed on multiple exchanges; specify the exchange."
            )
        return matches[0] if matches else None

    def supports_style(
        self, symbol: str, style: TradingStyle | str, exchange: str | None = None
    ) -> bool:
        instrument = self.get_instrument(symbol, exchange)
        if instrument is None:
            return False
        return instrument.supports_style(style)

    def filter_by_style(self, style: TradingStyle | str) -> tuple[Instrument, ...]:
        normalized = TradingStyle(style) if isinstance(style, str) else style
        return tuple(
            instrument for instrument in self.instruments if instrument.supports_style(normalized)
        )

    def is_excluded(self, asset_class: str) -> bool:
        return asset_class.upper() in self.excluded_asset_classes


DEFAULT_EQUITY_UNIVERSE = MarketUniverse(
    name="india-equity-paper-universe",
    market="NSE+BSE",
    country="IN",
    excluded_asset_classes=EXCLUDED_ASSET_CLASSES,
    allowed_styles=(TradingStyle.INTRADAY, TradingStyle.SWING),
)

__all__ = [
    "DEFAULT_EQUITY_UNIVERSE",
    "EXCLUDED_ASSET_CLASSES",
    "Instrument",
    "InstrumentCategory",
    "MarketUniverse",
    "SUPPORTED_STOCK_EXCHANGES",
    "TradingStyle",
]
