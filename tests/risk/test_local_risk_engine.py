"""
Unit tests for Phase 10 LocalRiskEngine.
No real file I/O — RiskStateStore backed by tmp_path.
"""
import json
from datetime import date, timedelta

import pytest

from src.risk.daily_state.state_store import RiskStateStore
from src.risk.daily_state.local_risk_engine import LocalRiskEngine
from src.risk.limits import MAX_TRADES_PER_DAY, MAX_CONSECUTIVE_LOSSES


# ── helpers ───────────────────────────────────────────────────────────────────

def _engine(tmp_path, state_dict=None):
    p = tmp_path / 'daily_state.json'
    if state_dict is not None:
        p.write_text(json.dumps(state_dict))
    store = RiskStateStore(str(p))
    return LocalRiskEngine(store)

def _fresh_state(tmp_path, **overrides):
    base = {
        'date': str(date.today()),
        'trades_taken': 0,
        'daily_pnl': 0.0,
        'consecutive_losses': 0,
        'kill_switch_active': False,
        'kill_switch_reason': '',
    }
    base.update(overrides)
    return _engine(tmp_path, base)

def _sig(**kwargs):
    base = {'quality_score': 75, 'entry_tf': '1h', 'direction': 'LONG'}
    base.update(kwargs)
    return base


# ── validate_trade_intent ─────────────────────────────────────────────────────

def test_validate_passes_clean_state(tmp_path):
    engine = _fresh_state(tmp_path)
    allowed, reason = engine.validate_trade_intent(_sig())
    assert allowed is True
    assert reason == ''

def test_validate_blocks_kill_switch(tmp_path):
    engine = _fresh_state(tmp_path, kill_switch_active=True, kill_switch_reason='Test halt')
    allowed, reason = engine.validate_trade_intent(_sig())
    assert allowed is False
    assert 'Kill switch' in reason

def test_validate_blocks_trade_limit(tmp_path):
    engine = _fresh_state(tmp_path, trades_taken=MAX_TRADES_PER_DAY)
    allowed, reason = engine.validate_trade_intent(_sig())
    assert allowed is False
    assert 'Daily trade limit' in reason

def test_validate_passes_one_below_limit(tmp_path):
    engine = _fresh_state(tmp_path, trades_taken=MAX_TRADES_PER_DAY - 1)
    allowed, _ = engine.validate_trade_intent(_sig())
    assert allowed is True


# ── trigger_kill_switch ───────────────────────────────────────────────────────

def test_trigger_kill_switch(tmp_path):
    engine = _fresh_state(tmp_path)
    engine.trigger_kill_switch('Manual halt by operator')
    assert engine.is_kill_switch_active() is True
    state = engine.get_daily_state()
    assert state.kill_switch_reason == 'Manual halt by operator'

def test_kill_switch_persists_after_reload(tmp_path):
    p = tmp_path / 'daily_state.json'
    store = RiskStateStore(str(p))
    e1 = LocalRiskEngine(store)
    e1.trigger_kill_switch('Test persistence')
    e2 = LocalRiskEngine(RiskStateStore(str(p)))
    assert e2.is_kill_switch_active() is True


# ── reset_daily_state ─────────────────────────────────────────────────────────

def test_reset_clears_trades_not_kill_switch(tmp_path):
    engine = _fresh_state(tmp_path, trades_taken=3, daily_pnl=-15.0,
                          consecutive_losses=2, kill_switch_active=True,
                          kill_switch_reason='Auto: limit')
    engine.reset_daily_state()
    state = engine.get_daily_state()
    assert state.trades_taken == 0
    assert state.daily_pnl == 0.0
    assert state.consecutive_losses == 0
    assert state.kill_switch_active is True  # NOT cleared by reset
    assert state.kill_switch_reason == 'Auto: limit'


# ── update_daily_state (auto kill switch) ────────────────────────────────────

def test_update_auto_triggers_on_consecutive_losses(tmp_path):
    engine = _fresh_state(tmp_path, consecutive_losses=MAX_CONSECUTIVE_LOSSES - 1)
    engine.update_daily_state({'result': 'LOSS', 'pnl_dollars': -5.0})
    assert engine.is_kill_switch_active() is True
    assert 'consecutive losses' in engine.get_daily_state().kill_switch_reason

def test_update_resets_consecutive_on_win(tmp_path):
    engine = _fresh_state(tmp_path, consecutive_losses=2)
    engine.update_daily_state({'result': 'WIN', 'pnl_dollars': 10.0})
    state = engine.get_daily_state()
    assert state.consecutive_losses == 0
    assert state.kill_switch_active is False


# ── date rollover ─────────────────────────────────────────────────────────────

def test_date_rollover_resets_trades(tmp_path):
    yesterday = str(date.today() - timedelta(days=1))
    engine = _engine(tmp_path, {
        'date': yesterday,
        'trades_taken': 3,
        'daily_pnl': -20.0,
        'consecutive_losses': 2,
        'kill_switch_active': False,
        'kill_switch_reason': '',
    })
    state = engine.get_daily_state()
    assert state.date == str(date.today())
    assert state.trades_taken == 0
    assert state.daily_pnl == 0.0
    assert state.consecutive_losses == 0

def test_date_rollover_preserves_kill_switch(tmp_path):
    yesterday = str(date.today() - timedelta(days=1))
    engine = _engine(tmp_path, {
        'date': yesterday,
        'trades_taken': 3,
        'daily_pnl': -20.0,
        'consecutive_losses': 3,
        'kill_switch_active': True,
        'kill_switch_reason': 'Auto: 3 consecutive losses',
    })
    state = engine.get_daily_state()
    assert state.kill_switch_active is True
