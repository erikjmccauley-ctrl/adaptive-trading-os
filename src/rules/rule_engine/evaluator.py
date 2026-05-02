from src.rules.rule_engine.models import Rule


def matches(rule: Rule, signal: dict) -> bool:
    val = signal.get(rule.condition)
    if val is None:
        return False
    op = rule.operator
    rv = rule.value
    if op == 'eq':      return val == rv
    if op == 'neq':     return val != rv
    if op == 'in':      return val in rv
    if op == 'not_in':  return val not in rv
    try:
        if op == 'lt':  return float(val) < float(rv)
        if op == 'gt':  return float(val) > float(rv)
    except (TypeError, ValueError):
        return False
    return False
