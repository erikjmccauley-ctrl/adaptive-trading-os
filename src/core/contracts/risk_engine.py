from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DailyRiskState:
    date: str
    trades_taken: int
    daily_pnl: float
    consecutive_losses: int
    kill_switch_active: bool
    kill_switch_reason: str = ''


class RiskEngine(ABC):
    """
    Abstract interface for the risk management layer.
    Gates every signal before it reaches the execution or alert layer.
    """

    @abstractmethod
    def validate_trade_intent(self, signal: dict) -> tuple[bool, str]:
        """
        Check whether a signal is allowed under current risk state.
        Returns (allowed: bool, reason: str).
        'reason' is empty string when allowed=True.
        """

    @abstractmethod
    def update_daily_state(self, outcome: dict) -> None:
        """
        Record a trade outcome (win/loss/timeout) and update daily state.
        Triggers kill switch automatically if limits are breached.
        """

    @abstractmethod
    def get_daily_state(self) -> DailyRiskState:
        """Return current daily risk state."""

    @abstractmethod
    def trigger_kill_switch(self, reason: str) -> None:
        """
        Manually halt all signal delivery for the rest of the session.
        Persisted so Lambda invocations and local runner both see it.
        """

    @abstractmethod
    def reset_daily_state(self) -> None:
        """
        Reset for a new trading day. Called at session open.
        Does NOT clear kill switch — that requires explicit operator action.
        """

    @abstractmethod
    def is_kill_switch_active(self) -> bool:
        """True if the kill switch has been triggered today."""
