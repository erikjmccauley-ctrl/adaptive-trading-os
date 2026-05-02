import pandas as pd
import numpy as np


def smma(series, period):
    """Smoothed Moving Average — matches the SMMA shown on your WolfWave chart."""
    return series.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def add_smmAs(df):
    df = df.copy()
    df['smma3']  = smma(df['close'], 3)
    df['smma8']  = smma(df['close'], 8)
    df['smma21'] = smma(df['close'], 21)
    return df


def calc_standard_pivots(high, low, close):
    pp = (high + low + close) / 3
    return {
        'PP': pp,
        'R1': 2 * pp - low,
        'R2': pp + (high - low),
        'R3': high + 2 * (pp - low),
        'S1': 2 * pp - high,
        'S2': pp - (high - low),
        'S3': low - 2 * (high - pp),
    }


def calc_fib_pivots(high, low, close):
    pp  = (high + low + close) / 3
    rng = high - low
    return {
        'PP':  pp,
        'R1':  pp + 0.382 * rng,
        'R2':  pp + 0.618 * rng,
        'R3':  pp + 1.000 * rng,
        'S1':  pp - 0.382 * rng,
        'S2':  pp - 0.618 * rng,
        'S3':  pp - 1.000 * rng,
    }


def get_all_pivots(pivot_source):
    """
    Returns a flat dict of all pivot levels from daily, weekly, monthly.
    Keys: D_PP, D_R1, D_FibR1, W_PP, M_S2, etc.
    """
    prefix_map = {'daily': 'D', 'weekly': 'W', 'monthly': 'M'}
    levels = {}

    for tf_name, df in pivot_source.items():
        if df is None or len(df) < 2:
            continue
        prev = df.iloc[-2]  # previous completed period
        prefix = prefix_map.get(tf_name, tf_name[0].upper())

        for k, v in calc_standard_pivots(prev['high'], prev['low'], prev['close']).items():
            levels[f"{prefix}_{k}"] = round(float(v), 2)

        for k, v in calc_fib_pivots(prev['high'], prev['low'], prev['close']).items():
            if k != 'PP':  # don't duplicate PP
                levels[f"{prefix}_F{k}"] = round(float(v), 2)

    return levels


def ema_alignment(df):
    """Returns 'bullish', 'bearish', or 'neutral' based on full SMMA stack (3>8>21)."""
    last = df.iloc[-1]
    if last['smma3'] > last['smma8'] > last['smma21']:
        return 'bullish'
    elif last['smma3'] < last['smma8'] < last['smma21']:
        return 'bearish'
    return 'neutral'


def smma_micro_alignment(df):
    """Fast directional bias from smma3 vs smma8 only. Used for ranging scalp entries
    where the full stack won't align but the short-term momentum is readable."""
    last = df.iloc[-1]
    if last['smma3'] > last['smma8']:
        return 'bullish'
    elif last['smma3'] < last['smma8']:
        return 'bearish'
    return 'neutral'


def calc_atr(df, period=14):
    high  = df['high']
    low   = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return float(tr.ewm(span=period, adjust=False).mean().iloc[-1])


def find_swing_high(df, lookback=10):
    return float(df['high'].iloc[-lookback:].max())


def find_swing_low(df, lookback=10):
    return float(df['low'].iloc[-lookback:].min())


def smma_pullback_touch(df, lookback=4):
    """
    Returns 'bullish', 'bearish', or None.

    'bullish': stack is 3>8>21, price touched or undercut smma21 within the last
               `lookback` bars, and the current bar closes back above smma21.
               → trend pullback to dynamic support, bounce confirmed.

    'bearish': mirror image — stack 3<8<21, price briefly above smma21, now closed below.
    """
    if len(df) < lookback + 2:
        return None

    last    = df.iloc[-1]
    recent  = df.iloc[-(lookback + 1):-1]   # completed bars before the current

    bullish_stack = last['smma3'] > last['smma8'] > last['smma21']
    bearish_stack = last['smma3'] < last['smma8'] < last['smma21']

    if bullish_stack:
        touched = (recent['low'] <= recent['smma21']).any()
        bounced = last['close'] > last['smma21']
        if touched and bounced:
            return 'bullish'

    if bearish_stack:
        touched = (recent['high'] >= recent['smma21']).any()
        bounced = last['close'] < last['smma21']
        if touched and bounced:
            return 'bearish'

    return None


def calc_adx(df, period=14):
    """ADX trend strength indicator. > 25 = trending, < 20 = ranging."""
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)

    up_move  = high.diff()
    dn_move  = -low.diff()
    plus_dm  = pd.Series(np.where((up_move > dn_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn_move > up_move) & (dn_move > 0), dn_move, 0.0), index=df.index)

    smooth   = lambda s: s.ewm(alpha=1 / period, adjust=False).mean()
    atr_s    = smooth(tr)
    plus_di  = 100 * smooth(plus_dm) / atr_s
    minus_di = 100 * smooth(minus_dm) / atr_s
    dx       = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return float(smooth(dx).iloc[-1])


# ── Price action helpers ──────────────────────────────────────────────────────

def rejection_at_level(df, direction, pivot_level, lookback=2):
    """
    True if any bar in the last `lookback` bars tested the pivot level and closed
    on the trade side — confirming the level held.
    Long: bar low <= level AND bar close > level.
    Short: bar high >= level AND bar close < level.
    """
    recent = df.iloc[-(lookback + 1):]
    if direction == 'bullish':
        return bool(((recent['low'] <= pivot_level) & (recent['close'] > pivot_level)).any())
    else:
        return bool(((recent['high'] >= pivot_level) & (recent['close'] < pivot_level)).any())


def bar_close_quality(df):
    """
    Close position within the bar range: 0.0 = closed at low, 1.0 = closed at high.
    Returns 0.5 for doji (zero range). High = bullish close strength, low = bearish.
    """
    last      = df.iloc[-1]
    bar_range = float(last['high'] - last['low'])
    if bar_range == 0:
        return 0.5
    return float((last['close'] - last['low']) / bar_range)


def is_engulfing(df, direction):
    """
    True if the current bar's body completely engulfs the prior bar's body in the
    given direction.
    Bullish: current bullish body contains a prior bearish body.
    Bearish: current bearish body contains a prior bullish body.
    """
    if len(df) < 2:
        return False
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    c_o, c_c = float(curr['open']), float(curr['close'])
    p_o, p_c = float(prev['open']), float(prev['close'])
    if direction == 'bullish':
        return c_c > c_o and p_c < p_o and c_o <= p_c and c_c >= p_o
    else:
        return c_c < c_o and p_c > p_o and c_o >= p_c and c_c <= p_o


def momentum_consistency(df, direction, lookback=3):
    """
    Count of the last `lookback` completed bars that closed in the given direction.
    bullish = close > open, bearish = close < open.
    """
    if len(df) < lookback + 2:
        return 0
    recent = df.iloc[-(lookback + 1):-1]
    if direction == 'bullish':
        return int((recent['close'] > recent['open']).sum())
    else:
        return int((recent['close'] < recent['open']).sum())
