"""
Candle resampler — single source of truth for OHLCV aggregation rules.

Previously the AGG dict was duplicated in src/data.py and backtest.py.
All resampling goes through here.
"""

import pandas as pd

AGG = {
    'open':   'first',
    'high':   'max',
    'low':    'min',
    'close':  'last',
    'volume': 'sum',
}

# Pandas resample rule strings for each logical timeframe
RESAMPLE_RULES: dict[str, str] = {
    '1m':  '1min',
    '5m':  '5min',
    '15m': '15min',
    '1h':  '1h',
    '4h':  '4h',
    '1d':  'D',
    'W':   'W',
    'ME':  'ME',
}


def resample(df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """
    Resample an OHLCV DataFrame to the target timeframe.

    `target_tf` must be a key in RESAMPLE_RULES or a valid pandas offset string.
    Returns an empty DataFrame if input is empty.
    """
    if df.empty:
        return df
    rule = RESAMPLE_RULES.get(target_tf, target_tf)
    return df.resample(rule).agg(AGG).dropna()


def resample_to_higher(df: pd.DataFrame, from_tf: str, to_tf: str) -> pd.DataFrame:
    """
    Resample from a lower timeframe to a higher one, with a validity check.
    Raises ValueError if to_tf is lower than from_tf in the standard hierarchy.
    """
    _ORDER = ['1m', '5m', '15m', '1h', '4h', '1d']
    if from_tf in _ORDER and to_tf in _ORDER:
        if _ORDER.index(to_tf) <= _ORDER.index(from_tf):
            raise ValueError(f"Cannot resample down: {from_tf} → {to_tf}")
    return resample(df, to_tf)


def build_higher_tfs(base_df: pd.DataFrame, base_tf: str) -> dict[str, pd.DataFrame]:
    """
    Given a base DataFrame and its timeframe, return a dict of all higher TFs
    derived by resampling. Used by backtest.py to build the tf_data dict.
    """
    _CHAIN: dict[str, list[str]] = {
        '1m':  ['5m', '15m', '1h', '4h', '1d'],
        '5m':  ['15m', '1h', '4h', '1d'],
        '15m': ['1h', '4h', '1d'],
        '1h':  ['4h', '1d'],
    }
    result = {base_tf: base_df}
    prev_tf = base_tf
    prev_df = base_df
    for tf in _CHAIN.get(base_tf, []):
        resampled = resample(prev_df, tf)
        result[tf] = resampled
        prev_df = resampled
        prev_tf = tf
    return result
