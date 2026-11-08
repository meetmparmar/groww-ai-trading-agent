import unittest

from groww_agent.instruments import (
    DEFAULT_EQUITY_UNIVERSE,
    Instrument,
    InstrumentCategory,
    MarketUniverse,
    SUPPORTED_STOCK_EXCHANGES,
    TradingStyle,
)


class TestInstrumentUniverse(unittest.TestCase):
    def test_default_universe_covers_nse_and_bse_without_a_fixed_seed_list(self):
        self.assertEqual(DEFAULT_EQUITY_UNIVERSE.instruments, ())
        self.assertEqual(DEFAULT_EQUITY_UNIVERSE.exchanges, ("NSE", "BSE"))
        self.assertEqual(DEFAULT_EQUITY_UNIVERSE.market, "NSE+BSE")
        self.assertEqual(DEFAULT_EQUITY_UNIVERSE.country, "IN")
        self.assertEqual(SUPPORTED_STOCK_EXCHANGES, ("NSE", "BSE"))

    def test_instrument_supports_both_styles_and_exclusions(self):
        instrument = Instrument("RELIANCE", "Reliance Industries", exchange="NSE")
        self.assertTrue(instrument.supports_style(TradingStyle.INTRADAY))
        self.assertTrue(instrument.supports_style(TradingStyle.SWING))
        universe = MarketUniverse(
            name="test-universe",
            market="NSE+BSE",
            country="IN",
            instruments=(instrument,),
        )
        self.assertTrue(universe.supports_style("RELIANCE", "swing", exchange="NSE"))
        self.assertTrue(DEFAULT_EQUITY_UNIVERSE.is_excluded("OPTIONS"))
        self.assertTrue(DEFAULT_EQUITY_UNIVERSE.is_excluded("FUTURES"))
        self.assertTrue(DEFAULT_EQUITY_UNIVERSE.is_excluded("ETF"))
        self.assertIn("INDEX", DEFAULT_EQUITY_UNIVERSE.excluded_asset_classes)

    def test_same_symbol_can_be_listed_on_both_exchanges(self):
        nse = Instrument("ABC", "ABC Ltd", exchange="NSE")
        bse = Instrument("ABC", "ABC Ltd", exchange="BSE")
        universe = MarketUniverse(
            name="test-universe",
            market="NSE+BSE",
            country="IN",
            instruments=(nse, bse),
        )

        with self.assertRaisesRegex(ValueError, "specify the exchange"):
            universe.get_instrument("ABC")

        self.assertIs(universe.get_instrument("ABC", "NSE"), nse)
        self.assertIs(universe.get_instrument("ABC", "BSE"), bse)

    def test_universe_rejects_non_equity_and_unknown_exchange_listings(self):
        with self.assertRaisesRegex(ValueError, "Only cash-equity"):
            MarketUniverse(
                name="test-universe",
                market="NSE+BSE",
                country="IN",
                instruments=(
                    Instrument("TESTETF", "Test ETF", category=InstrumentCategory.ETF),
                ),
            )

        with self.assertRaisesRegex(ValueError, "not an allowed exchange"):
            MarketUniverse(
                name="test-universe",
                market="NSE+BSE",
                country="IN",
                instruments=(Instrument("TEST", "Test Ltd", exchange="OTHER"),),
            )


if __name__ == "__main__":
    unittest.main()
