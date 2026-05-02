"""
SchwabProvider — implements MarketDataProvider for the Charles Schwab API.

Wraps the existing fetch logic from src/data.py into a class that satisfies the
MarketDataProvider interface. Config-driven — no direct env var reads here.

Local mode:  token loaded from config.schwab_token_path (local file)
Lambda mode: token downloaded from S3, uploaded back after refresh
             (Lambda path is triggered by AWS_LAMBDA_FUNCTION_NAME env var)
"""

import os
import pandas as pd
from datetime import datetime, timedelta

from src.core.contracts.market_data import MarketDataProvider
from src.core.config import Config, get_config
from .validator import validate_ohlcv, ValidationResult

SYMBOL = '/MES'

_AGG = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}

# Schwab has no 1H bar endpoint. Fetch 30m and resample up.
# 4H is always derived from 1H — not fetched separately.
_TF_FETCH_CONFIG = {
    '1m':  {'interval': '1m',  'days_back': 5},
    '5m':  {'interval': '5m',  'days_back': 10},
    '15m': {'interval': '15m', 'days_back': 20},
    '1h':  {'interval': '30m', 'days_back': 30},
    '1d':  {'interval': '1d',  'days_back': 730},
}


class SchwabProvider(MarketDataProvider):
    """
    Market data provider backed by the Charles Schwab API.

    Usage:
        from src.core.config import get_config
        from src.data_sources.schwab import SchwabProvider

        provider = SchwabProvider(get_config())
        tf_data  = provider.get_multi_tf_data()
        pivots   = provider.get_pivot_source_ohlc()
    """

    def __init__(self, config: Config | None = None):
        self._config  = config or get_config()
        self._client  = None
        self._live    = False
        self._s3_bucket: str | None = None   # set only in Lambda mode

    # ── MarketDataProvider interface ──────────────────────────────────────────

    def get_multi_tf_data(self) -> dict[str, pd.DataFrame]:
        """
        Return OHLCV DataFrames for all active timeframes.
        Keys: '1m', '5m', '15m', '1h', '4h', '1d'
        """
        self._ensure_connected()
        data: dict[str, pd.DataFrame] = {}

        for tf, cfg in _TF_FETCH_CONFIG.items():
            raw = self._fetch_ohlcv(cfg['interval'], cfg['days_back'])
            if tf == '1h' and not raw.empty:
                raw = raw.resample('1h').agg(_AGG).dropna()
            cleaned, result = validate_ohlcv(raw, tf)
            if result.warnings:
                for w in result.warnings:
                    print(f"  [Schwab/{tf}] WARN: {w}")
            data[tf] = cleaned

        # 4H derived from 1H — never fetched from API
        df_1h = data.get('1h', pd.DataFrame())
        data['4h'] = df_1h.resample('4h').agg(_AGG).dropna() if not df_1h.empty else pd.DataFrame()

        return data

    def get_pivot_source_ohlc(self) -> dict[str, pd.DataFrame]:
        """
        Return daily, weekly, and monthly OHLCV used to compute pivot levels.
        Keys: 'daily', 'weekly', 'monthly'
        """
        self._ensure_connected()
        daily_raw = self._fetch_ohlcv('1d', 730)
        daily, result = validate_ohlcv(daily_raw, '1d')

        if not result.is_usable:
            raise RuntimeError(
                f"Schwab daily data unusable for pivot calculation: {result.warnings}"
            )

        weekly  = daily.resample('W').agg(_AGG).dropna()
        monthly = daily.resample('ME').agg(_AGG).dropna()
        return {'daily': daily, 'weekly': weekly, 'monthly': monthly}

    def is_live(self) -> bool:
        """True when connected to Schwab real-time data."""
        return self._live

    def get_symbol(self) -> str:
        return SYMBOL

    # ── Public helpers (used by backtest.py during transition) ────────────────

    def fetch_ohlcv(self, interval: str = '5m', days_back: int = 10) -> pd.DataFrame:
        """
        Public wrapper around _fetch_ohlcv.
        Returns a validated, cleaned DataFrame. Empty if fetch fails.
        Used by backtest.py to pull historical data per TF.
        """
        self._ensure_connected()
        raw = self._fetch_ohlcv(interval, days_back)
        # Determine the logical TF for validation purposes
        tf_map = {'1m': '1m', '5m': '5m', '15m': '15m', '30m': '1h', '1d': '1d'}
        tf = tf_map.get(interval, interval)
        cleaned, result = validate_ohlcv(raw, tf)
        if result.warnings:
            for w in result.warnings:
                print(f"  [Schwab/{tf}] WARN: {w}")
        return cleaned

    # ── Internal initialization ───────────────────────────────────────────────

    def _ensure_connected(self) -> None:
        if self._client is not None:
            return

        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            self._init_lambda()
        else:
            self._init_local()

    def _init_local(self) -> None:
        """Initialize Schwab client using local token file and .env credentials."""
        cfg = self._config
        if not cfg.schwab_api_key or not cfg.schwab_app_secret:
            raise RuntimeError(
                "SCHWAB_API_KEY / SCHWAB_APP_SECRET missing from config — "
                "check your .env file"
            )
        token_path = cfg.schwab_token_path
        if not os.path.exists(token_path):
            raise RuntimeError(
                f"{token_path} not found — run scripts/maintenance/refresh_schwab_token.py "
                "to authenticate with Schwab"
            )

        import schwab
        self._client = schwab.auth.easy_client(
            api_key=cfg.schwab_api_key,
            app_secret=cfg.schwab_app_secret,
            callback_url=cfg.schwab_redirect_uri,
            token_path=token_path,
        )
        self._live = True
        print(f"  [Schwab] Connected — real-time data active  ({token_path})")

    def _init_lambda(self) -> None:
        """
        Initialize Schwab client in Lambda mode.
        Downloads token from S3, uploads back after any refresh.

        TODO (Phase 14): implement full S3 token lifecycle here.
        For now this is a stub — Lambda still uses its own data.py init path.
        """
        raise NotImplementedError(
            "Lambda init path not yet implemented in SchwabProvider. "
            "Lambda currently uses lambda/trading-bot/function/src/data.py directly. "
            "This will be resolved in Phase 14."
        )

    # ── Internal fetch logic (exact port from src/data.py) ───────────────────

    def _fetch_ohlcv(self, interval: str = '5m', days_back: int = 10) -> pd.DataFrame:
        """Fetch OHLCV from Schwab API. Returns empty DataFrame on failure."""
        from schwab.client import Client
        C = Client.PriceHistory

        end   = datetime.now()
        start = end - timedelta(days=days_back)

        try:
            if interval == '1d':
                # Schwab has no '1d' frequency constant.
                # period_type=YEAR + period=TWO_DAYS + frequency_type=DAILY → 2yr of daily bars.
                # frequency=EVERY_MINUTE (value=1) is the correct integer for the daily slot.
                resp = self._client.get_price_history(
                    SYMBOL,
                    period_type=C.PeriodType.YEAR,
                    period=C.Period.TWO_DAYS,
                    frequency_type=C.FrequencyType.DAILY,
                    frequency=C.Frequency.EVERY_MINUTE,
                )
            else:
                freq_map = {
                    '1m':  (C.FrequencyType.MINUTE, C.Frequency.EVERY_MINUTE),
                    '5m':  (C.FrequencyType.MINUTE, C.Frequency.EVERY_FIVE_MINUTES),
                    '15m': (C.FrequencyType.MINUTE, C.Frequency.EVERY_FIFTEEN_MINUTES),
                    '30m': (C.FrequencyType.MINUTE, C.Frequency.EVERY_THIRTY_MINUTES),
                }
                if interval not in freq_map:
                    raise ValueError(f"Unsupported interval: {interval}")
                ft, f = freq_map[interval]
                resp = self._client.get_price_history(
                    SYMBOL,
                    frequency_type=ft,
                    frequency=f,
                    start_datetime=start,
                    end_datetime=end,
                    need_extended_hours_data=False,
                )

            data = resp.json()
            if data.get('empty', True) or not data.get('candles'):
                return pd.DataFrame()

            return self._candles_to_df(data['candles'])

        except Exception as e:
            print(f"  [Schwab] Fetch failed ({interval}): {e}")
            return pd.DataFrame()

    @staticmethod
    def _candles_to_df(candles: list[dict]) -> pd.DataFrame:
        """Convert Schwab candle list to a clean OHLCV DataFrame."""
        df = pd.DataFrame(candles)
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df = df.set_index('datetime')
        df.index.name = None
        return df[['open', 'high', 'low', 'close', 'volume']].dropna()
