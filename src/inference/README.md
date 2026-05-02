# src/inference

Inference engine. Analyzes resolved trade outcomes and surfaces confidence grades and rule
recommendations. This is the "adaptive" in Adaptive Trading OS.

## What belongs here
- `bucket_analysis/` — `BucketEngine`, `BucketResult`: group trades by any dimension combination,
  compute win rate / expectancy / profit factor per bucket
- `expectancy/` — `compute_stats()`: pure function, takes a list of trade dicts, returns stat dict
- `confidence/` — `assign_confidence(n, win_rate, profit_factor) -> str`: A / B / C / insufficient-data
- `rule_recommendations/` — `generate_recommendations()`: surface AVOID / KEEP / WATCH signals

## What does NOT belong here
- Signal generation
- Trade execution
- Rule enforcement (goes in `src/rules/`)
- Auto-promotion of rules (goes in `src/rules/promotion/`)

## Status — COMPLETE (Phase 8)

## Public API
```python
from src.inference import run_inference, BucketEngine, BucketResult

# Programmatic — pass trades from walk_forward()
trades = walk_forward(data, '1h')
df = run_inference(trades=trades)

# CLI / CSV path
df = run_inference(csv_paths=['backtest_yf_1h.csv', 'backtest_schwab_15m.csv'])

# Default — loads all backtest_*.csv in cwd
df = run_inference()
```

## Confidence thresholds
| Label | Condition |
|---|---|
| `A` | n ≥ 30, WR ≥ 45%, PF ≥ 2.0 |
| `B` | n ≥ 10, WR ≥ 35%, PF ≥ 1.0 |
| `C` | n ≥ 10, below B thresholds |
| `insufficient-data` | n < 10 |

## Design intent
The inference engine does not change rules automatically. It surfaces recommendations.
A human (or Phase 9 rule engine) decides whether to promote a candidate rule to active.
