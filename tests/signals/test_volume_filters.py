import pandas as pd
import numpy as np
import pytest
from src.signals.filters.volume import (
    passes_volume_gate,
    passes_volume_direction_gate,
    volume_direction_note,
)
from src.signals.constants import VOLUME_DIRECTION_BARS


def _make_df(n=30, volume=3000.0, bullish=True):
    """All bars trending up, constant volume, all bullish or all bearish."""
    closes = np.linspace(5000.0, 5000.0 + n, n)
    if bullish:
        opens = closes - 0.5
    else:
        opens = closes + 0.5
    highs = np.maximum(opens, closes) + 0.5
    lows  = np.minimum(opens, closes) - 0.5
    return pd.DataFrame(
        {'open': opens, 'high': highs, 'low': lows, 'close': closes,
         'volume': np.full(n, volume)}
    )


def _make_mixed_dir_df(up_bars=3, total=10):
    """
    DataFrame where exactly `up_bars` of the 5 bars at positions -6..-2 are bullish.
    Remaining bars in that window are bearish.
    """
    closes = np.full(total, 5000.0)
    opens  = np.full(total, 5000.5)  # default bearish (open > close)
    n = VOLUME_DIRECTION_BARS  # 5
    window_start = total - (n + 1)   # first index of the -6..-2 window
    for i in range(n):
        idx = window_start + i
        if i < up_bars:
            opens[idx] = 4999.5   # bullish: close (5000) > open
    highs = np.maximum(opens, closes) + 0.5
    lows  = np.minimum(opens, closes) - 0.5
    return pd.DataFrame(
        {'open': opens, 'high': highs, 'low': lows, 'close': closes,
         'volume': np.full(total, 2000.0)}
    )


# ── passes_volume_gate ────────────────────────────────────────────────────────

def test_passes_volume_gate_above():
    df = _make_df(n=30, volume=3000.0)
    assert passes_volume_gate(df) is True


def test_passes_volume_gate_below():
    df = _make_df(n=30, volume=3000.0)
    df.loc[df.index[-3:], 'volume'] = 1.0   # recent bars collapse
    assert passes_volume_gate(df) is False


def test_passes_volume_gate_insufficient_bars():
    # Fewer than 23 bars → skip gate (return True)
    df = _make_df(n=20)
    assert passes_volume_gate(df) is True


def test_passes_volume_gate_zero_hist_volume():
    # avg_vol_20 == 0 → True (skip gate)
    df = _make_df(n=30, volume=0.0)
    assert passes_volume_gate(df) is True


# ── passes_volume_direction_gate ──────────────────────────────────────────────

def test_passes_volume_direction_gate_aligned_bullish():
    df = _make_df(n=10, bullish=True)   # all bars bullish
    assert passes_volume_direction_gate(df, 'bullish') is True


def test_passes_volume_direction_gate_against_bullish():
    df = _make_df(n=10, bullish=False)  # all bars bearish
    assert passes_volume_direction_gate(df, 'bullish') is False


def test_passes_volume_direction_gate_insufficient_bars():
    # Fewer than VOLUME_DIRECTION_BARS+1 rows → True (skip gate)
    df = _make_df(n=5)
    assert passes_volume_direction_gate(df, 'bullish') is True


# ── volume_direction_note ─────────────────────────────────────────────────────

def test_volume_direction_note_all_bullish():
    df = _make_mixed_dir_df(up_bars=5)   # 5/5 up
    note = volume_direction_note(df, 'bullish')
    assert 'vol' in note
    assert '100%' in note
    assert 'bullish' in note


def test_volume_direction_note_mixed():
    df = _make_mixed_dir_df(up_bars=2)   # 2/5 up → 40% → mixed
    note = volume_direction_note(df, 'bullish')
    assert 'mixed' in note


def test_volume_direction_note_contains_pct():
    df = _make_mixed_dir_df(up_bars=5)
    assert '%' in volume_direction_note(df, 'bullish')


def test_volume_direction_note_empty_when_insufficient():
    df = _make_df(n=5)   # too short
    assert volume_direction_note(df, 'bullish') == ''
