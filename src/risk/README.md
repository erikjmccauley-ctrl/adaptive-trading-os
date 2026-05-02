# src/risk

Risk management layer. The last gate before any signal reaches execution or alert delivery.
Every signal passes through `validate_trade_intent()` before going anywhere.

## What belongs here
- `daily_state/` — LocalRiskEngine + RiskStateStore (JSON-backed, DynamoDB-ready)
- `limits.py` — risk limit constants
- `interfaces/`, `kill_switch/`, `validators/` — placeholder folders for future expansion

## What does NOT belong here
- Signal generation
- Execution logic
- Config loading (use `src/core/config/`)

## Status — COMPLETE (Phase 10)

### Active limits ($250 account)
| Limit | Value | Notes |
|---|---|---|
| Max trades/day | 3 | Hard stop |
| Max daily loss | 5% ($12.50) | Auto-triggers kill switch — enforced when Phase 12 feeds outcomes |
| Max consecutive losses | 3 | Auto-triggers kill switch |
| Min quality score | 0 | Raise to 50 after 30+ live trades justify it |

### Kill switch behavior
- Manual: `engine.trigger_kill_switch(reason)`
- Auto: 3 consecutive losses OR daily loss limit breached
- NOT cleared on date rollover — requires explicit `engine.reset_daily_state()` + manual kill switch clear

### State persistence
`risk/daily_state.json` — auto-created on first run. Designed for DynamoDB swap in Phase 14.

## Note on cooldown persistence
The current `main.py` dedup dict is in-memory and resets on restart. The Lambda has
NO dedup at all. The persistent cooldown store belongs here in `daily_state/` —
DynamoDB table with TTL matching each TF's cooldown window. Deferred to Phase 14.
