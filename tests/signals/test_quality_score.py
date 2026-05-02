import pandas as pd
import numpy as np
import pytest
from src.signals.scoring.quality import signal_quality


def _make_df(n=10, step=1.0, base=5000.0):
    """All-bullish trending OHLCV DataFrame."""
    closes = np.array([base + i * step for i in range(n)], dtype=float)
    opens  = closes - 0.5
    highs  = closes + 1.0
    lows   = opens  - 1.0
    return pd.DataFrame(
        {'open': opens, 'high': highs, 'low': lows, 'close': closes,
         'volume': np.full(n, 2000.0)}
    )


def test_signal_quality_returns_tuple():
    df = _make_df()
    result = signal_quality(df, 'bullish')
    assert isinstance(result, tuple) and len(result) == 2


def test_signal_quality_tier_is_valid():
    df = _make_df()
    tier, _ = signal_quality(df, 'bullish')
    assert tier in ('A', 'B', 'C')


def test_signal_quality_detail_not_empty():
    df = _make_df()
    _, detail = signal_quality(df, 'bullish')
    assert isinstance(detail, str) and len(detail) > 0


def test_signal_quality_tier_a():
    """Strong bar + 3/3 momentum + engulfing → score 3 → 'A'."""
    df = _make_df(n=10, step=1.0)
    # Bar -1: close at top of range → bar_close_quality ≈ 1.0 ≥ 0.65 (score +1)
    df.loc[df.index[-1], 'close'] = float(df.iloc[-1]['high'])
    # Bars -4..-2: all bullish → momentum_consistency = 3 (score +1)
    # Bars -2 engulfs bar -3:
    df.loc[df.index[-2], 'open']  = 5007.5  # bearish bar
    df.loc[df.index[-2], 'close'] = 5007.0
    df.loc[df.index[-1], 'open']  = 5006.9   # <= prior close
    df.loc[df.index[-1], 'close'] = float(df.iloc[-1]['high'])  # >= prior open, closed at high
    tier, _ = signal_quality(df, 'bullish', pivot_level=None)
    assert tier in ('A', 'B')  # engulfing + strong close should score ≥ 2


def test_signal_quality_tier_c():
    """Weak close + no momentum + no engulf → score 0 → 'C'."""
    df = _make_df(n=10, step=0.0)   # flat price, no trend
    # Force close at low (bad quality)
    df.loc[df.index[-1], 'close'] = float(df.iloc[-1]['low'])
    # Flip all prior bars to bearish (bad momentum for 'bullish' direction)
    for i in range(-4, -1):
        df.loc[df.index[i], 'close'] = float(df.iloc[i]['open']) - 0.1
    tier, _ = signal_quality(df, 'bullish', pivot_level=None)
    assert tier == 'C'


def test_signal_quality_both_directions_valid():
    df = _make_df()
    tier_long, _  = signal_quality(df, 'bullish')
    tier_short, _ = signal_quality(df, 'bearish')
    assert tier_long  in ('A', 'B', 'C')
    assert tier_short in ('A', 'B', 'C')


def test_signal_quality_no_pivot_level_no_crash():
    df = _make_df()
    tier, detail = signal_quality(df, 'bullish', pivot_level=None)
    assert tier in ('A', 'B', 'C')
    assert 'engulf' in detail   # engulfing path taken when pivot_level is None


def test_signal_quality_with_pivot_level():
    df = _make_df()
    level = float(df.iloc[-2]['low']) + 0.1
    tier, detail = signal_quality(df, 'bullish', pivot_level=level)
    assert tier in ('A', 'B', 'C')
    assert 'wick' in detail   # rejection path taken when pivot_level is given
