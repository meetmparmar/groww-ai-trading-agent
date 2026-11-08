import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from groww_agent.cli import main
from groww_agent.market_data import MarketDataError, load_daily_bars


class TestLocalDailyData(unittest.TestCase):
    def test_loads_and_normalizes_completed_daily_bars(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bars.csv"
            path.write_text(
                "date,symbol,exchange,open,high,low,close,volume\n"
                "2026-11-06,abc,nse,10,12,9,11,1000\n",
                encoding="utf-8",
            )

            bars = load_daily_bars(path)

        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].symbol, "ABC")
        self.assertEqual(bars[0].exchange, "NSE")
        self.assertEqual(str(bars[0].close), "11")

    def test_rejects_missing_columns_duplicate_bars_and_inconsistent_ohlc(self):
        cases = (
            (
                "date,symbol,exchange,open,high,low,close\n"
                "2026-11-06,ABC,NSE,10,12,9,11\n",
                "missing columns",
            ),
            (
                "date,symbol,exchange,open,high,low,close,volume\n"
                "2026-11-06,ABC,NSE,10,12,9,11,1000\n"
                "2026-11-06,ABC,NSE,10,12,9,11,1000\n",
                "duplicate bar",
            ),
            (
                "date,symbol,exchange,open,high,low,close,volume\n"
                "2026-11-06,ABC,NSE,10,9,8,11,1000\n",
                "high is below",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bars.csv"
            for content, message in cases:
                with self.subTest(message=message):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaisesRegex(MarketDataError, message):
                        load_daily_bars(path)

    def test_rejects_an_empty_data_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bars.csv"
            path.write_text(
                "date,symbol,exchange,open,high,low,close,volume\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(MarketDataError, "no daily bars"):
                load_daily_bars(path)

    def test_scan_is_watchlist_only_and_does_not_initialize_trading_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bars.csv"
            database = Path(directory) / "paper.sqlite3"
            path.write_text(
                "date,symbol,exchange,open,high,low,close,volume\n"
                "2026-11-06,ABC,NSE,10,12,9,11,1000\n"
                "2026-11-06,NIFTY 50,NSE,100,102,99,101,1000\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with patch.dict(
                os.environ,
                {"APP_MODE": "paper", "GROWW_AGENT_DATABASE": str(database)},
                clear=True,
            ):
                with contextlib.redirect_stdout(output):
                    result = main(["scan", "--bars-file", str(path)])

            self.assertEqual(result, 0)
            self.assertIn("TECHNICAL WATCHLIST ONLY", output.getvalue())
            self.assertFalse(database.exists())


if __name__ == "__main__":
    unittest.main()
