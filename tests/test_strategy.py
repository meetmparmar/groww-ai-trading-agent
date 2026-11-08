import unittest
from datetime import date, timedelta
from decimal import Decimal

from groww_agent.market_data import DailyBar
from groww_agent.strategy import build_technical_watchlist


def _bar(symbol, session_date, close, *, volume=1000, range_size=0.5):
    value = Decimal(str(close))
    spread = Decimal(str(range_size))
    return DailyBar(
        symbol=symbol,
        exchange="NSE",
        session_date=session_date,
        open=value - spread / 4,
        high=value + spread / 4,
        low=value - spread,
        close=value,
        volume=volume,
    )


class TestTechnicalWatchlist(unittest.TestCase):
    def test_ranks_candidate_only_when_daily_bar_rules_and_benchmark_pass(self):
        start = date(2026, 8, 1)
        stock = [_bar("ABC", start, 100)]
        for index in range(1, 54):
            change = -0.22 if index % 3 == 0 else 0.15
            if index == 53:
                change = -0.5
            stock.append(
                _bar("ABC", start + timedelta(days=index), float(stock[-1].close) + change)
            )
        stock.append(
            _bar(
                "ABC",
                start + timedelta(days=54),
                float(stock[-1].close) + 0.7,
                volume=1500,
            )
        )

        benchmark = [
            _bar("NIFTY 50", start + timedelta(days=index), 100 + index * 0.1)
            for index in range(55)
        ]

        candidates = build_technical_watchlist(stock + benchmark)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].symbol, "ABC")
        self.assertEqual(candidates[0].exchange, "NSE")
        self.assertGreater(candidates[0].close, candidates[0].indicative_stop)

    def test_returns_no_candidates_without_benchmark_or_synchronized_session(self):
        start = date(2026, 8, 1)
        stock = [
            _bar("ABC", start + timedelta(days=index), 100 + index * 0.2)
            for index in range(55)
        ]

        self.assertEqual(build_technical_watchlist(stock), ())

        benchmark = [
            _bar("NIFTY 50", start + timedelta(days=index), 100 + index * 0.1)
            for index in range(54)
        ]
        self.assertEqual(build_technical_watchlist(stock + benchmark), ())


if __name__ == "__main__":
    unittest.main()
