# src/rules

The rule engine. Evaluates candidate signals against active rules and scores/blocks them.
Rules are data-driven — stored in DynamoDB, not hardcoded.

## What belongs here
- `rule_engine/` — evaluate_signal(), score_signal(), block_signal()
- `active_rules/` — current live rules (loaded from DynamoDB or local JSON)
- `candidate_rules/` — rules in testing / promotion queue
- `promotion/` — logic to promote a candidate rule to active after N trades + threshold
- `versioning/` — rule version history and rollback

## What does NOT belong here
- Signal generation (goes in `src/signals/`)
- Risk management (goes in `src/risk/`)
- Hardcoded trading thresholds that should be in config

## Status — COMPLETE (Phase 9)

## Related TODOs
- Phase 9: Define candidate and active rule schemas
- Phase 9: Implement rule_engine.evaluate_signal()
- Phase 9: Add rule promotion / retirement logic

## Design note
In the current `src/signals.py`, rule gates (volume filter, ADX routing, ATR block,
R/R minimum) are hardcoded in the signal functions. In the OS, these move here as
data-driven rules that can be adjusted by the inference engine without code changes.
