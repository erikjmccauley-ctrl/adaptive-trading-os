"""
VWAP — Volume Weighted Average Price.

Standard intraday VWAP that resets at the RTH open (9:30 ET) each day.
Used as a dynamic reference level: price above VWAP = bullish bias, below = bearish.

Formula:
  typical_price = (high + low + close) / 3
  vwap = cumsum(typical_price * volume) / cumsum(volume)
  Reset at 9:30 ET each session.
"""

import pandas as pd
from .labels import is_rth


def calc_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Compute intraday VWAP, resetting each RTH session.

    Input:  DatetimeIndex OHLCV DataFrame (any intraday TF).
    Output: pd.Series aligned to df.index with VWAP values.
            NaN for bars outside RTH.

    Note: For accurate results the index should be timezone-naive UTC
    (as returned by Schwab). Conversion to ET is handled internally.
    """
    if df.empty or not {'high', 'low', 'close', 'volume'}.issubset(df.columns):
        return pd.Series(index=df.index, dtype=float)

    tp = (df['high'] + df['low'] + df['close']) / 3   # typical price
    pv = tp * df['volume']

    vwap_vals = pd.Series(index=df.index, dtype=float)

    # Group by calendar date, compute cumulative VWAP within each RTH session
    for date, group in df.groupby(df.index.date):
        rth_mask = pd.Series(
            [is_rth(ts) for ts in group.index],
            index=group.index,
        )
        rth_group = group[rth_mask]
        if rth_group.empty:
            continue

        rth_tp = (rth_group['high'] + rth_group['low'] + rth_group['close']) / 3
        rth_pv = rth_tp * rth_group['volume']

        cum_pv  = rth_pv.cumsum()
        cum_vol = rth_group['volume'].cumsum()

        session_vwap = cum_pv / cum_vol.replace(0, float('nan'))
        vwap_vals.loc[session_vwap.index] = session_vwap

    return vwap_vals


def vwap_position(price: float, vwap: float) -> str:
    """
    Return the price's position relative to VWAP.
    'above' | 'below' | 'at' (within 0.1 pts)
    """
    diff = price - vwap
    if abs(diff) <= 0.1:
        return 'at'
    return 'above' if diff > 0 else 'below'
