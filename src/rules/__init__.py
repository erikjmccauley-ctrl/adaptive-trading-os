from src.rules.rule_engine.engine import RuleEngine
from src.rules.rule_engine.models import Rule
from src.rules.rule_engine.rule_store import RuleStore


def load_rule_engine(
    active_path:    str = 'rules/active_rules.json',
    candidate_path: str = 'rules/candidate_rules.json',
) -> RuleEngine:
    store = RuleStore(active_path, candidate_path)
    return RuleEngine(store)


__all__ = ['RuleEngine', 'Rule', 'RuleStore', 'load_rule_engine']
