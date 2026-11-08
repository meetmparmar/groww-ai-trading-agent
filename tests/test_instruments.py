import unittest
from datetime import datetime, timedelta, timezone

from groww_agent.instruments import (
    DEFAULT_EQUITY_UNIVERSE,
    DEFAULT_MARKET_UNIVERSE,
    BudgetLimit,
    ComponentInterface,
    DataSourceSpec,
    EvaluationCriteria,
    ImplementationReadinessChecklist,
    Instrument,
    InstrumentCategory,
    MarketUniverse,
    RecoveryTarget,
    SessionApproval,
    SessionRiskProfile,
    SimulationParameters,
    StateSecuritySpec,
    SUPPORTED_STOCK_EXCHANGES,
    TradingStyle,
)


class TestInstrumentUniverse(unittest.TestCase):
    def test_default_universe_covers_nse_and_bse_without_a_fixed_seed_list(self):
        self.assertEqual(DEFAULT_MARKET_UNIVERSE.instruments, ())
        self.assertEqual(DEFAULT_MARKET_UNIVERSE.exchanges, ("NSE", "BSE"))
        self.assertEqual(DEFAULT_MARKET_UNIVERSE.market, "NSE+BSE")
        self.assertEqual(DEFAULT_MARKET_UNIVERSE.country, "IN")
        self.assertEqual(SUPPORTED_STOCK_EXCHANGES, ("NSE", "BSE"))
        self.assertIs(DEFAULT_EQUITY_UNIVERSE, DEFAULT_MARKET_UNIVERSE)

    def test_instrument_supports_swing_only_and_exclusions(self):
        instrument = Instrument("RELIANCE", "Reliance Industries", exchange="NSE")
        self.assertTrue(instrument.supports_style(TradingStyle.SWING))
        self.assertTrue(instrument.supports_style("swing"))
        with self.assertRaisesRegex(ValueError, "intraday"):
            instrument.supports_style("intraday")

        universe = MarketUniverse(
            name="test-universe",
            market="NSE+BSE",
            country="IN",
            instruments=(instrument,),
        )
        self.assertTrue(universe.supports_style("RELIANCE", "swing", exchange="NSE"))
        self.assertTrue(DEFAULT_MARKET_UNIVERSE.is_excluded("OPTIONS"))
        self.assertTrue(DEFAULT_MARKET_UNIVERSE.is_excluded("FUTURES"))
        self.assertFalse(DEFAULT_MARKET_UNIVERSE.is_excluded("ETF"))
        self.assertIn("INDEX", DEFAULT_MARKET_UNIVERSE.excluded_asset_classes)

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

    def test_universe_accepts_etfs_and_rejects_unknown_exchange_listings(self):
        etf = Instrument(
            "TESTETF",
            "Test Equity ETF",
            exchange="BSE",
            category=InstrumentCategory.ETF,
        )
        universe = MarketUniverse(
            name="test-universe",
            market="NSE+BSE",
            country="IN",
            instruments=(etf,),
        )
        self.assertIs(universe.get_instrument("TESTETF"), etf)
        with self.assertRaisesRegex(ValueError, "not an allowed exchange"):
            MarketUniverse(
                name="test-universe",
                market="NSE+BSE",
                country="IN",
                instruments=(Instrument("TEST", "Test Ltd", exchange="OTHER"),),
            )

    def test_session_loss_profile_tracks_daily_breaker_and_sticky_lock(self):
        session = SessionRiskProfile(
            approved_capital=50_000.0,
            session_baseline_net_liquidation=50_000.0,
            current_net_liquidation=49_000.0,
        )

        self.assertEqual(session.daily_loss_threshold, 750.0)
        self.assertAlmostEqual(session.session_net_pnl(), -1000.0)
        self.assertTrue(session.apply_breaker_if_needed())
        self.assertTrue(session.entry_lock_active)

        session.current_net_liquidation = 49_500.0
        self.assertTrue(session.apply_breaker_if_needed())
        self.assertTrue(session.entry_lock_active)

        session.reset_entry_lock()
        self.assertFalse(session.entry_lock_active)

    def test_session_approval_validates_expiry_and_reapproval(self):
        approved_at = datetime.now(timezone.utc)
        approval = SessionApproval(
            session_id="session-001",
            batch_id="batch-001",
            approved_capital=50_000.0,
            approved_at=approved_at,
            expires_at=approved_at + timedelta(minutes=30),
            valid_symbols=("RELIANCE", "TCS"),
        )

        self.assertTrue(approval.is_valid())
        self.assertTrue(approval.can_authorize_symbol("RELIANCE"))
        self.assertTrue(approval.can_authorize_capital(15_000.0))
        self.assertFalse(approval.can_authorize_symbol("INFY"))
        self.assertTrue(approval.requires_reapproval(symbol="INFY"))
        self.assertTrue(approval.requires_reapproval(proposed_capital=60_000.0))

        expired = SessionApproval(
            session_id="session-002",
            batch_id="batch-002",
            approved_capital=10_000.0,
            approved_at=approved_at,
            expires_at=approved_at + timedelta(minutes=5),
        )
        self.assertFalse(expired.is_valid(now=approved_at + timedelta(minutes=10)))
        self.assertFalse(expired.can_authorize_capital(10_000.0, now=approved_at + timedelta(minutes=10)))

    def test_recovery_budget_and_evaluation_models_are_guarded(self):
        recovery = RecoveryTarget(rto_minutes=15, rpo_minutes=5, stale_data_minutes=15)
        self.assertTrue(recovery.is_recovery_within_target(10))
        self.assertTrue(recovery.is_stale(16))

        budget = BudgetLimit(monthly_cap=4_000.0, ai_usage_cap=500.0, aws_cap=1_500.0)
        self.assertTrue(budget.is_allowed(3_900.0))
        self.assertEqual(budget.remaining_budget(3_900.0), 100.0)

        evaluation = EvaluationCriteria(min_sessions=30, target_net_return_pct=0.10, max_drawdown_pct=0.15)
        self.assertTrue(
            evaluation.passes(
                sessions_completed=30,
                net_return_pct=0.12,
                max_drawdown_pct=0.10,
                critical_defects=0,
            )
        )
        self.assertFalse(
            evaluation.passes(
                sessions_completed=29,
                net_return_pct=0.12,
                max_drawdown_pct=0.10,
                critical_defects=0,
            )
        )

        source = DataSourceSpec(
            source_name="NSE India",
            purpose="cash-equity and ETF reference data",
            is_verified=True,
            freshness_minutes=15,
        )
        self.assertTrue(source.is_acceptable(10))

        sim = SimulationParameters(slippage_bps=5.0, market_impact_bps=2.0, fee_bps=1.0, max_gap_pct=0.5)
        self.assertAlmostEqual(sim.total_cost_bps(), 8.0)
        self.assertTrue(sim.allows_gap(0.4))
        self.assertFalse(sim.allows_gap(0.6))

    def test_interface_security_and_readiness_models_are_defined(self):
        interface = ComponentInterface(
            name="telegram-approval",
            inputs=("session", "approval", "symbol"),
            outputs=("decision", "status"),
            failure_modes=("timeout", "replay", "identity_mismatch"),
        )
        self.assertTrue(interface.is_compatible("session"))
        self.assertFalse(interface.is_compatible("trade"))

        security = StateSecuritySpec()
        self.assertTrue(security.requires_audit("approval"))
        self.assertIn("audit", security.backup_boundaries)

        readiness = ImplementationReadinessChecklist(
            strategy_accepted=True,
            limits_accepted=True,
            loss_rules_accepted=True,
            data_sources_verified=True,
            simulation_assumptions_defined=True,
        )
        self.assertTrue(readiness.is_ready())


if __name__ == "__main__":
    unittest.main()
