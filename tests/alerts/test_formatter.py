"""
Unit tests for format_signal_card().
No network calls — formatter is a pure function.
"""
from dataclasses import dataclass
from src.alerts.formatters.signal_card import format_signal_card
from src.core.contracts.risk_engine import DailyRiskState


# ── helpers ───────────────────────────────────────────────────────────────────

@dataclass
class FakeBucket:
    n: int
    wins: int
    win_rate: float
    profit_factor: float | None
    confidence: str
    key: dict


def _sig(**overrides):
    base = {
        'direction': 'LONG', 'entry_tf': '5m', 'tf_label': '5m (scalp)',
        'display_tfs': ['15m', '1h', '1d'],
        'entry': 5248.50, 'stop': 5241.25,
        'target1': 5312.50, 'target1_name': 'D_R2',
        'target2': 5336.75, 'target2_name': 'W_R1',
        'near_level': 'D_R2',
        'risk_per_contract': 36.25, 'reward_per_contract': 320.00,
        'reward2_per_contract': 441.25,
        'rr': 14.3,
        'tf_align': {'15m': 'bullish', '1h': 'bullish', '1d': 'bullish'},
        'reason': 'Pullback to SMMA21 held', 'signal_type': 'pullback',
        'hold_condition': None,
        'quality': 'B', 'quality_score': 75, 'quality_detail': 'Trend continuation',
        'regime': 'trending', 'adx': 31.2, 'adx_tf': '1h',
        'daily_consumed_pct': 52, 't2_suppressed': False,
    }
    base.update(overrides)
    return base


def _risk(trades_taken=1, daily_pnl=0.0, kill_switch_active=False):
    return DailyRiskState(
        date='2026-04-30', trades_taken=trades_taken, daily_pnl=daily_pnl,
        consecutive_losses=0, kill_switch_active=kill_switch_active,
    )


def _bucket(n=12, wins=7, wr=0.583, pf=2.1, conf='B'):
    return FakeBucket(n=n, wins=wins, win_rate=wr, profit_factor=pf,
                      confidence=conf, key={'near_level': 'D_R2', 'regime': 'trending'})


# ── tests ─────────────────────────────────────────────────────────────────────

def test_long_signal_card():
    card = format_signal_card(_sig(), risk_state=_risk(), bucket_stats=_bucket())
    assert '🟢' in card
    assert 'LONG MES' in card
    assert 'B · 75' in card
    assert 'PULLBACK' in card
    assert '5,248.50' in card
    assert 'T1:' in card
    assert 'T2:' in card
    assert 'TRENDING' in card
    assert 'D_R2' in card
    assert '58% WR' in card
    assert 'Trades left:' in card


def test_short_range_scalp_card():
    card = format_signal_card(_sig(
        direction='SHORT', signal_type='range_scalp',
        target2=None, target2_name=None, reward2_per_contract=None,
        tf_align={'5m': 'neutral', '15m': 'neutral', '1h': 'neutral'},
        display_tfs=['5m', '15m', '1h'], regime='ranging',
    ))
    assert '🔴' in card
    assert 'SHORT MES' in card
    assert 'RANGE SCALP' in card
    assert 'T2:' not in card
    assert 'SCALP' in card


def test_no_bucket_stats():
    card = format_signal_card(_sig(), bucket_stats=None)
    assert '📊' not in card


def test_insufficient_bucket():
    card = format_signal_card(_sig(), bucket_stats=_bucket(n=3, wins=1))
    assert 'insufficient data' in card
    assert 'n=3' in card


def test_no_risk_state():
    card = format_signal_card(_sig(), risk_state=None)
    assert 'Trades left:' not in card
    assert '⏱' in card  # timestamp line still present


def test_pullback_hold_condition():
    hold = 'Hold while 5m closes above SMMA21 (5,241.00)'
    card = format_signal_card(_sig(hold_condition=hold))
    assert 'Hold:' in card
    assert 'SMMA21' in card


def test_kill_switch_shown_in_card():
    card = format_signal_card(_sig(), risk_state=_risk(kill_switch_active=True))
    assert 'KILL SWITCH' in card
