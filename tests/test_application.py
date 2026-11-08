import contextlib
import io
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from groww_agent.cli import main
from groww_agent.config import AppConfig, ConfigurationError
from groww_agent.storage import IdempotencyConflict, SQLiteStore, StorageError


class TestApplicationConfig(unittest.TestCase):
    def test_paper_only_config_loads_approved_capital_defaults(self):
        config = AppConfig.from_env({})

        self.assertEqual(config.mode, "paper")
        self.assertEqual(config.default_capital, 50_000.0)
        self.assertEqual(config.capital_ceiling, 100_000.0)
        self.assertEqual(config.per_position_risk_rate, 0.005)
        self.assertEqual(config.daily_loss_lock_rate, 0.015)
        self.assertTrue(config.database_path.is_absolute())

    def test_non_paper_and_invalid_risk_or_capital_configuration_is_rejected(self):
        for values in (
            {"APP_MODE": "live"},
            {"PAPER_DEFAULT_CAPITAL": "101000"},
            {"PAPER_CAPITAL_CEILING": "100001"},
            {"PAPER_POSITION_RISK_RATE": "nan"},
            {"PAPER_POSITION_RISK_RATE": "0.006"},
            {"PAPER_DAILY_LOSS_RATE": "0"},
        ):
            with self.subTest(values=values):
                with self.assertRaises(ConfigurationError):
                    AppConfig.from_env(values)

    def test_start_creates_paper_store_but_keeps_entries_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.sqlite3"
            output = io.StringIO()
            with patch.dict(
                os.environ,
                {"GROWW_AGENT_DATABASE": str(database), "APP_MODE": "paper"},
                clear=True,
            ):
                with contextlib.redirect_stdout(output):
                    result = main(["start"])

            self.assertEqual(result, 0)
            self.assertTrue(database.is_file())
            self.assertIn("PAPER mode", output.getvalue())
            self.assertIn("Entry processing is disabled", output.getvalue())
            self.assertEqual(SQLiteStore(database).count_records()["audit_events"], 1)

    def test_live_mode_fails_without_initializing_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.sqlite3"
            error_output = io.StringIO()
            with patch.dict(
                os.environ,
                {"GROWW_AGENT_DATABASE": str(database), "APP_MODE": "live"},
                clear=True,
            ):
                with contextlib.redirect_stderr(error_output):
                    result = main(["start"])

            self.assertEqual(result, 2)
            self.assertFalse(database.exists())
            self.assertIn("Only APP_MODE=paper", error_output.getvalue())


class TestSQLiteStore(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_directory.name) / "state.sqlite3"
        self.store = SQLiteStore(self.database)
        self.store.initialize()

    def tearDown(self):
        self.temp_directory.cleanup()

    def _create_approved_intent(self):
        self.store.create_session(
            session_id="session-1",
            exchange_date="2026-11-09",
            approved_capital=50_000.0,
            state="AWAITING_APPROVAL",
        )
        self.store.create_approval(
            approval_id="approval-1",
            session_id="session-1",
            proposal_digest="sha256:example",
            approved_by="owner",
            approved_at=datetime.now(timezone.utc).isoformat(),
            expires_at="2026-11-09T04:00:00+00:00",
        )
        self.store.create_signal(
            signal_id="signal-1",
            session_id="session-1",
            symbol="RELIANCE",
            exchange="NSE",
            strategy_version="swing-v1",
            decision="ENTRY_CANDIDATE",
            reason="Candidate from validated fixture data.",
            input_digest="sha256:inputs",
        )
        return {
            "intent_id": "intent-1",
            "idempotency_key": "entry-session1-reliance-nse",
            "session_id": "session-1",
            "approval_id": "approval-1",
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "side": "BUY",
            "quantity": 2,
            "strategy_version": "swing-v1",
        }

    def test_session_approval_intent_order_fill_and_position_persist(self):
        intent = self._create_approved_intent()
        self.assertTrue(self.store.create_order_intent(**intent))
        self.store.create_paper_order(
            order_id="order-1",
            intent_id="intent-1",
            requested_quantity=2,
            status="SUBMITTED",
        )
        self.assertTrue(
            self.store.record_fill(
                fill_id="fill-1",
                event_key="simulator-event-1",
                order_id="order-1",
                quantity=2,
                price=100.0,
                fees=1.0,
                filled_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        self.store.upsert_position(
            position_id="position-1",
            session_id="session-1",
            symbol="RELIANCE",
            exchange="NSE",
            quantity=2,
            average_price=100.0,
        )

        restarted_store = SQLiteStore(self.database)
        self.assertEqual(
            restarted_store.count_records(),
            {
                "sessions": 1,
                "approvals": 1,
                "signals": 1,
                "order_intents": 1,
                "paper_orders": 1,
                "fills": 1,
                "positions": 1,
                "audit_events": 0,
                "runtime_control": 1,
            },
        )

        connection = sqlite3.connect(self.database)
        try:
            order_status = connection.execute(
                "SELECT status FROM paper_orders WHERE order_id = 'order-1'"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(order_status, "FILLED")

    def test_startup_persists_recovery_required_and_never_enables_entries(self):
        first_generation = self.store.begin_startup()
        self.assertEqual(first_generation, 1)
        first_status = self.store.runtime_status()
        self.assertEqual(first_status["entry_state"], "RECOVERY_REQUIRED")

        restarted_store = SQLiteStore(self.database)
        restarted_store.initialize()
        second_generation = restarted_store.begin_startup()
        second_status = restarted_store.runtime_status()

        self.assertEqual(second_generation, 2)
        self.assertEqual(second_status["entry_state"], "RECOVERY_REQUIRED")
        self.assertEqual(second_status["startup_generation"], 2)
        self.assertEqual(
            restarted_store.count_records()["audit_events"],
            2,
        )

    def test_portfolio_snapshot_accounts_for_fees_realized_and_unrealized_pnl(self):
        buy_intent = self._create_approved_intent()
        self.store.create_order_intent(**buy_intent)
        self.store.create_paper_order(
            order_id="buy-order",
            intent_id="intent-1",
            requested_quantity=2,
            status="SUBMITTED",
        )
        self.store.record_fill(
            fill_id="buy-fill",
            event_key="buy-event",
            order_id="buy-order",
            quantity=2,
            price=100.0,
            fees=1.0,
            filled_at="2026-11-09T05:00:00+00:00",
        )

        self.store.create_order_intent(
            intent_id="sell-intent",
            idempotency_key="exit-session1-reliance-nse",
            session_id="session-1",
            approval_id="approval-1",
            symbol="RELIANCE",
            exchange="NSE",
            side="SELL",
            quantity=1,
            strategy_version="swing-v1",
        )
        self.store.create_paper_order(
            order_id="sell-order",
            intent_id="sell-intent",
            requested_quantity=1,
            status="SUBMITTED",
        )
        self.store.record_fill(
            fill_id="sell-fill",
            event_key="sell-event",
            order_id="sell-order",
            quantity=1,
            price=120.0,
            fees=1.0,
            filled_at="2026-11-09T06:00:00+00:00",
        )

        snapshot = self.store.portfolio_snapshot(
            session_id="session-1",
            marks={("RELIANCE", "NSE"): 130.0},
        )

        self.assertEqual(snapshot.cash, 49_918)
        self.assertEqual(snapshot.realized_pnl, 18.5)
        self.assertEqual(snapshot.unrealized_pnl, 29.5)
        self.assertEqual(snapshot.net_liquidation, 50_048)
        self.assertEqual(snapshot.total_fees, 2)
        self.assertEqual(snapshot.positions[0].quantity, 1)

    def test_portfolio_snapshot_blocks_valuation_when_a_mark_is_missing(self):
        intent = self._create_approved_intent()
        self.store.create_order_intent(**intent)
        self.store.create_paper_order(
            order_id="order-1",
            intent_id="intent-1",
            requested_quantity=1,
            status="SUBMITTED",
        )
        self.store.record_fill(
            fill_id="fill-1",
            event_key="event-1",
            order_id="order-1",
            quantity=1,
            price=100.0,
            fees=0.0,
            filled_at="2026-11-09T05:00:00+00:00",
        )

        snapshot = self.store.portfolio_snapshot(session_id="session-1", marks={})

        self.assertIsNone(snapshot.net_liquidation)
        self.assertIsNone(snapshot.unrealized_pnl)
        self.assertEqual(snapshot.missing_marks, (("RELIANCE", "NSE"),))

    def test_schema_one_database_migrates_to_fail_closed_runtime_control(self):
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TABLE runtime_control")
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
        finally:
            connection.close()

        migrated_store = SQLiteStore(self.database)
        migrated_store.initialize()

        self.assertEqual(
            migrated_store.runtime_status()["entry_state"],
            "RECOVERY_REQUIRED",
        )

    def test_paper_order_rejects_invalid_transitions_and_overfills(self):
        intent = self._create_approved_intent()
        self.store.create_order_intent(**intent)
        self.store.create_paper_order(
            order_id="order-1",
            intent_id="intent-1",
            requested_quantity=1,
        )
        with self.assertRaisesRegex(StorageError, "Invalid paper-order transition"):
            self.store.transition_paper_order(order_id="order-1", new_status="FILLED")

        self.store.transition_paper_order(order_id="order-1", new_status="SUBMITTED")
        self.store.record_fill(
            fill_id="fill-1",
            event_key="event-1",
            order_id="order-1",
            quantity=1,
            price=100.0,
            fees=0.0,
            filled_at=datetime.now(timezone.utc).isoformat(),
        )
        with self.assertRaisesRegex(StorageError, "Cannot record a fill"):
            self.store.record_fill(
                fill_id="fill-2",
                event_key="event-2",
                order_id="order-1",
                quantity=1,
                price=100.0,
                fees=0.0,
                filled_at=datetime.now(timezone.utc).isoformat(),
            )

    def test_duplicate_intent_is_idempotent_but_changed_payload_conflicts(self):
        intent = self._create_approved_intent()
        self.assertTrue(self.store.create_order_intent(**intent))
        self.assertFalse(self.store.create_order_intent(**intent))

        changed_intent = dict(intent, quantity=3)
        with self.assertRaises(IdempotencyConflict):
            self.store.create_order_intent(**changed_intent)

    def test_expired_or_mismatched_approval_cannot_back_an_order_intent(self):
        intent = self._create_approved_intent()
        self.store.create_approval(
            approval_id="expired-approval",
            session_id="session-1",
            proposal_digest="sha256:expired",
            approved_by="owner",
            approved_at="2026-11-07T00:00:00+00:00",
            expires_at="2026-11-07T01:00:00+00:00",
        )
        with self.assertRaisesRegex(StorageError, "approval has expired"):
            self.store.create_order_intent(
                **dict(intent, approval_id="expired-approval")
            )
        with self.assertRaisesRegex(StorageError, "no approval for its session"):
            self.store.create_order_intent(
                **dict(intent, session_id="different-session")
            )

    def test_audit_entries_redact_common_secret_assignments(self):
        self.store.record_audit(
            actor="system",
            action="startup",
            reason="GROWW_API_KEY=abc123 TELEGRAM_BOT_TOKEN=topsecret",
        )
        connection = sqlite3.connect(self.database)
        try:
            reason = connection.execute(
                "SELECT reason FROM audit_events"
            ).fetchone()[0]
        finally:
            connection.close()

        self.assertNotIn("abc123", reason)
        self.assertNotIn("topsecret", reason)
        self.assertIn("[REDACTED]", reason)

    def test_audit_events_are_append_only(self):
        self.store.record_audit(actor="system", action="startup", reason="Started safely.")
        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute("UPDATE audit_events SET reason = 'changed'")
            connection.rollback()
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute("DELETE FROM audit_events")
        finally:
            connection.close()

    def test_foreign_keys_and_invalid_values_fail_closed(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.create_approval(
                approval_id="orphan",
                session_id="missing",
                proposal_digest="digest",
                approved_by="owner",
                approved_at="2026-11-09T00:00:00+00:00",
                expires_at="2026-11-09T01:00:00+00:00",
            )
        with self.assertRaises(ValueError):
            self.store.create_session(
                session_id="bad",
                exchange_date="2026-11-09",
                approved_capital=float("inf"),
            )


if __name__ == "__main__":
    unittest.main()
