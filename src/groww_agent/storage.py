from __future__ import annotations

import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator

from .portfolio import PortfolioSnapshot, TradeFill, build_portfolio_snapshot


class StorageError(RuntimeError):
    """Base error for local durable-state failures."""


class IdempotencyConflict(StorageError):
    """Raised when an existing idempotency key is reused for different content."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    exchange_date TEXT NOT NULL,
    approved_capital REAL NOT NULL CHECK (approved_capital > 0),
    state TEXT NOT NULL CHECK (
        state IN ('PREPARING', 'AWAITING_APPROVAL', 'ACTIVE', 'ENTRIES_LOCKED', 'CLOSED')
    ),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    proposal_digest TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('APPROVED', 'REJECTED', 'EXPIRED', 'INVALIDATED')),
    UNIQUE (session_id, proposal_digest),
    UNIQUE (approval_id, session_id)
);

CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL CHECK (exchange IN ('NSE', 'BSE')),
    strategy_version TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ENTRY_CANDIDATE', 'NO_TRADE', 'EXIT')),
    reason TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_intents (
    intent_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    approval_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL CHECK (exchange IN ('NSE', 'BSE')),
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    strategy_version TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('APPROVED', 'SUBMITTED', 'REJECTED')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (approval_id, session_id)
        REFERENCES approvals(approval_id, session_id)
);

CREATE TABLE IF NOT EXISTS paper_orders (
    order_id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL UNIQUE REFERENCES order_intents(intent_id),
    status TEXT NOT NULL CHECK (
        status IN (
            'CREATED', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED',
            'CANCEL_PENDING', 'CANCELLED', 'REJECTED', 'UNKNOWN'
        )
    ),
    requested_quantity INTEGER NOT NULL CHECK (requested_quantity > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
    fill_id TEXT PRIMARY KEY,
    event_key TEXT NOT NULL UNIQUE,
    order_id TEXT NOT NULL REFERENCES paper_orders(order_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL CHECK (price > 0),
    fees REAL NOT NULL CHECK (fees >= 0),
    filled_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL CHECK (exchange IN ('NSE', 'BSE')),
    quantity INTEGER NOT NULL,
    average_price REAL NOT NULL CHECK (average_price >= 0),
    updated_at TEXT NOT NULL,
    UNIQUE (session_id, symbol, exchange)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT
);

CREATE TABLE IF NOT EXISTS runtime_control (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    mode TEXT NOT NULL CHECK (mode = 'PAPER'),
    entry_state TEXT NOT NULL CHECK (
        entry_state IN ('DISABLED', 'RECOVERY_REQUIRED', 'PAUSED', 'LOCKED')
    ),
    reason TEXT NOT NULL,
    startup_generation INTEGER NOT NULL CHECK (startup_generation >= 0),
    updated_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS audit_events_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END;

CREATE INDEX IF NOT EXISTS idx_orders_session ON order_intents(session_id);
CREATE INDEX IF NOT EXISTS idx_signals_session ON signals(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id);
"""

_SCHEMA_VERSION = 2
_ORDER_TRANSITIONS = {
    "CREATED": {"SUBMITTED", "REJECTED"},
    "SUBMITTED": {"PARTIALLY_FILLED", "FILLED", "CANCEL_PENDING", "REJECTED", "UNKNOWN"},
    "PARTIALLY_FILLED": {"PARTIALLY_FILLED", "FILLED", "CANCEL_PENDING", "UNKNOWN"},
    "CANCEL_PENDING": {"CANCELLED", "PARTIALLY_FILLED", "FILLED", "UNKNOWN"},
    "UNKNOWN": {"PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED"},
    "FILLED": set(),
    "CANCELLED": set(),
    "REJECTED": set(),
}

_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(?:\b|_)(password|passwd|secret(?:[_-]?(?:access[_-]?)?key)?|"
    r"token|api[_-]?key|authorization)\b"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _safe_audit_text(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    redacted = _BEARER_TOKEN.sub("Bearer [REDACTED]", value)
    return _SENSITIVE_ASSIGNMENT.sub(r"\1\2[REDACTED]", redacted)[:2000]


class SQLiteStore:
    """Small SQLite record store; it does not execute or simulate trades."""

    def __init__(self, path: Path) -> None:
        if not path.name:
            raise ValueError("Database path must name a file.")
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current_version > _SCHEMA_VERSION:
                raise StorageError(
                    f"Database schema version {current_version} is newer than supported "
                    f"version {_SCHEMA_VERSION}."
                )
            connection.executescript(_SCHEMA)
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            connection.execute(
                """
                INSERT OR IGNORE INTO runtime_control (
                    singleton, mode, entry_state, reason, startup_generation, updated_at
                ) VALUES (1, 'PAPER', 'RECOVERY_REQUIRED',
                    'Startup requires state reconciliation.', 0, ?)
                """,
                (_utc_now(),),
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def record_audit(
        self,
        *,
        actor: str,
        action: str,
        reason: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> None:
        safe_actor = _safe_audit_text(actor, "actor")
        safe_action = _safe_audit_text(action, "action")
        safe_reason = _safe_audit_text(reason, "reason")
        safe_entity_type = (
            _safe_audit_text(entity_type, "entity_type") if entity_type is not None else None
        )
        safe_entity_id = (
            _safe_audit_text(entity_id, "entity_id") if entity_id is not None else None
        )
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO audit_events (
                    occurred_at, actor, action, reason, entity_type, entity_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    _utc_now(),
                    safe_actor,
                    safe_action,
                    safe_reason,
                    safe_entity_type,
                    safe_entity_id,
                ),
            )

    def begin_startup(self) -> int:
        """Persist a new startup generation and require recovery before any entries."""
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE runtime_control
                SET entry_state = 'RECOVERY_REQUIRED',
                    reason = 'Startup requires state reconciliation.',
                    startup_generation = startup_generation + 1,
                    updated_at = ?
                WHERE singleton = 1
                """,
                (_utc_now(),),
            )
            row = connection.execute(
                "SELECT startup_generation FROM runtime_control WHERE singleton = 1"
            ).fetchone()
            if row is None:
                raise StorageError("Runtime control state is missing.")
            generation = int(row["startup_generation"])
            connection.execute(
                """
                INSERT INTO audit_events (
                    occurred_at, actor, action, reason, entity_type, entity_id
                ) VALUES (?, 'system', 'startup_recovery_required',
                    'Entry processing remains disabled pending reconciliation.',
                    'runtime_control', ?)
                """,
                (_utc_now(), str(generation)),
            )
            return generation

    def runtime_status(self) -> dict[str, str | int]:
        """Return persisted recovery state; this store never enables entries."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT mode, entry_state, reason, startup_generation, updated_at
                FROM runtime_control WHERE singleton = 1
                """
            ).fetchone()
            if row is None:
                raise StorageError("Runtime control state is missing.")
            return dict(row)

    def create_session(
        self,
        *,
        session_id: str,
        exchange_date: str,
        approved_capital: float,
        state: str = "PREPARING",
    ) -> None:
        if not session_id.strip():
            raise ValueError("Session identifier is required.")
        try:
            date.fromisoformat(exchange_date)
        except ValueError as error:
            raise ValueError("Exchange date must be an ISO-8601 date.") from error
        if not exchange_date.strip():
            raise ValueError("Session identifier and exchange date are required.")
        if (
            not _finite_number(approved_capital)
            or approved_capital <= 0
            or approved_capital > 100_000
        ):
            raise ValueError("Approved capital must be finite, positive, and within INR 100000.")
        created_at = _utc_now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT exchange_date, approved_capital, state FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if existing is not None:
                expected = (exchange_date, approved_capital, state)
                actual = (
                    existing["exchange_date"],
                    existing["approved_capital"],
                    existing["state"],
                )
                if actual != expected:
                    raise IdempotencyConflict(
                        "Session ID already exists with different session data."
                    )
                return
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id, exchange_date, approved_capital, state, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, exchange_date, approved_capital, state, created_at),
            )

    def create_approval(
        self,
        *,
        approval_id: str,
        session_id: str,
        proposal_digest: str,
        approved_by: str,
        approved_at: str,
        expires_at: str,
        state: str = "APPROVED",
    ) -> None:
        values = (
            approval_id,
            session_id,
            proposal_digest,
            approved_by,
            approved_at,
            expires_at,
            state,
        )
        if any(not value.strip() for value in values):
            raise ValueError("Approval fields cannot be empty.")
        try:
            approved_time = datetime.fromisoformat(approved_at)
            expiry_time = datetime.fromisoformat(expires_at)
        except ValueError as error:
            raise ValueError("Approval timestamps must be ISO-8601 values.") from error
        if approved_time.tzinfo is None or expiry_time.tzinfo is None:
            raise ValueError("Approval timestamps must include a timezone.")
        if expiry_time <= approved_time:
            raise ValueError("Approval expiry must be after its approval time.")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO approvals (
                    approval_id, session_id, proposal_digest, approved_by,
                    approved_at, expires_at, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )

    def create_signal(
        self,
        *,
        signal_id: str,
        session_id: str,
        symbol: str,
        exchange: str,
        strategy_version: str,
        decision: str,
        reason: str,
        input_digest: str,
    ) -> None:
        values = (
            signal_id,
            session_id,
            symbol.upper(),
            exchange,
            strategy_version,
            decision,
            _safe_audit_text(reason, "reason"),
            input_digest,
            _utc_now(),
        )
        if not all(value.strip() for value in values[:-1]):
            raise ValueError("Signal fields cannot be empty.")
        if exchange not in {"NSE", "BSE"}:
            raise ValueError("Signal exchange must be NSE or BSE.")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO signals (
                    signal_id, session_id, symbol, exchange, strategy_version,
                    decision, reason, input_digest, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )

    def create_order_intent(
        self,
        *,
        intent_id: str,
        idempotency_key: str,
        session_id: str,
        approval_id: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        strategy_version: str,
        state: str = "APPROVED",
    ) -> bool:
        if not all(
            value.strip()
            for value in (
                intent_id,
                idempotency_key,
                session_id,
                approval_id,
                symbol,
                exchange,
                strategy_version,
            )
        ):
            raise ValueError("Order intent identifiers and instrument are required.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Order quantity must be a positive integer.")
        if exchange not in {"NSE", "BSE"} or side not in {"BUY", "SELL"}:
            raise ValueError("Order intent must use a supported exchange and side.")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM order_intents WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            expected = (
                intent_id,
                session_id,
                approval_id,
                symbol.upper(),
                exchange,
                side,
                quantity,
                strategy_version,
                state,
            )
            if existing is not None:
                actual = (
                    existing["intent_id"],
                    existing["session_id"],
                    existing["approval_id"],
                    existing["symbol"],
                    existing["exchange"],
                    existing["side"],
                    existing["quantity"],
                    existing["strategy_version"],
                    existing["state"],
                )
                if actual != expected:
                    raise IdempotencyConflict(
                        "Idempotency key already exists with different intent data."
                    )
                return False
            approval = connection.execute(
                """
                SELECT state, expires_at FROM approvals
                WHERE approval_id = ? AND session_id = ?
                """,
                (approval_id, session_id),
            ).fetchone()
            if approval is None:
                raise StorageError("Order intent has no approval for its session.")
            if approval["state"] != "APPROVED":
                raise StorageError("Order intent approval is not in APPROVED state.")
            if datetime.fromisoformat(approval["expires_at"]) <= datetime.now(timezone.utc):
                raise StorageError("Order intent approval has expired.")
            connection.execute(
                """
                INSERT INTO order_intents (
                    intent_id, idempotency_key, session_id, approval_id, symbol,
                    exchange, side, quantity, strategy_version, state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intent_id,
                    idempotency_key,
                    session_id,
                    approval_id,
                    symbol.upper(),
                    exchange,
                    side,
                    quantity,
                    strategy_version,
                    state,
                    _utc_now(),
                ),
            )
        return True

    def create_paper_order(
        self,
        *,
        order_id: str,
        intent_id: str,
        requested_quantity: int,
        status: str = "CREATED",
    ) -> None:
        if not order_id.strip() or not intent_id.strip():
            raise ValueError("Order and intent identifiers are required.")
        if (
            isinstance(requested_quantity, bool)
            or not isinstance(requested_quantity, int)
            or requested_quantity <= 0
        ):
            raise ValueError("Requested quantity must be a positive integer.")
        now = _utc_now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO paper_orders (
                    order_id, intent_id, status, requested_quantity, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (order_id, intent_id, status, requested_quantity, now, now),
            )

    def transition_paper_order(self, *, order_id: str, new_status: str) -> None:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM paper_orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            if row is None:
                raise StorageError(f"Unknown paper order: {order_id}")
            current_status = row["status"]
            if new_status == current_status:
                return
            if new_status not in _ORDER_TRANSITIONS[current_status]:
                raise StorageError(
                    f"Invalid paper-order transition: {current_status} -> {new_status}."
                )
            connection.execute(
                "UPDATE paper_orders SET status = ?, updated_at = ? WHERE order_id = ?",
                (new_status, _utc_now(), order_id),
            )

    def record_fill(
        self,
        *,
        fill_id: str,
        event_key: str,
        order_id: str,
        quantity: int,
        price: float,
        fees: float,
        filled_at: str,
    ) -> bool:
        if not all(value.strip() for value in (fill_id, event_key, order_id, filled_at)):
            raise ValueError("Fill identifiers and timestamp are required.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Fill quantity must be a positive integer.")
        if not _finite_number(price) or price <= 0:
            raise ValueError("Fill price must be finite and positive.")
        if not _finite_number(fees) or fees < 0:
            raise ValueError("Fill fees must be finite and non-negative.")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM fills WHERE event_key = ?",
                (event_key,),
            ).fetchone()
            expected = (fill_id, order_id, quantity, price, fees, filled_at)
            if existing is not None:
                actual = (
                    existing["fill_id"],
                    existing["order_id"],
                    existing["quantity"],
                    existing["price"],
                    existing["fees"],
                    existing["filled_at"],
                )
                if actual != expected:
                    raise IdempotencyConflict(
                        "Fill event key already exists with different fill data."
                    )
                return False
            order = connection.execute(
                "SELECT status, requested_quantity FROM paper_orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            if order is None:
                raise StorageError(f"Unknown paper order: {order_id}")
            if order["status"] not in {"SUBMITTED", "PARTIALLY_FILLED"}:
                raise StorageError(
                    f"Cannot record a fill for a {order['status']} paper order."
                )
            filled_quantity = int(
                connection.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM fills WHERE order_id = ?",
                    (order_id,),
                ).fetchone()[0]
            )
            total_filled = filled_quantity + quantity
            if total_filled > order["requested_quantity"]:
                raise StorageError("Recorded fills exceed the paper order quantity.")
            connection.execute(
                """
                INSERT INTO fills (
                    fill_id, event_key, order_id, quantity, price, fees, filled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (fill_id, event_key, order_id, quantity, price, fees, filled_at),
            )
            new_status = (
                "FILLED"
                if total_filled == order["requested_quantity"]
                else "PARTIALLY_FILLED"
            )
            connection.execute(
                "UPDATE paper_orders SET status = ?, updated_at = ? WHERE order_id = ?",
                (new_status, _utc_now(), order_id),
            )
        return True

    def upsert_position(
        self,
        *,
        position_id: str,
        session_id: str,
        symbol: str,
        exchange: str,
        quantity: int,
        average_price: float,
    ) -> None:
        if not all(value.strip() for value in (position_id, session_id, symbol)):
            raise ValueError("Position identifiers and symbol are required.")
        if exchange not in {"NSE", "BSE"}:
            raise ValueError("Position exchange must be NSE or BSE.")
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("Position quantity must be an integer.")
        if not _finite_number(average_price) or average_price < 0:
            raise ValueError("Average price must be finite and non-negative.")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO positions (
                    position_id, session_id, symbol, exchange, quantity, average_price, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, symbol, exchange) DO UPDATE SET
                    quantity = excluded.quantity,
                    average_price = excluded.average_price,
                    updated_at = excluded.updated_at
                """,
                (
                    position_id,
                    session_id,
                    symbol.upper(),
                    exchange,
                    quantity,
                    average_price,
                    _utc_now(),
                ),
            )

    def count_records(self) -> dict[str, int]:
        tables = (
            "sessions",
            "approvals",
            "signals",
            "order_intents",
            "paper_orders",
            "fills",
            "positions",
            "audit_events",
            "runtime_control",
        )
        with self._connection() as connection:
            return {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in tables
            }

    def portfolio_snapshot(
        self,
        *,
        session_id: str,
        marks: dict[tuple[str, str], float],
    ) -> PortfolioSnapshot:
        """Build a paper ledger snapshot from durable fills and caller-supplied marks."""
        with self._connection() as connection:
            session = connection.execute(
                "SELECT approved_capital FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise StorageError(f"Unknown session: {session_id}")
            fill_rows = connection.execute(
                """
                SELECT i.symbol, i.exchange, i.side, f.quantity, f.price,
                       f.fees, f.filled_at
                FROM fills AS f
                JOIN paper_orders AS o ON o.order_id = f.order_id
                JOIN order_intents AS i ON i.intent_id = o.intent_id
                WHERE i.session_id = ?
                ORDER BY f.filled_at, f.fill_id
                """,
                (session_id,),
            ).fetchall()

        fills = tuple(
            TradeFill(
                symbol=row["symbol"],
                exchange=row["exchange"],
                side=row["side"],
                quantity=row["quantity"],
                price=row["price"],
                fees=row["fees"],
                filled_at=row["filled_at"],
            )
            for row in fill_rows
        )
        return build_portfolio_snapshot(
            starting_cash=session["approved_capital"],
            fills=fills,
            marks=marks,
        )
