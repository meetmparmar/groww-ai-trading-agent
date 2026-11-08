from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class TradingStyle(str, Enum):
    """Approved paper-trading style for the current short-term swing plan."""

    SWING = "swing"


class InstrumentCategory(str, Enum):
    """Instrument categories allowed in the initial v1 universe."""

    EQUITY = "equity"
    ETF = "etf"


@dataclass(frozen=True, slots=True)
class Instrument:
    """Metadata for a permitted Indian stock or exchange-traded fund."""

    symbol: str
    name: str
    exchange: str = "NSE"
    country: str = "IN"
    category: InstrumentCategory = InstrumentCategory.EQUITY
    allowed_styles: tuple[TradingStyle, ...] = (TradingStyle.SWING,)

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
    "UNLISTED",
    "DERIVATIVE",
)

SUPPORTED_STOCK_EXCHANGES: tuple[str, ...] = ("NSE", "BSE")


@dataclass(frozen=True, slots=True)
class MarketUniverse:
    """Scope and loaded listing catalog for the paper-trading universe."""

    name: str
    market: str
    country: str
    instruments: tuple[Instrument, ...] = ()
    exchanges: tuple[str, ...] = SUPPORTED_STOCK_EXCHANGES
    excluded_asset_classes: tuple[str, ...] = EXCLUDED_ASSET_CLASSES
    allowed_styles: tuple[TradingStyle, ...] = (TradingStyle.SWING,)
    notes: str = (
        "All listed cash-equity stocks and ETFs on NSE and BSE that are supported by Groww; "
        "the current approved strategy is short-lived swing trading with profit-taking once a "
        "material move is available and no forced end-of-day liquidation."
    )

    def __post_init__(self) -> None:
        known_listings = {(instrument.exchange, instrument.symbol) for instrument in self.instruments}
        if len(known_listings) != len(self.instruments):
            raise ValueError("Instrument listings must be unique by exchange and symbol.")
        for instrument in self.instruments:
            if instrument.exchange not in self.exchanges:
                raise ValueError(
                    f"{instrument.exchange} is not an allowed exchange in this universe."
                )
            if instrument.category not in (
                InstrumentCategory.EQUITY,
                InstrumentCategory.ETF,
            ):
                raise ValueError("Only listed cash equities and ETFs are allowed in this universe.")

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


DEFAULT_MARKET_UNIVERSE = MarketUniverse(
    name="india-stock-etf-paper-universe",
    market="NSE+BSE",
    country="IN",
    excluded_asset_classes=EXCLUDED_ASSET_CLASSES,
    allowed_styles=(TradingStyle.SWING,),
)


@dataclass(slots=True)
class SessionRiskProfile:
    """Paper-session risk state for the accepted T04 daily-loss accounting rules."""

    approved_capital: float = 50_000.0
    session_baseline_net_liquidation: float = 50_000.0
    current_net_liquidation: float = 50_000.0
    loss_threshold_rate: float = 0.015
    entry_lock_active: bool = False

    def __post_init__(self) -> None:
        if self.approved_capital <= 0:
            raise ValueError("Approved capital must be positive.")
        if not 0 < self.loss_threshold_rate < 1:
            raise ValueError("Loss threshold rate must be between 0 and 1.")

    @property
    def daily_loss_threshold(self) -> float:
        return self.approved_capital * self.loss_threshold_rate

    def session_net_pnl(self) -> float:
        return self.current_net_liquidation - self.session_baseline_net_liquidation

    def apply_breaker_if_needed(self) -> bool:
        if self.entry_lock_active:
            return True
        if self.session_net_pnl() <= -self.daily_loss_threshold:
            self.entry_lock_active = True
            return True
        return False

    def reset_entry_lock(self) -> None:
        self.entry_lock_active = False


@dataclass(frozen=True, slots=True)
class SessionApproval:
    """Validated Telegram approval for a paper-trading entry batch."""

    session_id: str
    batch_id: str
    approved_capital: float
    strategy_version: str = "short-lived-swing-v1"
    approved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=30))
    max_positions: int = 5
    valid_symbols: tuple[str, ...] = ()
    valid_exchange: str | None = None

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("Session approval requires a session identifier.")
        if not self.batch_id:
            raise ValueError("Session approval requires a batch identifier.")
        if self.approved_capital <= 0:
            raise ValueError("Approved capital must be positive.")
        if self.max_positions <= 0:
            raise ValueError("Maximum positions must be positive.")
        if self.expires_at <= self.approved_at:
            raise ValueError("Approval expiry must be after approval time.")

    def is_expired(self, now: datetime | None = None) -> bool:
        reference = now or datetime.now(timezone.utc)
        return reference >= self.expires_at

    def is_valid(self, now: datetime | None = None) -> bool:
        return not self.is_expired(now)

    def can_authorize_symbol(self, symbol: str, *, now: datetime | None = None) -> bool:
        if not self.is_valid(now):
            return False
        normalized = symbol.upper()
        if not self.valid_symbols:
            return True
        return normalized in {item.upper() for item in self.valid_symbols}

    def can_authorize_capital(self, proposed_capital: float, *, now: datetime | None = None) -> bool:
        if not self.is_valid(now):
            return False
        return proposed_capital <= self.approved_capital

    def requires_reapproval(
        self,
        *,
        symbol: str | None = None,
        proposed_capital: float | None = None,
    ) -> bool:
        if symbol is not None and self.valid_symbols and symbol.upper() not in {
            item.upper() for item in self.valid_symbols
        }:
            return True
        if proposed_capital is not None and proposed_capital > self.approved_capital:
            return True
        return False


@dataclass(frozen=True, slots=True)
class RecoveryTarget:
    """Operational health and recovery targets for the paper-trading workflow."""

    rto_minutes: int = 15
    rpo_minutes: int = 5
    stale_data_minutes: int = 15
    heartbeat_seconds: int = 60
    alert_deadline_minutes: int = 10
    retention_days: int = 30
    downtime_budget_minutes: int = 30

    def __post_init__(self) -> None:
        if self.rto_minutes <= 0:
            raise ValueError("Recovery-time objective must be positive.")
        if self.rpo_minutes <= 0:
            raise ValueError("Recovery-point objective must be positive.")
        if self.stale_data_minutes <= 0:
            raise ValueError("Stale-data threshold must be positive.")
        if self.heartbeat_seconds <= 0:
            raise ValueError("Heartbeat interval must be positive.")

    def is_stale(self, age_minutes: int) -> bool:
        return age_minutes > self.stale_data_minutes

    def is_recovery_within_target(self, minutes_to_restore: int) -> bool:
        return minutes_to_restore <= self.rto_minutes


@dataclass(frozen=True, slots=True)
class BudgetLimit:
    """Monthly spending ceiling for local operation and optional AWS resources."""

    monthly_cap: float = 4_000.0
    ai_usage_cap: float = 500.0
    aws_cap: float = 1_500.0
    subscriptions_cap: float = 500.0

    def __post_init__(self) -> None:
        if self.monthly_cap <= 0:
            raise ValueError("Monthly cap must be positive.")
        if self.ai_usage_cap < 0 or self.aws_cap < 0 or self.subscriptions_cap < 0:
            raise ValueError("All component budgets must be non-negative.")

    def is_allowed(self, spend_amount: float) -> bool:
        return spend_amount <= self.monthly_cap

    def remaining_budget(self, spent_amount: float) -> float:
        return max(self.monthly_cap - spent_amount, 0.0)


@dataclass(frozen=True, slots=True)
class EvaluationCriteria:
    """Minimum success evidence required before the MVP can advance."""

    min_sessions: int = 30
    target_net_return_pct: float = 0.10
    max_drawdown_pct: float = 0.15
    max_critical_defects: int = 0
    require_no_real_order_path: bool = True

    def __post_init__(self) -> None:
        if self.min_sessions <= 0:
            raise ValueError("Minimum sessions must be positive.")
        if self.max_drawdown_pct < 0:
            raise ValueError("Maximum drawdown cannot be negative.")
        if self.max_critical_defects < 0:
            raise ValueError("Critical defect allowance cannot be negative.")

    def passes(
        self,
        *,
        sessions_completed: int,
        net_return_pct: float,
        max_drawdown_pct: float,
        critical_defects: int,
    ) -> bool:
        if sessions_completed < self.min_sessions:
            return False
        if net_return_pct < self.target_net_return_pct:
            return False
        if max_drawdown_pct > self.max_drawdown_pct:
            return False
        if critical_defects > self.max_critical_defects:
            return False
        return True


@dataclass(frozen=True, slots=True)
class DataSourceSpec:
    """Market or broker data source contract and freshness requirements."""

    source_name: str
    purpose: str
    is_verified: bool = False
    freshness_minutes: int = 15
    requires_source_links: bool = True

    def __post_init__(self) -> None:
        if not self.source_name:
            raise ValueError("Source name is required.")
        if not self.purpose:
            raise ValueError("Source purpose is required.")
        if self.freshness_minutes <= 0:
            raise ValueError("Freshness window must be positive.")

    def is_acceptable(self, age_minutes: int) -> bool:
        return self.is_verified and age_minutes <= self.freshness_minutes


@dataclass(frozen=True, slots=True)
class SimulationParameters:
    """Fill, cost, and gap assumptions used in paper evaluation."""

    slippage_bps: float = 5.0
    market_impact_bps: float = 2.0
    fee_bps: float = 1.0
    tax_bps: float = 0.0
    max_gap_pct: float = 0.5
    fill_latency_seconds: int = 30

    def __post_init__(self) -> None:
        if self.slippage_bps < 0 or self.market_impact_bps < 0:
            raise ValueError("Slippage and market-impact assumptions cannot be negative.")
        if self.max_gap_pct < 0:
            raise ValueError("Maximum allowed gap cannot be negative.")
        if self.fill_latency_seconds <= 0:
            raise ValueError("Fill-latency assumption must be positive.")

    def total_cost_bps(self) -> float:
        return self.slippage_bps + self.market_impact_bps + self.fee_bps + self.tax_bps

    def allows_gap(self, gap_pct: float) -> bool:
        return gap_pct <= self.max_gap_pct


@dataclass(frozen=True, slots=True)
class ComponentInterface:
    """Interface contract for a system component and its expected failure handling."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    failure_modes: tuple[str, ...]
    owner: str = "paper-trading-agent"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Component name is required.")
        if not self.inputs:
            raise ValueError("Component inputs cannot be empty.")
        if not self.outputs:
            raise ValueError("Component outputs cannot be empty.")

    def is_compatible(self, required_input: str) -> bool:
        return required_input in self.inputs


@dataclass(frozen=True, slots=True)
class StateSecuritySpec:
    """State durability and audit requirements for the paper-trading system."""

    persisted_states: tuple[str, ...] = ("session", "orders", "positions", "approvals")
    audit_fields: tuple[str, ...] = ("timestamp", "actor", "action", "reason")
    secrets_policy: str = "Never log secrets or tokens"
    backup_boundaries: tuple[str, ...] = ("state", "audit", "config")

    def __post_init__(self) -> None:
        if not self.persisted_states:
            raise ValueError("Persisted states cannot be empty.")
        if not self.audit_fields:
            raise ValueError("Audit fields must be defined.")

    def requires_audit(self, action: str) -> bool:
        return action in {"entry", "exit", "approval", "recovery"}


@dataclass(frozen=True, slots=True)
class ImplementationReadinessChecklist:
    """Gate to confirm the application is ready for implementation work."""

    strategy_accepted: bool = False
    limits_accepted: bool = False
    loss_rules_accepted: bool = False
    data_sources_verified: bool = False
    simulation_assumptions_defined: bool = False

    def is_ready(self) -> bool:
        return (
            self.strategy_accepted
            and self.limits_accepted
            and self.loss_rules_accepted
            and self.data_sources_verified
            and self.simulation_assumptions_defined
        )


# Retained for compatibility with the earlier stock-only domain model.
DEFAULT_EQUITY_UNIVERSE = DEFAULT_MARKET_UNIVERSE

__all__ = [
    "DEFAULT_EQUITY_UNIVERSE",
    "DEFAULT_MARKET_UNIVERSE",
    "BudgetLimit",
    "ComponentInterface",
    "DataSourceSpec",
    "EvaluationCriteria",
    "EXCLUDED_ASSET_CLASSES",
    "ImplementationReadinessChecklist",
    "Instrument",
    "InstrumentCategory",
    "MarketUniverse",
    "RecoveryTarget",
    "SessionApproval",
    "SessionRiskProfile",
    "SimulationParameters",
    "StateSecuritySpec",
    "SUPPORTED_STOCK_EXCHANGES",
    "TradingStyle",
]
