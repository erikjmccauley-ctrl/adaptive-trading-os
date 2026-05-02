"""
Unit tests for the three signal generator functions.
Uses minimal mock classes for LevelCatalog and PivotLevel.
The orchestrator is responsible for checking SMMA alignment and pullback touch
before calling these functions — so those conditions are not tested here.
"""
import pandas as pd
import numpy as np
import pytest
from src.features.indicators import add_smmAs
from src.signals.candidate_generators.pivot_signal   import check_pivot_setup
from src.signals.candidate_generators.pullback_signal import check_pullback_setup
from src.signals.candidate_generators.range_scalp    import check_range_scalp
from src.signals.constants import MIN_RR, MIN_RR_SCALP


# ── Mock helpers ──────────────────────────────────────────────────────────────

class _Level:
    def __init__(self, name, price):
        self.name  = name
        self.price = price


class _Catalog:
    """Minimal catalog that always returns the same t1 (and optional t2)."""
    def __init__(self, t1_name, t1_price, t2_name=None, t2_price=None):
        self._t1 = _Level(t1_name, t1_price)
        self._t2 = _Level(t2_name, t2_price) if t2_name else None

    def two_targets(self, price, direction):
        return self._t1, self._t2


def _make_signal_df(n=30, price=5000.0, pivot_level=4999.5):
    """
    Ascending OHLCV DataFrame (all bars bullish) with smma columns.
    Bar -2 is engineered to test-and-reject `pivot_level` (low < level, close > level),
    satisfying `rejection_at_level` for LONG signals.
    Volume is constant → volume gate always passes.
    """
    step   = 1.0
    closes = np.array([price - (n - 1 - i) * step for i in range(n)], dtype=float)
    opens  = closes - 0.5
    highs  = closes + 1.0
    lows   = opens  - 1.0

    df = pd.DataFrame(
        {'open': opens, 'high': highs, 'low': lows, 'close': closes,
         'volume': np.full(n, 3000.0)}
    )
    df = add_smmAs(df)

    # Force rejection wick on bar -2 for LONG at pivot_level
    df.loc[df.index[-2], 'low']   = pivot_level - 0.1
    df.loc[df.index[-2], 'close'] = pivot_level + 0.5

    return df


_MARKET_CTX  = {'daily_consumed_pct': 0.50}
_ADX_VAL     = 28.0
_ADX_TF      = '1h'
_REGIME      = 'trending'
_ALIGN       = 'bullish'
_ENTRY_TF    = '5m'

_CATALOG_LONG  = _Catalog('D_R1', 5060.0, 'D_R2', 5100.0)
_CATALOG_SHORT = _Catalog('D_S1', 4940.0, 'D_S2', 4900.0)
_CATALOG_NONE  = _Catalog.__new__(_Catalog)   # no t1


class _CatalogNoTarget:
    def two_targets(self, price, direction):
        return None, None


# ── Pivot Signal ──────────────────────────────────────────────────────────────

def test_pivot_signal_fires_long():
    df = _make_signal_df(price=5000.0, pivot_level=4999.5)
    nearby = [_Level('D_PP', 4999.5)]   # support just below price
    result = check_pivot_setup(
        _ENTRY_TF, 'bullish', 5000.0, df, nearby,
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is not None


def test_pivot_signal_none_no_nearby_levels():
    df = _make_signal_df()
    result = check_pivot_setup(
        _ENTRY_TF, 'bullish', 5000.0, df, [],   # empty nearby_levels
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is None


def test_pivot_signal_none_no_target():
    df = _make_signal_df()
    nearby = [_Level('D_PP', 4999.5)]
    result = check_pivot_setup(
        _ENTRY_TF, 'bullish', 5000.0, df, nearby,
        _CatalogNoTarget(), _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is None


def test_pivot_signal_has_required_fields():
    df = _make_signal_df()
    nearby = [_Level('D_PP', 4999.5)]
    result = check_pivot_setup(
        _ENTRY_TF, 'bullish', 5000.0, df, nearby,
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is not None
    for field in ('direction', 'entry', 'stop', 'target1', 'near_level', 'rr', 'signal_type'):
        assert field in result, f"missing field: {field}"


def test_pivot_signal_direction_label():
    df = _make_signal_df()
    nearby = [_Level('D_PP', 4999.5)]
    result = check_pivot_setup(
        _ENTRY_TF, 'bullish', 5000.0, df, nearby,
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result['direction'] == 'LONG'
    assert result['signal_type'] == 'pivot'


def test_pivot_signal_rr_meets_minimum():
    df = _make_signal_df()
    nearby = [_Level('D_PP', 4999.5)]
    result = check_pivot_setup(
        _ENTRY_TF, 'bullish', 5000.0, df, nearby,
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is not None
    assert result['rr'] >= MIN_RR


def test_pivot_signal_t2_suppressed_in_ranging():
    df = _make_signal_df()
    nearby = [_Level('D_PP', 4999.5)]
    result = check_pivot_setup(
        _ENTRY_TF, 'bullish', 5000.0, df, nearby,
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, 'ranging',
    )
    assert result is not None
    assert result['target2'] is None
    assert result['t2_suppressed'] is True


# ── Pullback Signal ───────────────────────────────────────────────────────────

def test_pullback_signal_fires():
    df = _make_signal_df()   # smma columns already on df
    result = check_pullback_setup(
        _ENTRY_TF, 'bullish', 5000.0, df,
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is not None


def test_pullback_signal_none_no_target():
    df = _make_signal_df()
    result = check_pullback_setup(
        _ENTRY_TF, 'bullish', 5000.0, df,
        _CatalogNoTarget(), _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is None


def test_pullback_signal_has_hold_condition():
    df = _make_signal_df()
    result = check_pullback_setup(
        _ENTRY_TF, 'bullish', 5000.0, df,
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is not None
    assert 'hold_condition' in result
    assert result['hold_condition'] is not None
    assert 'SMMA21' in result['hold_condition']


def test_pullback_signal_type():
    df = _make_signal_df()
    result = check_pullback_setup(
        _ENTRY_TF, 'bullish', 5000.0, df,
        _CATALOG_LONG, _ALIGN, _MARKET_CTX, _ADX_VAL, _ADX_TF, _REGIME,
    )
    assert result is not None
    assert result['signal_type'] == 'pullback'
    assert result['near_level'] == 'SMMA21'


# ── Range Scalp ───────────────────────────────────────────────────────────────

def _make_range_df(n=30, price=5000.0):
    """Plain OHLCV for range scalp tests — no smma or volume gate needed."""
    closes = np.array([price - (n - 1 - i) * 0.5 for i in range(n)], dtype=float)
    opens  = closes - 0.3
    highs  = closes + 0.5
    lows   = opens  - 0.5
    return pd.DataFrame(
        {'open': opens, 'high': highs, 'low': lows, 'close': closes,
         'volume': np.full(n, 2000.0)}
    )


_RANGE_CTX = {'daily_consumed_pct': 0.40}
_ADX_RANGE  = 14.0


def test_range_scalp_fires_long():
    df = _make_range_df(price=5000.0)
    nearby = [_Level('D_S1', 4999.5)]   # support below
    catalog = _Catalog('D_R1', 5020.0)
    result = check_range_scalp(
        '1m', 'bullish', 5000.0, df, nearby, catalog,
        'neutral', _RANGE_CTX, _ADX_RANGE, '15m', vol_note='', micro_dir='bullish',
    )
    assert result is not None
    assert result['direction'] == 'LONG'


def test_range_scalp_fires_short():
    n = 30
    price = 5000.0
    closes = np.array([price + (n - 1 - i) * 0.5 for i in range(n)], dtype=float)
    opens  = closes + 0.3
    highs  = closes + 0.5
    lows   = opens  - 0.5
    df = pd.DataFrame(
        {'open': opens, 'high': highs, 'low': lows, 'close': closes,
         'volume': np.full(n, 2000.0)}
    )
    nearby = [_Level('D_R1', 5000.5)]  # resistance above
    catalog = _Catalog('D_PP', 4980.0)
    result = check_range_scalp(
        '1m', 'bearish', 5000.0, df, nearby, catalog,
        'neutral', _RANGE_CTX, _ADX_RANGE, '15m', vol_note='', micro_dir='bearish',
    )
    assert result is not None
    assert result['direction'] == 'SHORT'


def test_range_scalp_no_target2():
    df = _make_range_df(price=5000.0)
    nearby = [_Level('D_S1', 4999.5)]
    catalog = _Catalog('D_R1', 5020.0)
    result = check_range_scalp(
        '1m', 'bullish', 5000.0, df, nearby, catalog,
        'neutral', _RANGE_CTX, _ADX_RANGE, '15m', vol_note='',
    )
    assert result is not None
    assert result['target2'] is None
    assert result['t2_suppressed'] is True


def test_range_scalp_rr_meets_minimum():
    df = _make_range_df(price=5000.0)
    nearby = [_Level('D_S1', 4999.5)]
    catalog = _Catalog('D_R1', 5020.0)
    result = check_range_scalp(
        '1m', 'bullish', 5000.0, df, nearby, catalog,
        'neutral', _RANGE_CTX, _ADX_RANGE, '15m', vol_note='',
    )
    assert result is not None
    assert result['rr'] >= MIN_RR_SCALP


def test_range_scalp_signal_type():
    df = _make_range_df(price=5000.0)
    nearby = [_Level('D_S1', 4999.5)]
    catalog = _Catalog('D_R1', 5020.0)
    result = check_range_scalp(
        '1m', 'bullish', 5000.0, df, nearby, catalog,
        'neutral', _RANGE_CTX, _ADX_RANGE, '15m', vol_note='',
    )
    assert result is not None
    assert result['signal_type'] == 'range_scalp'


def test_range_scalp_none_no_nearby_levels():
    df = _make_range_df()
    catalog = _Catalog('D_R1', 5020.0)
    result = check_range_scalp(
        '1m', 'bullish', 5000.0, df, [], catalog,
        'neutral', _RANGE_CTX, _ADX_RANGE, '15m', vol_note='',
    )
    assert result is None
