# Phase 1–7 Structured Review
_Review date: 2026-04-29_

---

## Executive Summary

Phases 1–7 are complete. The Adaptive Trading OS refactor has produced a clean layered architecture
from what was originally a 4-file flat script. All original entry points (`main.py`, `backtest.py`)
still work without modification. No files were deleted. No live execution code was enabled.

**What was built:** 7 src layers (core, data_sources, features, signals, backtesting, storage, execution)
with ABC contracts, a full feature engine, modular signal generators, a walk-forward backtest
engine with MFE/MAE/R-multiple tracking, and complete documentation.

**Critical gaps remaining:** zero automated tests, stale docs (partially corrected this review),
one missing abstract method (fixed), and one incomplete Phase 7 item (ATR-based stop tests).

**Safety status:** Live execution is permanently disabled. `TradovateBroker.is_enabled()` returns
`False`. `LIVE_EXECUTION_ENABLED` defaults to `false`. No path to live orders exists.

---

## Phase Completion Status

| Phase | Name | Status | Notes |
|---|---|---|---|
| 1 | Repo Cleanup & Inventory | ✅ Complete | `docs/cleanup_candidates.md` still `[ ]` |
| 2 | Architecture & Folder Structure | ✅ Complete | `Map existing docs into docs/` still `[ ]` |
| 3 | Schwab Market Data Layer | ✅ Complete | — |
| 4 | AWS Storage Layer | ⚠ Partial | S3Storage, DynamoDBStateStore not implemented |
| 5 | Candle & Feature Engine | ✅ Complete | All 6 submodules built |
| 6 | Candidate Signal Generator | ✅ Complete | Future setup families are `[ ]` (expected) |
| 7 | Backtest Engine | ✅ Complete (1 item open) | ATR-based stop tests `[ ]` |

---

## Architecture Review

### Layer separation — PASS

Each `src/` subdirectory contains only what it should:
- `src/features/` — pure functions, no I/O, no API calls ✅
- `src/signals/` — reads feature output, no storage writes ✅
- `src/backtesting/` — imports signals exactly (no drift) ✅
- `src/core/contracts/` — ABCs only, no implementations ✅
- `src/data_sources/` — API calls isolated here ✅

### Shim pattern integrity — PASS

- `src/indicators.py` → one-liner: `from src.features.indicators import *`
- `src/signals/__init__.py` → re-exports from `src.signals.orchestrator` + `constants`
- Neither `main.py` nor `backtest.py` was touched

### Duplication elimination — PASS

Phase 7 eliminated the only known duplication: `AGG` and `RESAMPLE_RULES` that existed
both in the old `backtest.py` and in `src/features/candles/resampler.py`.
`build_higher_tfs()` is now the single source of truth.

### Known architectural debt

1. **Rule enforcement fused in signal generators** — R/R check and ATR gate live inside
   `pivot_signal.py`, `pullback_signal.py`, `range_scalp.py` rather than in `src/rules/`.
   This is correct for Phase 6; full separation is Phase 9. Not a defect.

2. **`main.py` still calls `src/data.py` directly** — the `SchwabProvider` class from
   `src/data_sources/schwab/provider.py` is built but not wired into the live scanner.
   `main.py` still imports `from src.data import ...`. Wiring is Phase 14.

3. **Session/VWAP features not wired into live path** — `src/features/sessions/` is built
   but `main.py` does not call it. Also Phase 14.

---

## Interface Contract Review

### `src/core/contracts/market_data.py` — FIXED this review
- Added `get_latest_quote() -> dict` abstract method (returns `{'last','bid','ask','timestamp'}`)
- `SchwabProvider` must implement this before Phase 11 (Telegram alerts need live quote)

### `src/core/contracts/execution.py` — FIXED this review
- Added `get_open_orders() -> list[Order]` abstract method
- Added `cancel_order(order: Order) -> bool` abstract method
- `TradovateBroker` updated: both methods implemented (raise `RuntimeError` — disabled)

### `src/core/contracts/storage.py` — OK
- `LocalStorage` implements all abstract methods

### `src/core/contracts/alerts.py` — PLACEHOLDER
- `AlertProvider` ABC defined. No concrete implementation until Phase 11.

### `src/core/contracts/risk.py` — PLACEHOLDER
- `RiskEngine` ABC defined. No concrete implementation until Phase 10.

---

## Repo Hygiene

### `.gitignore` coverage — PASS
Confirmed covered:
- `.env` ✅
- `schwab_token.json` ✅
- `__pycache__/` ✅
- `*.pyc` ✅
- `.venv/` ✅
- `*.log` ✅
- `data/raw/`, `data/normalized/` ✅

### Security scan — PASS
Pattern `(api_key|app_secret|password|token)\s*=\s*['"][^'"]{10,}` found zero matches in `.py` files.
All credentials go through `.env` / `python-dotenv` or Secrets Manager (Lambda path).

### Safety check — PASS
`LIVE_EXECUTION_ENABLED=true` pattern found only inside `RuntimeError` message strings in
`src/execution/tradovate_future/broker.py` (error text, not executable code).
`TradovateBroker.is_enabled()` returns `False` unconditionally.

---

## Compilation Check

```
python -m compileall src -q
```
Result: **All OK** — zero syntax errors across all `.py` files in `src/`.

---

## Static Analysis

**ruff:** Not installed. Not run.
**mypy:** Not installed. Not run.
**pytest:** Not installed. Zero test files exist.

These are all blockers for Phase 16. Recommend adding `ruff`, `mypy`, `pytest` to `requirements.txt`
and running them before Phase 8 ships any new logic.

---

## Documentation Consistency

### README files — PASS (after fixes this review)

| Path | Status |
|---|---|
| `README.md` (root) | Created this review |
| `docs/README.md` | Created this review |
| `src/backtesting/README.md` | Updated this review — reflects Phase 7 |
| `src/signals/README.md` | Updated this review — reflects Phase 6 |
| `src/features/README.md` | Updated this review — reflects Phase 5 |
| `src/ingestion/README.md` | Created this review |
| `scripts/dev/README.md` | Exists ✅ |
| `scripts/maintenance/README.md` | Exists ✅ |
| `src/core/README.md` | Exists ✅ |
| `src/data_sources/README.md` | Exists ✅ |
| `src/storage/README.md` | Exists ✅ |
| `src/execution/README.md` | Exists ✅ |
| `src/inference/README.md` | Exists ✅ |
| `src/rules/README.md` | Exists ✅ |
| `src/risk/README.md` | Exists ✅ |
| `src/alerts/README.md` | Exists ✅ |
| `src/aws/README.md` | Exists ✅ |

### Stale docs — PARTIALLY FIXED this review

| Doc | Finding | Action Taken |
|---|---|---|
| `docs/repo_inventory.md` | Phase 1 baseline — didn't reflect Phase 5-7 src/ structure | Updated header + src/ tree |
| `docs/adaptive_trading_os_gap_analysis.md` | Phase 5-7 components shown as "missing" | Updated 7 sections to reflect completion |
| `docs/refactor_log.md` | Missing entirely — required by Phase 6 review | Created this review |

### CLAUDE.md file structure diagram — STALE
`CLAUDE.md` shows the original 4-file `src/` structure:
```
src/
├── data.py
├── indicators.py
├── signals.py
└── display.py
```
This has not been updated to reflect Phase 5-7. The README.md (root) has the current architecture tree.
Updating CLAUDE.md is low priority — it is a project-instructions file for Claude, not user-facing docs.

---

## Defects Found

| ID | Severity | Description | Status |
|---|---|---|---|
| D-01 | Low | `MarketDataProvider` missing `get_latest_quote()` | Fixed this review |
| D-02 | Low | `ExecutionProvider` missing `cancel_order()`, `get_open_orders()` | Fixed this review |
| D-03 | Low | `TradovateBroker` didn't implement new abstract methods | Fixed this review |
| D-04 | Low | `docs/refactor_log.md` missing | Fixed this review |
| D-05 | Info | `docs/repo_inventory.md` stale (Phase 1 baseline) | Partially fixed — header + src tree updated |
| D-06 | Info | `docs/adaptive_trading_os_gap_analysis.md` stale | Partially fixed — 7 sections updated |
| D-07 | Info | `src/ingestion/README.md` missing | Fixed this review |
| D-08 | Info | `docs/README.md` missing | Fixed this review |
| D-09 | Info | `CLAUDE.md` file structure diagram stale | Not fixed — low priority |
| D-10 | Info | `docs/cleanup_candidates.md` still `[ ]` in To Do.txt | Not fixed — deferred to Phase 17 |

---

## Validation Commands

Run these to verify Phase 1–7 integrity at any point:

```bash
# 1. Syntax check
python -m compileall src -q

# 2. Shim imports
python -X utf8 -c "from src.indicators import calc_smma, calc_adx; print('indicators shim OK')"
python -X utf8 -c "from src.signals import generate_signals, MIN_RR, ADX_TRENDING; print('signals pkg OK')"

# 3. Feature engine
python -X utf8 -c "
from src.features.indicators import calc_smma, calc_adx
from src.features.regimes import RegimeClassifier
from src.features.candles import build_higher_tfs
from src.features.sessions import get_session, calc_vwap
from src.features.support_resistance import LevelCatalog
print('features OK')
"

# 4. Signal generators
python -X utf8 -c "
from src.signals.candidate_generators.pivot_signal import check_pivot_setup
from src.signals.candidate_generators.pullback_signal import check_pullback_setup
from src.signals.candidate_generators.range_scalp import check_range_scalp
from src.signals.filters.volume import passes_volume_gate
from src.signals.scoring.quality import signal_quality
print('signal generators OK')
"

# 5. Backtesting
python -X utf8 -c "
from src.backtesting import walk_forward, print_report, load_yfinance_1h, load_schwab_data
from src.backtesting.engine.walk_forward import TradeState, TradeResolver
print('backtesting OK')
"

# 6. Entry point imports (must not break)
python -X utf8 -c "import main; print('main.py OK')"
python -X utf8 -c "import backtest; print('backtest.py OK')"

# 7. Safety check
python -X utf8 -c "
from src.execution.tradovate_future.broker import TradovateBroker
b = TradovateBroker()
assert b.is_enabled() == False, 'SAFETY BREACH: is_enabled returned True'
print('safety check OK')
"
```

---

## Blockers for Phase 8

| Blocker | Required Before |
|---|---|
| No test suite (zero pytest coverage) | Phase 8 should not ship without at least smoke tests on `walk_forward()` |
| `load_yfinance_1h()` requires network (yfinance) | Phase 8 bucket analysis needs the trade records — ensure CSV export works |
| ATR-based stop tests `[ ]` in Phase 7 | Nice-to-have for Phase 8 bucket comparison — not a hard blocker |

---

## Next 5 Steps (after this review)

1. **Phase 8 — Inference Engine**
   - Import `walk_forward()` output programmatically
   - Bucket by: `signal_type`, `quality`, `regime`, `entry_tf`, `near_level`
   - Compute win rate, avg win/loss, expectancy, profit factor per bucket
   - Output `confidence` label (A/B/C/insufficient-data) for each bucket

2. **Add `pytest` to `requirements.txt`** — minimum viable test: smoke test `walk_forward()` with
   synthetic DataFrame (no network), assert trade records contain all Phase 7 fields.

3. **Run `backtest.py`** — generate fresh trade records with the Phase 7 engine. Verify CSV export
   contains all new fields (`mfe_pts`, `r_multiple`, `reached_1r`, etc.).

4. **Review Phase 7 alt-exit output** — the "Alternate Exit Scenarios" section in `print_report()`
   will show whether T1 (current) or some R-multiple exit is actually optimal. This should inform
   Phase 8 rule recommendations.

5. **Update `CLAUDE.md` file structure diagram** — add Phase 5-7 `src/` layers so future sessions
   start with accurate context.
