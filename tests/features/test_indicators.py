import pandas as pd
import numpy as np
import pytest
from src.features.indicators import (
    smma, add_smmAs,
    calc_standard_pivots, calc_fib_pivots, get_all_pivots,
    ema_alignment, smma_micro_alignment,
    calc_atr, find_swing_high, find_swing_low,
    smma_pullback_touch, calc_adx,
    rejection_at_level, bar_close_quality, is_engulfing, momentum_consistency,
)


def _make_df(n=30, base=5000.0, step=1.0):
    """Uniformly trending OHLCV DataFrame. All bars bullish (close > open)."""
    closes = np.array([base + i * step for i in range(n)], dtype=float)
    opens  = closes - 0.5
    highs  = closes + 1.0
    lows   = opens  - 1.0
    vols   = np.full(n, 2000.0)
    return pd.DataFrame(
        {'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': vols}
    )


def _df_with_smmAs(smma3_val, smma8_val, smma21_val, n=25):
    """Build a trending df, then override the last row's SMMA values."""
    df = add_smmAs(_make_df(n=n))
    df.loc[df.index[-1], 'smma3']  = smma3_val
    df.loc[df.index[-1], 'smma8']  = smma8_val
    df.loc[df.index[-1], 'smma21'] = smma21_val
    return df


# ── SMMA ──────────────────────────────────────────────────────────────────────

def test_smma_formula():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    expected = s.ewm(alpha=1 / 3, min_periods=3, adjust=False).mean()
    pd.testing.assert_series_equal(smma(s, period=3), expected)


def test_smma_length_preserved():
    s = pd.Series(range(20), dtype=float)
    assert len(smma(s, period=5)) == 20


def test_add_smmAs_columns():
    result = add_smmAs(_make_df())
    assert {'smma3', 'smma8', 'smma21'}.issubset(result.columns)


def test_add_smmAs_does_not_mutate():
    df = _make_df()
    _ = add_smmAs(df)
    assert 'smma3' not in df.columns


# ── Standard Pivots ───────────────────────────────────────────────────────────

def test_standard_pivots_pp():
    p = calc_standard_pivots(high=5200.0, low=5000.0, close=5100.0)
    assert p['PP'] == pytest.approx((5200 + 5000 + 5100) / 3)


def test_standard_pivots_r1_s1():
    p = calc_standard_pivots(high=5200.0, low=5000.0, close=5100.0)
    pp = p['PP']
    assert p['R1'] == pytest.approx(2 * pp - 5000.0)
    assert p['S1'] == pytest.approx(2 * pp - 5200.0)


def test_standard_pivots_r2_s2():
    h, l, c = 5200.0, 5000.0, 5100.0
    p = calc_standard_pivots(h, l, c)
    pp = p['PP']
    assert p['R2'] == pytest.approx(pp + (h - l))
    assert p['S2'] == pytest.approx(pp - (h - l))


# ── Fibonacci Pivots ──────────────────────────────────────────────────────────

def test_fib_pivots_pp_matches_standard():
    h, l, c = 5200.0, 5000.0, 5100.0
    assert calc_fib_pivots(h, l, c)['PP'] == pytest.approx(calc_standard_pivots(h, l, c)['PP'])


def test_fib_pivot_r1():
    h, l, c = 5200.0, 5000.0, 5100.0
    p = calc_fib_pivots(h, l, c)
    pp = (h + l + c) / 3
    assert p['R1'] == pytest.approx(pp + 0.382 * (h - l))


def test_fib_pivot_s1():
    h, l, c = 5200.0, 5000.0, 5100.0
    p = calc_fib_pivots(h, l, c)
    pp = (h + l + c) / 3
    assert p['S1'] == pytest.approx(pp - 0.382 * (h - l))


# ── get_all_pivots ────────────────────────────────────────────────────────────

def test_get_all_pivots_keys():
    row = pd.DataFrame({'high': [5200.0, 5210.0], 'low': [5000.0, 5010.0], 'close': [5100.0, 5110.0]})
    levels = get_all_pivots({'daily': row, 'weekly': row, 'monthly': row})
    assert 'D_PP' in levels
    assert 'W_R1' in levels
    assert 'M_S1' in levels
    assert 'D_FR1' in levels   # fib variant


def test_get_all_pivots_skips_too_short():
    tiny = pd.DataFrame({'high': [5200.0], 'low': [5000.0], 'close': [5100.0]})
    assert get_all_pivots({'daily': tiny}) == {}


# ── Alignment ─────────────────────────────────────────────────────────────────

def test_ema_alignment_bullish():
    assert ema_alignment(_df_with_smmAs(5030.0, 5020.0, 5010.0)) == 'bullish'


def test_ema_alignment_bearish():
    assert ema_alignment(_df_with_smmAs(4970.0, 4980.0, 4990.0)) == 'bearish'


def test_ema_alignment_neutral():
    assert ema_alignment(_df_with_smmAs(5010.0, 5010.0, 5005.0)) == 'neutral'


def test_smma_micro_bullish():
    assert smma_micro_alignment(_df_with_smmAs(5030.0, 5020.0, 5010.0)) == 'bullish'


def test_smma_micro_bearish():
    assert smma_micro_alignment(_df_with_smmAs(4970.0, 4980.0, 4990.0)) == 'bearish'


# ── ATR ───────────────────────────────────────────────────────────────────────

def test_calc_atr_positive():
    assert calc_atr(_make_df(n=30)) > 0


def test_calc_atr_returns_float():
    assert isinstance(calc_atr(_make_df(n=30)), float)


# ── Swing High / Low ──────────────────────────────────────────────────────────

def test_find_swing_high():
    df = _make_df(n=30, step=1.0)
    assert find_swing_high(df, lookback=10) == pytest.approx(df['high'].iloc[-10:].max())


def test_find_swing_low():
    df = _make_df(n=30, step=1.0)
    assert find_swing_low(df, lookback=10) == pytest.approx(df['low'].iloc[-10:].min())


# ── SMMA Pullback Touch ───────────────────────────────────────────────────────

def test_smma_pullback_touch_bullish():
    df = add_smmAs(_make_df(n=30, step=2.0))
    # touched compares each recent bar's low to ITS OWN smma21 — use bar -3's smma21
    bar3_smma21  = float(df['smma21'].iloc[-3])
    last_smma21  = float(df['smma21'].iloc[-1])
    # Bar -3: low dips below its own smma21 (the touch)
    df.loc[df.index[-3], 'low']   = bar3_smma21 - 0.1
    df.loc[df.index[-3], 'close'] = bar3_smma21 + 1.0
    # Last bar: force bullish stack and close above its smma21 (the bounce)
    df.loc[df.index[-1], 'smma3']  = last_smma21 + 10.0
    df.loc[df.index[-1], 'smma8']  = last_smma21 + 5.0
    df.loc[df.index[-1], 'smma21'] = last_smma21
    df.loc[df.index[-1], 'close']  = last_smma21 + 2.0
    assert smma_pullback_touch(df, lookback=4) == 'bullish'


def test_smma_pullback_touch_none_no_touch():
    df = add_smmAs(_make_df(n=30, step=2.0))
    smma21_val = float(df['smma21'].iloc[-1])
    # Bullish stack on last bar
    df.loc[df.index[-1], 'smma3']  = smma21_val + 10.0
    df.loc[df.index[-1], 'smma8']  = smma21_val + 5.0
    df.loc[df.index[-1], 'smma21'] = smma21_val
    # Keep all recent lows well above smma21 (no touch)
    for i in range(-5, 0):
        df.loc[df.index[i], 'low'] = smma21_val + 3.0
    assert smma_pullback_touch(df, lookback=4) is None


# ── ADX ───────────────────────────────────────────────────────────────────────

def test_calc_adx_returns_float_in_range():
    result = calc_adx(_make_df(n=40))
    assert isinstance(result, float)
    assert 0 <= result <= 100


# ── Rejection at Level ────────────────────────────────────────────────────────

def test_rejection_at_level_bullish():
    df = _make_df(n=10)
    level = 5000.0
    df.loc[df.index[-2], 'low']   = level - 0.1   # bar dipped to level
    df.loc[df.index[-2], 'close'] = level + 1.0   # closed above → rejection confirmed
    assert rejection_at_level(df, 'bullish', level) is True


def test_rejection_at_level_bearish():
    df = _make_df(n=10)
    level = 5005.0
    df.loc[df.index[-2], 'high']  = level + 0.1
    df.loc[df.index[-2], 'close'] = level - 1.0
    assert rejection_at_level(df, 'bearish', level) is True


def test_rejection_at_level_miss():
    df = _make_df(n=10)
    far_level = float(df['high'].max()) + 100.0
    assert rejection_at_level(df, 'bullish', far_level) is False


# ── Bar Close Quality ─────────────────────────────────────────────────────────

def test_bar_close_quality_top():
    df = _make_df(n=5)
    df.loc[df.index[-1], 'close'] = float(df.iloc[-1]['high'])
    assert bar_close_quality(df) == pytest.approx(1.0)


def test_bar_close_quality_bottom():
    df = _make_df(n=5)
    df.loc[df.index[-1], 'close'] = float(df.iloc[-1]['low'])
    assert bar_close_quality(df) == pytest.approx(0.0)


def test_bar_close_quality_doji():
    df = _make_df(n=5)
    df.loc[df.index[-1], ['high', 'low', 'close']] = 5000.0
    assert bar_close_quality(df) == pytest.approx(0.5)


# ── Is Engulfing ──────────────────────────────────────────────────────────────

def test_is_engulfing_bullish():
    df = _make_df(n=5)
    # Prior bar: bearish (open > close)
    df.loc[df.index[-2], 'open']  = 5000.5
    df.loc[df.index[-2], 'close'] = 5000.0
    # Current bar: bullish body that wraps the prior bar's body
    df.loc[df.index[-1], 'open']  = 4999.9   # <= prior close (5000.0)
    df.loc[df.index[-1], 'close'] = 5000.6   # >= prior open (5000.5)
    assert is_engulfing(df, 'bullish') is True


def test_is_engulfing_false_when_not_engulfing():
    df = _make_df(n=5)
    df.loc[df.index[-2], 'open']  = 5000.0
    df.loc[df.index[-2], 'close'] = 5001.0
    df.loc[df.index[-1], 'open']  = 5000.5
    df.loc[df.index[-1], 'close'] = 5001.5
    assert is_engulfing(df, 'bullish') is False


# ── Momentum Consistency ──────────────────────────────────────────────────────

def test_momentum_consistency_all_bullish():
    df = _make_df(n=10, step=1.0)  # all bars: close > open
    assert momentum_consistency(df, 'bullish', lookback=3) == 3


def test_momentum_consistency_none_in_direction():
    df = _make_df(n=10, step=1.0)
    assert momentum_consistency(df, 'bearish', lookback=3) == 0


def test_momentum_consistency_partial():
    df = _make_df(n=10, step=1.0)
    # Flip bar -3 to bearish
    df.loc[df.index[-3], 'close'] = float(df.iloc[-3]['open']) - 0.1
    assert momentum_consistency(df, 'bullish', lookback=3) == 2
