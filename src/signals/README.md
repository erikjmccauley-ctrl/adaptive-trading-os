# src/signals

Candidate signal generation. Reads feature output, produces signal dicts.
Does NOT enforce rules or risk gates — that is the rule engine's job.

## What belongs here
- `constants.py` — all strategy constants (MIN_RR, ADX thresholds, TF maps, etc.)
- `orchestrator.py` — `generate_signals()` entry point wiring all generators together
- `candidate_generators/` — one file per setup family:
  - `pivot_signal.py` — at-level pivot bounce signal
  - `pullback_signal.py` — SMMA21 pullback trend continuation
  - `range_scalp.py` — pivot-to-pivot scalp in ranging markets
  - Future: breakout_retest, vwap_reclaim, opening_range_breakout, volatility_expansion
- `scoring/` — `signal_quality()`: A/B/C tier from price action components
- `filters/` — `passes_volume_gate()`, `passes_volume_direction_gate()`, `volume_direction_note()`

## What does NOT belong here
- Rule enforcement (goes in `src/rules/rule_engine/`)
- Risk validation (goes in `src/risk/`)
- Data fetching or storage

## Status — COMPLETE (Phase 6)
All signal logic extracted from the monolithic `src/_signals_legacy.py`:
- `src/_signals_legacy.py` preserved as read-only fallback (removed in Phase 17)
- `src/signals/__init__.py` re-exports public API — zero changes to `main.py` or `backtest.py`
- `RegimeClassifier` (Phase 5) and `LevelCatalog` (Phase 5) now wired into the orchestrator

## Public API (backward compatible)
```python
from src.signals import generate_signals, CONFIRMATION_MAP, MIN_RR, ADX_TRENDING, ...
```
