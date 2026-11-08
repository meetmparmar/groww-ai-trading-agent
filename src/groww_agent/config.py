from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigurationError(ValueError):
    """Raised when application configuration is missing or unsafe."""


def _positive_number(
    values: Mapping[str, str], name: str, default: float
) -> float:
    raw_value = values.get(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a number.") from error
    if not math.isfinite(value) or value <= 0:
        raise ConfigurationError(f"{name} must be a finite positive number.")
    return value


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated, paper-only configuration for the local application."""

    mode: str = "paper"
    database_path: Path = Path("data/paper-trading.sqlite3")
    default_capital: float = 50_000.0
    capital_ceiling: float = 100_000.0
    per_position_risk_rate: float = 0.005
    daily_loss_lock_rate: float = 0.015

    def __post_init__(self) -> None:
        if self.mode != "paper":
            raise ConfigurationError("Only APP_MODE=paper is supported.")
        values = (
            self.default_capital,
            self.capital_ceiling,
            self.per_position_risk_rate,
            self.daily_loss_lock_rate,
        )
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ConfigurationError("Paper capital and risk values must be finite and positive.")
        if self.default_capital > 50_000:
            raise ConfigurationError("Default capital cannot exceed INR 50000.")
        if self.capital_ceiling > 100_000:
            raise ConfigurationError("Capital ceiling cannot exceed the approved INR 100000.")
        if self.default_capital > self.capital_ceiling:
            raise ConfigurationError("Default capital cannot exceed the capital ceiling.")
        if self.per_position_risk_rate > 0.005:
            raise ConfigurationError("Per-position risk rate cannot exceed the approved 0.5%.")
        if self.daily_loss_lock_rate > 0.015:
            raise ConfigurationError("Daily loss lock rate cannot exceed the approved 1.5%.")
        if not self.database_path.name:
            raise ConfigurationError("Database path must name a file.")

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> AppConfig:
        """Load validated configuration; all non-paper modes are rejected."""
        env = os.environ if values is None else values
        mode = env.get("APP_MODE", "paper").strip().lower()
        db_value = env.get("GROWW_AGENT_DATABASE", "data/paper-trading.sqlite3")
        db_path = Path(db_value).expanduser()
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path

        config = cls(
            mode=mode,
            database_path=db_path,
            default_capital=_positive_number(env, "PAPER_DEFAULT_CAPITAL", 50_000.0),
            capital_ceiling=_positive_number(env, "PAPER_CAPITAL_CEILING", 100_000.0),
            per_position_risk_rate=_positive_number(env, "PAPER_POSITION_RISK_RATE", 0.005),
            daily_loss_lock_rate=_positive_number(env, "PAPER_DAILY_LOSS_RATE", 0.015),
        )
        return config
