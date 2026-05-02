from src.rules.rule_engine.models import Rule
from src.rules.rule_engine.rule_store import RuleStore
from src.rules.rule_engine.evaluator import matches

_QUALITY_SCORE = {'A': 25, 'B': 10, 'C': 0}
_REGIME_SCORE  = {'trending': 15, 'neutral': 5, 'ranging': 0}
_TYPE_SCORE    = {'pullback': 10, 'pivot': 0, 'range_scalp': -5}
_TF_SCORE      = {'1d': 15, '4h': 15, '1h': 10, '15m': 0, '5m': -5, '1m': -10}
_BASE           = 40


def _base_score(signal: dict) -> int:
    return (
        _BASE
        + _QUALITY_SCORE.get(signal.get('quality', 'C'), 0)
        + _REGIME_SCORE.get(signal.get('regime', 'neutral'), 0)
        + _TYPE_SCORE.get(signal.get('signal_type', 'pivot'), 0)
        + _TF_SCORE.get(signal.get('entry_tf', '15m'), 0)
    )


class RuleEngine:
    def __init__(self, store: RuleStore):
        self._rules: list[Rule] = store.load_active()

    def evaluate(self, signal: dict) -> tuple[bool, str]:
        """
        Returns (passed, reason).
        passed=False means the signal is blocked — do not deliver.
        """
        for rule in self._rules:
            if rule.action == 'block' and matches(rule, signal):
                return False, f'[{rule.id}] {rule.name}'
        return True, ''

    def score(self, signal: dict) -> int:
        """
        Returns quality_score 0–100. Used by Phase 11 for signal prioritization.
        """
        s = _base_score(signal)
        for rule in self._rules:
            if rule.action == 'score_adjust' and matches(rule, signal):
                s += int(rule.score_delta)
        return max(0, min(100, s))
