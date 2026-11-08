from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from .market_data import DailyBar


_BENCHMARK_SYMBOL = "NIFTY 50"
_PROTECTIVE_STOP_RATE = 0.02


@dataclass(frozen=True, slots=True)
class TechnicalCandidate:
    symbol: str
    exchange: str
    session_date: str
    close: float
    indicative_stop: float
    trend_strength_atr: float
    relative_volume: float


def _ema(values: list[float], period: int) -> list[float | None]:
    if len(values) < period:
        return [None] * len(values)
    result: list[float | None] = [None] * (period - 1)
    current = sum(values[:period]) / period
    result.append(current)
    alpha = 2.0 / (period + 1)
    for value in values[period:]:
        current = alpha * value + (1 - alpha) * current
        result.append(current)
    return result


def _true_ranges(bars: list[DailyBar]) -> list[float]:
    ranges: list[float] = []
    previous_close: float | None = None
    for bar in bars:
        high = float(bar.high)
        low = float(bar.low)
        close = float(bar.close)
        ranges.append(
            max(high - low, abs(high - previous_close), abs(low - previous_close))
            if previous_close is not None
            else high - low
        )
        previous_close = close
    return ranges


def _atr(bars: list[DailyBar], period: int = 14) -> float | None:
    ranges = _true_ranges(bars)
    if len(ranges) < period:
        return None
    current = sum(ranges[:period]) / period
    for value in ranges[period:]:
        current = ((period - 1) * current + value) / period
    return current


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [right - left for left, right in zip(values, values[1:])]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = ((period - 1) * average_gain + gain) / period
        average_loss = ((period - 1) * average_loss + loss) / period
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return 100.0 - 100.0 / (1.0 + relative_strength)


def build_technical_watchlist(
    bars: Iterable[DailyBar],
    *,
    benchmark_symbol: str = _BENCHMARK_SYMBOL,
) -> tuple[TechnicalCandidate, ...]:
    """Rank technical-only candidates; this does not authorize or simulate entries."""
    grouped: dict[tuple[str, str], list[DailyBar]] = {}
    for bar in bars:
        grouped.setdefault((bar.symbol.upper(), bar.exchange.upper()), []).append(bar)
    for history in grouped.values():
        history.sort(key=lambda bar: bar.session_date)

    benchmarks = [
        history
        for (symbol, _), history in grouped.items()
        if symbol == benchmark_symbol.upper()
    ]
    if not benchmarks:
        return ()
    benchmark = max(benchmarks, key=len)
    benchmark_closes = [float(bar.close) for bar in benchmark]
    benchmark_ema20 = _ema(benchmark_closes, 20)
    if len(benchmark) < 20 or benchmark_ema20[-1] is None:
        return ()
    benchmark_is_up = benchmark_closes[-1] > benchmark_ema20[-1]
    benchmark_date = benchmark[-1].session_date
    if not benchmark_is_up:
        return ()

    candidates: list[TechnicalCandidate] = []
    for (symbol, exchange), history in grouped.items():
        if symbol == benchmark_symbol.upper() or len(history) < 51:
            continue
        if history[-1].session_date != benchmark_date:
            continue

        closes = [float(bar.close) for bar in history]
        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, 50)
        atr14 = _atr(history)
        rsi14 = _rsi(closes)
        latest = history[-1]
        previous = history[-2]
        if atr14 is None or atr14 <= 0 or rsi14 is None:
            continue
        if ema20[-1] is None or ema50[-1] is None:
            continue
        if not (closes[-1] > ema20[-1] > ema50[-1]):
            continue
        if not 50 <= rsi14 <= 70:
            continue
        if closes[-1] <= float(previous.high):
            continue
        recent_volume = [bar.volume for bar in history[-21:-1]]
        if len(recent_volume) != 20 or median(recent_volume) <= 0:
            continue
        relative_volume = latest.volume / median(recent_volume)
        if relative_volume < 1.2:
            continue
        pullback_indexes = range(len(history) - 4, len(history) - 1)
        if not any(
            ema20[index] is not None
            and ema50[index] is not None
            and float(history[index].low) <= ema20[index]
            and float(history[index].close) >= ema50[index]
            for index in pullback_indexes
        ):
            continue

        candidates.append(
            TechnicalCandidate(
                symbol=symbol,
                exchange=exchange,
                session_date=latest.session_date.isoformat(),
                close=closes[-1],
                indicative_stop=closes[-1] * (1 - _PROTECTIVE_STOP_RATE),
                trend_strength_atr=(ema20[-1] - ema50[-1]) / atr14,
                relative_volume=relative_volume,
            )
        )

    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                -candidate.trend_strength_atr,
                -candidate.relative_volume,
                candidate.exchange,
                candidate.symbol,
            ),
        )
    )
