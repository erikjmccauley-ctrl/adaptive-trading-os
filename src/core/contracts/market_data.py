from abc import ABC, abstractmethod
import pandas as pd


class MarketDataProvider(ABC):
    """
    Abstract interface for all market data sources.
    Implementations: SchwabProvider (live), TradovateProvider (future).
    """

    @abstractmethod
    def get_multi_tf_data(self) -> dict[str, pd.DataFrame]:
        """
        Return OHLCV DataFrames keyed by timeframe string.
        Keys: '1m', '5m', '15m', '1h', '4h', '1d'
        Each DataFrame: DatetimeIndex, columns [open, high, low, close, volume]
        """

    @abstractmethod
    def get_pivot_source_ohlc(self) -> dict[str, pd.DataFrame]:
        """
        Return daily/weekly/monthly OHLCV used to compute pivot levels.
        Keys: 'daily', 'weekly', 'monthly'
        """

    @abstractmethod
    def is_live(self) -> bool:
        """True if data is real-time; False if delayed or unavailable."""

    @abstractmethod
    def get_symbol(self) -> str:
        """Return the instrument symbol this provider is configured for."""

    @abstractmethod
    def get_latest_quote(self) -> dict:
        """
        Return the most recent bid/ask/last quote for the configured symbol.
        Keys: 'last', 'bid', 'ask', 'timestamp'
        Returns empty dict if unavailable (e.g., outside market hours).
        """
