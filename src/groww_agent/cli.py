from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Sequence

from .config import AppConfig, ConfigurationError
from .market_data import MarketDataError, load_daily_bars
from .storage import SQLiteStore, StorageError
from .strategy import build_technical_watchlist


_FOUNDATION_ONLY = (
    "Foundation initialized in PAPER mode. Entry processing is disabled; "
    "the CLI only validates data and produces technical watchlists."
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="groww-agent",
        description="Local paper-trading tools; no order execution is implemented.",
    )
    parser.add_argument(
        "command",
        choices=("start", "init", "status", "config-check", "validate-data", "scan"),
        help="initialize/inspect paper state, validate local data, or build a technical watchlist",
    )
    parser.add_argument("--bars-file", type=Path, help="Local completed daily OHLCV CSV")
    parser.add_argument("--benchmark", default="NIFTY 50", help="Benchmark symbol in the CSV")
    return parser


def _load_store(config: AppConfig) -> SQLiteStore:
    return SQLiteStore(config.database_path)


def _run(
    command: str,
    config: AppConfig,
    *,
    bars_file: Path | None = None,
    benchmark: str = "NIFTY 50",
) -> int:
    if command in {"validate-data", "scan"}:
        if bars_file is None:
            print(f"{command} requires --bars-file.", file=sys.stderr)
            return 2
        bars = load_daily_bars(bars_file)
        if command == "validate-data":
            symbols = {(bar.symbol, bar.exchange) for bar in bars}
            print(f"Validated daily bars: {len(bars)}")
            print(f"Exchange-qualified symbols: {len(symbols)}")
            print(f"Latest session date: {max(bar.session_date for bar in bars).isoformat()}")
            return 0

        candidates = build_technical_watchlist(bars, benchmark_symbol=benchmark)
        print(
            "TECHNICAL WATCHLIST ONLY - no entries or paper orders are created. "
            "Market/news/event evidence, data-source permissions, and source freshness "
            "are not validated. The 2% protective-stop reference uses the latest CSV "
            "close, not an actual fill; the 2% net-profit target needs a cost model."
        )
        if not candidates:
            print("No technical candidates passed; this may also indicate insufficient data.")
            return 0
        print("Rank  Symbol              Date        Close      Indicative stop   Trend/ATR   RelVol")
        for rank, candidate in enumerate(candidates, start=1):
            print(
                f"{rank:>4}  {candidate.symbol:<8} {candidate.exchange:<3} "
                f"{candidate.session_date} {candidate.close:>10.2f} "
                f"{candidate.indicative_stop:>16.2f} "
                f"{candidate.trend_strength_atr:>11.3f} "
                f"{candidate.relative_volume:>7.2f}"
            )
        return 0

    store = _load_store(config)
    if command == "config-check":
        print(
            "Configuration valid: PAPER mode; "
            f"default capital INR {config.default_capital:.0f}; "
            f"ceiling INR {config.capital_ceiling:.0f}."
        )
        return 0

    if command == "status":
        if not config.database_path.is_file():
            print("Local state is not initialized.", file=sys.stderr)
            return 2
        store.initialize()
        print(f"Mode: PAPER\nDatabase: {config.database_path}")
        runtime = store.runtime_status()
        print(f"Entry state: {runtime['entry_state']}")
        print(f"Recovery generation: {runtime['startup_generation']}")
        print(f"Recovery required: {runtime['reason']}")
        for table, count in store.count_records().items():
            print(f"{table}: {count}")
        print("Entry processing: disabled")
        return 0

    store.initialize()
    if command == "start":
        store.begin_startup()
        print(_FOUNDATION_ONLY)
        print("Recovery state: REQUIRED; entry processing remains disabled.")
    else:
        print(f"Paper state store initialized: {config.database_path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = AppConfig.from_env()
        return _run(
            args.command,
            config,
            bars_file=args.bars_file,
            benchmark=args.benchmark,
        )
    except ConfigurationError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    except MarketDataError as error:
        print(f"Market-data error: {error}", file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error, StorageError) as error:
        print(f"Startup error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
