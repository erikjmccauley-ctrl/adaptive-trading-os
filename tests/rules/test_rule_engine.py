"""
Unit tests for Phase 9 Rule Engine.
No file I/O — rules are injected directly into RuleEngine._rules.
RuleStore JSON round-trip tests use tmp_path (pytest fixture).
"""
import json
import pytest

from src.rules.rule_engine.models import Rule
from src.rules.rule_engine.evaluator import matches
from src.rules.rule_engine.engine import RuleEngine, _base_score
from src.rules.rule_engine.rule_store import RuleStore


# ── fixtures ──────────────────────────────────────────────────────────────────

def _block_rule(condition='near_level', operator='eq', value='D_FR1', rid='r001'):
    return Rule(id=rid, name=f'Block {value}', status='active',
                action='block', condition=condition, operator=operator, value=value)

def _score_rule(delta=10.0, condition='quality', operator='eq', value='A'):
    return Rule(id='s001', name='Boost A quality', status='active',
                action='score_adjust', condition=condition, operator=operator,
                value=value, score_delta=delta)

def _engine(*rules):
    e = RuleEngine.__new__(RuleEngine)
    e._rules = list(rules)
    return e

def _sig(**kwargs):
    base = {'near_level': 'D_PP', 'entry_tf': '1h', 'signal_type': 'pivot',
            'quality': 'C', 'regime': 'trending', 'rr': 3.0, 'direction': 'LONG'}
    base.update(kwargs)
    return base


# ── evaluator ─────────────────────────────────────────────────────────────────

def test_matches_eq_true():
    rule = _block_rule(value='D_FR1')
    assert matches(rule, _sig(near_level='D_FR1')) is True

def test_matches_eq_false():
    rule = _block_rule(value='D_FR1')
    assert matches(rule, _sig(near_level='D_PP')) is False

def test_matches_neq():
    rule = _block_rule(operator='neq', value='D_PP')
    assert matches(rule, _sig(near_level='D_FR1')) is True
    assert matches(rule, _sig(near_level='D_PP'))  is False

def test_matches_in():
    rule = _block_rule(operator='in', value=['D_FR1', 'D_S2'])
    assert matches(rule, _sig(near_level='D_FR1')) is True
    assert matches(rule, _sig(near_level='D_PP'))  is False

def test_matches_not_in():
    rule = _block_rule(operator='not_in', value=['D_FR1', 'D_S2'])
    assert matches(rule, _sig(near_level='D_PP'))  is True
    assert matches(rule, _sig(near_level='D_FR1')) is False

def test_matches_lt():
    rule = _block_rule(condition='rr', operator='lt', value=2.0)
    assert matches(rule, _sig(rr=1.5)) is True
    assert matches(rule, _sig(rr=2.5)) is False

def test_matches_gt():
    rule = _block_rule(condition='rr', operator='gt', value=5.0)
    assert matches(rule, _sig(rr=6.0)) is True
    assert matches(rule, _sig(rr=4.0)) is False

def test_matches_missing_field_returns_false():
    rule = _block_rule(condition='nonexistent_field')
    assert matches(rule, _sig()) is False


# ── evaluate ──────────────────────────────────────────────────────────────────

def test_block_rule_blocks_matching_signal():
    engine = _engine(_block_rule(value='D_FR1'))
    passed, reason = engine.evaluate(_sig(near_level='D_FR1'))
    assert passed is False
    assert 'r001' in reason

def test_block_rule_passes_non_matching_signal():
    engine = _engine(_block_rule(value='D_FR1'))
    passed, reason = engine.evaluate(_sig(near_level='D_PP'))
    assert passed is True
    assert reason == ''

def test_evaluate_no_rules_passes_everything():
    engine = _engine()
    passed, _ = engine.evaluate(_sig(near_level='D_FR1'))
    assert passed is True

def test_evaluate_multiple_block_rules():
    engine = _engine(
        _block_rule(value='D_FR1', rid='r001'),
        _block_rule(value='D_S2',  rid='r002'),
    )
    assert engine.evaluate(_sig(near_level='D_FR1'))[0] is False
    assert engine.evaluate(_sig(near_level='D_S2'))[0]  is False
    assert engine.evaluate(_sig(near_level='D_PP'))[0]  is True


# ── score ─────────────────────────────────────────────────────────────────────

def test_score_quality_a_higher_than_c():
    engine = _engine()
    a_score = engine.score(_sig(quality='A'))
    c_score = engine.score(_sig(quality='C'))
    assert a_score > c_score

def test_score_bounds():
    engine = _engine()
    for q in ('A', 'B', 'C'):
        for regime in ('trending', 'neutral', 'ranging'):
            for tf in ('1m', '5m', '15m', '1h', '4h', '1d'):
                s = engine.score(_sig(quality=q, regime=regime, entry_tf=tf))
                assert 0 <= s <= 100, f'score {s} out of bounds for {q}/{regime}/{tf}'

def test_score_adjust_rule_applied():
    # Use C/ranging/scalp/1m so base ≈ 25, well below cap
    engine = _engine(_score_rule(delta=20.0, condition='quality', operator='eq', value='C'))
    base   = _engine()
    sig    = _sig(quality='C', regime='ranging', signal_type='range_scalp', entry_tf='1m')
    assert engine.score(sig) == base.score(sig) + 20

def test_score_adjust_does_not_block():
    engine = _engine(_score_rule(delta=-50.0, condition='quality', operator='eq', value='C'))
    passed, _ = engine.evaluate(_sig(quality='C'))
    assert passed is True  # score_adjust never blocks

def test_score_floor_zero():
    # Large negative delta should not push score below 0
    engine = _engine(_score_rule(delta=-9999.0, condition='quality', operator='eq', value='C'))
    assert engine.score(_sig(quality='C')) == 0


# ── rule store (uses tmp files) ───────────────────────────────────────────────

def _write_json(path, data):
    path.write_text(json.dumps(data, indent=2))

def test_rule_store_load_active(tmp_path):
    active = tmp_path / 'active.json'
    cand   = tmp_path / 'cand.json'
    _write_json(active, [
        {'id': 'r001', 'name': 'Block D_FR1', 'status': 'active', 'action': 'block',
         'condition': 'near_level', 'operator': 'eq', 'value': 'D_FR1',
         'score_delta': 0.0, 'source': 'inference', 'min_trades': 0, 'note': '', 'created': ''},
    ])
    _write_json(cand, [])
    store = RuleStore(str(active), str(cand))
    rules = store.load_active()
    assert len(rules) == 1
    assert rules[0].id == 'r001'
    assert rules[0].action == 'block'

def test_rule_store_promote(tmp_path):
    active = tmp_path / 'active.json'
    cand   = tmp_path / 'cand.json'
    _write_json(active, [])
    _write_json(cand, [
        {'id': 'c001', 'name': 'Watch W_FR1', 'status': 'candidate', 'action': 'block',
         'condition': 'near_level', 'operator': 'eq', 'value': 'W_FR1',
         'score_delta': 0.0, 'source': 'inference', 'min_trades': 0, 'note': '', 'created': ''},
    ])
    store = RuleStore(str(active), str(cand))
    store.promote('c001')
    active_rules = store.load_active()
    assert len(active_rules) == 1
    assert active_rules[0].id == 'c001'
    assert active_rules[0].status == 'active'
    remaining_cands = store.load_candidates()
    assert len(remaining_cands) == 0

def test_rule_store_retire(tmp_path):
    active = tmp_path / 'active.json'
    cand   = tmp_path / 'cand.json'
    _write_json(active, [
        {'id': 'r001', 'name': 'Block D_FR1', 'status': 'active', 'action': 'block',
         'condition': 'near_level', 'operator': 'eq', 'value': 'D_FR1',
         'score_delta': 0.0, 'source': 'inference', 'min_trades': 0, 'note': '', 'created': ''},
    ])
    _write_json(cand, [])
    store = RuleStore(str(active), str(cand))
    store.retire('r001')
    assert len(store.load_active()) == 0
