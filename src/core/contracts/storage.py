from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class StorageProvider(ABC):
    """
    Abstract interface for all persistence backends.
    Implementations: LocalStorage (dev/CSV), S3Storage (AWS), DynamoDBStateStore (state).
    """

    @abstractmethod
    def write_signal(self, signal: dict) -> None:
        """Persist a fired signal record."""

    @abstractmethod
    def read_signals(self, date: str) -> list[dict]:
        """Return all signals for a given date (YYYY-MM-DD)."""

    @abstractmethod
    def write_candles(self, tf: str, df: pd.DataFrame) -> None:
        """Persist normalized candles for a given timeframe."""

    @abstractmethod
    def read_candles(self, tf: str, days: int = 30) -> pd.DataFrame:
        """Return normalized candles for a given timeframe, up to N days back."""

    @abstractmethod
    def write_outcome(self, outcome: dict) -> None:
        """Persist a resolved trade outcome (win/loss/timeout + MFE/MAE)."""

    @abstractmethod
    def read_outcomes(self, days: int = 90) -> list[dict]:
        """Return resolved outcomes for the past N days."""

    @abstractmethod
    def get_cooldown_record(self, key: tuple) -> Optional[str]:
        """
        Return the ISO timestamp when (entry_tf, level, direction) last fired.
        Returns None if no record exists.
        """

    @abstractmethod
    def set_cooldown_record(self, key: tuple, fired_at: str) -> None:
        """Persist the last-fired timestamp for a cooldown key."""
