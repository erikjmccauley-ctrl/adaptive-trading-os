"""
Volatility regime utilities.

ATR percentile tells you WHERE today's volatility sits relative to recent history.
Useful as a second dimension alongside ADX trend regime:
  - ADX trending + low ATR percentile → early trend, room to run
  - ADX trending + high ATR percentile → extended move, tighter targets
  - ADX ranging + high ATR percentile → volatile chop, reduce size or skip
"""

import pandas as pd
from src.features.indicators import calc_atr


def calc_atr_percentile(df_daily: pd.DataFrame, lookback: int = 30) -> float:
    """
    Return where today's daily ATR sits within the last `lookback` daily ATRs.

    Returns 0.0–1.0:
      0.0 = today's ATR is the lowest in the lookback window (very quiet)
      0.5 = median volatility
      1.0 = today's ATR is the highest in the lookback window (very volatile)

    Returns 0.5 (neutral) if insufficient data.
    """
    if df_daily is None or df_daily.empty or len(df_daily) < lookback + 1:
        return 0.5

    # Compute ATR for each bar in the lookback window
    window = df_daily.iloc[-(lookback + 14):]   # extra bars for ATR convergence
    if len(window) < 15:
        return 0.5

    high  = window['high']
    low   = window['low']
    close = window['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr_series = tr.ewm(span=14, adjust=False).mean()

    # Slice to just the lookback window (drop the extra warm-up bars)
    atr_window = atr_series.iloc[-lookback:]
    if atr_window.empty:
        return 0.5

    today_atr = float(atr_window.iloc[-1])
    min_atr   = float(atr_window.min())
    max_atr   = float(atr_window.max())

    if max_atr == min_atr:
        return 0.5

    return round((today_atr - min_atr) / (max_atr - min_atr), 3)


def volatility_label(percentile: float) -> str:
    """Convert an ATR percentile to a human-readable label."""
    if percentile >= 0.75:
        return 'high'
    if percentile <= 0.25:
        return 'low'
    return 'normal'
