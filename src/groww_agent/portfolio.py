from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping


class PortfolioError(ValueError):
    """Raised when fills cannot form a consistent long-only paper portfolio."""


@dataclass(frozen=True, slots=True)
class TradeFill:
    symbol: str
    exchange: str
    side: str
    quantity: int
    price: Decimal | float
    fees: Decimal | float
    filled_at: str


@dataclass(frozen=True, slots=True)
class PositionValuation:
    symbol: str
    exchange: str
    quantity: int
    average_cost: Decimal
    mark_price: Decimal | None
    market_value: Decimal | None
    unrealized_pnl: Decimal | None


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    cash: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal | None
    net_liquidation: Decimal | None
    total_fees: Decimal
    positions: tuple[PositionValuation, ...]
    missing_marks: tuple[tuple[str, str], ...]


def _money(value: Decimal | float, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise PortfolioError(f"{name} must be a finite number.") from error
    if not result.is_finite():
        raise PortfolioError(f"{name} must be a finite number.")
    return result


def build_portfolio_snapshot(
    *,
    starting_cash: Decimal | float,
    fills: Iterable[TradeFill],
    marks: Mapping[tuple[str, str], Decimal | float],
) -> PortfolioSnapshot:
    """Account for long-only fills and value positions using explicitly supplied marks."""
    initial_cash = _money(starting_cash, "Starting cash")
    if initial_cash <= 0:
        raise PortfolioError("Starting cash must be positive.")

    def fill_time(fill: TradeFill) -> datetime:
        try:
            timestamp = datetime.fromisoformat(fill.filled_at)
        except ValueError as error:
            raise PortfolioError("Fill timestamp must be ISO-8601.") from error
        if timestamp.tzinfo is None:
            raise PortfolioError("Fill timestamp must include a timezone.")
        return timestamp.astimezone(timezone.utc)

    ordered_fills = sorted(fills, key=fill_time)
    normalized_marks = {
        (symbol.upper(), exchange.upper()): price
        for (symbol, exchange), price in marks.items()
    }
    cash = initial_cash
    realized_pnl = Decimal(0)
    total_fees = Decimal(0)
    positions: dict[tuple[str, str], tuple[int, Decimal]] = {}

    for fill in ordered_fills:
        key = (fill.symbol.upper(), fill.exchange.upper())
        if not fill.symbol.strip() or fill.exchange.upper() not in {"NSE", "BSE"}:
            raise PortfolioError("Each fill must identify a supported exchange and symbol.")
        if fill.side not in {"BUY", "SELL"}:
            raise PortfolioError("Fill side must be BUY or SELL.")
        if isinstance(fill.quantity, bool) or not isinstance(fill.quantity, int) or fill.quantity <= 0:
            raise PortfolioError("Fill quantity must be a positive integer.")
        price = _money(fill.price, "Fill price")
        fees = _money(fill.fees, "Fill fees")
        if price <= 0 or fees < 0:
            raise PortfolioError("Fill price must be positive and fees non-negative.")
        quantity, cost_basis = positions.get(key, (0, Decimal(0)))
        total_fees += fees

        if fill.side == "BUY":
            cash -= price * fill.quantity + fees
            positions[key] = (
                quantity + fill.quantity,
                cost_basis + price * fill.quantity + fees,
            )
        else:
            if fill.quantity > quantity:
                raise PortfolioError(
                    f"Sell quantity exceeds the open {key[0]} position on {key[1]}."
                )
            average_cost = cost_basis / quantity
            realized_pnl += (price - average_cost) * fill.quantity - fees
            cash += price * fill.quantity - fees
            remaining = quantity - fill.quantity
            if remaining:
                positions[key] = (remaining, cost_basis - average_cost * fill.quantity)
            else:
                del positions[key]

    valuations: list[PositionValuation] = []
    missing_marks: list[tuple[str, str]] = []
    unrealized_pnl = Decimal(0)
    market_value = Decimal(0)

    for (symbol, exchange), (quantity, cost_basis) in sorted(positions.items()):
        raw_mark = normalized_marks.get((symbol, exchange))
        if raw_mark is None:
            missing_marks.append((symbol, exchange))
            valuations.append(
                PositionValuation(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=quantity,
                    average_cost=cost_basis / quantity,
                    mark_price=None,
                    market_value=None,
                    unrealized_pnl=None,
                )
            )
            continue

        mark = _money(raw_mark, "Mark price")
        if mark <= 0:
            raise PortfolioError("Mark prices must be positive.")
        value = mark * quantity
        position_pnl = value - cost_basis
        market_value += value
        unrealized_pnl += position_pnl
        valuations.append(
            PositionValuation(
                symbol=symbol,
                exchange=exchange,
                quantity=quantity,
                average_cost=cost_basis / quantity,
                mark_price=mark,
                market_value=value,
                unrealized_pnl=position_pnl,
            )
        )

    complete_valuation = not missing_marks
    return PortfolioSnapshot(
        cash=cash,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl if complete_valuation else None,
        net_liquidation=cash + market_value if complete_valuation else None,
        total_fees=total_fees,
        positions=tuple(valuations),
        missing_marks=tuple(missing_marks),
    )
