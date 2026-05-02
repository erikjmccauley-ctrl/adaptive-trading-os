from __future__ import annotations
import json
import os
from src.rules.rule_engine.models import Rule


def _load_rules(path: str) -> list[Rule]:
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [Rule(**r) for r in data]


def _save_rules(path: str, rules: list[Rule]) -> None:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    rows = [r.__dict__ for r in rules]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2)


class RuleStore:
    def __init__(self,
                 active_path:    str = 'rules/active_rules.json',
                 candidate_path: str = 'rules/candidate_rules.json'):
        self._active_path    = active_path
        self._candidate_path = candidate_path

    def load_active(self) -> list[Rule]:
        return [r for r in _load_rules(self._active_path) if r.status == 'active']

    def load_candidates(self) -> list[Rule]:
        return [r for r in _load_rules(self._candidate_path) if r.status == 'candidate']

    def save_active(self, rules: list[Rule]) -> None:
        _save_rules(self._active_path, rules)

    def promote(self, rule_id: str) -> None:
        """Move a rule from candidate_rules.json → active_rules.json."""
        candidates = _load_rules(self._candidate_path)
        target = next((r for r in candidates if r.id == rule_id), None)
        if target is None:
            raise ValueError(f"Rule '{rule_id}' not found in candidate rules")
        target.status = 'active'
        remaining = [r for r in candidates if r.id != rule_id]
        _save_rules(self._candidate_path, remaining)
        active = _load_rules(self._active_path)
        active.append(target)
        _save_rules(self._active_path, active)

    def retire(self, rule_id: str) -> None:
        """Remove a rule from active_rules.json and mark it retired."""
        active = _load_rules(self._active_path)
        target = next((r for r in active if r.id == rule_id), None)
        if target is None:
            raise ValueError(f"Rule '{rule_id}' not found in active rules")
        target.status = 'retired'
        remaining = [r for r in active if r.id != rule_id]
        _save_rules(self._active_path, remaining)
