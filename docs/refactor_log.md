---
name: refactor_log
description: Documents all structural changes made during each phase — what moved, what was shimmed, and what was left in place.
---

# Refactor Log
_Last updated: 2026-04-30 (Phase 17 complete + Lambda sync to parity)_

---

## Approach

All phases used a **shim-and-copy** pattern rather than moving files. The original files are preserved
as shims that re-export from the new locations. This ensures:
- Zero changes to `main.py`, `backtest.py`, or any caller
- Any import that worked before still works exactly as before
- The legacy code is available as a fallback until Phase 17 cleanup

The shim pattern means: no files were moved or renamed. Originals are still present, still importable,
and still the source of truth for the live bot today.

---

## Phase 1 — Repo Cleanup & Inventory
**Files moved:** None.
**Files created:** `docs/repo_inventory.md`, `docs/adaptive_trading_os_gap_analysis.md`,
`docs/folder_architecture_plan.md`, `docs/security_findings.md`, `.gitignore`, `To Do.txt`.
**Risk:** None.

---

## Phase 2 — Architecture & Folder Structure
**Files moved:** None.
**Files created:** Full `src/` scaffold — all `__init__.py` placeholders, `README.md` files,
`.env.example`, `pyproject.toml`, `src/core/config/`, `src/core/contracts/`.
**Risk:** None — all new empty files.

---

## Phase 3 — Schwab Market Data Layer
**Files moved:** None.
**Shim created:** `src/data_sources/schwab/provider.py` wraps existing `src/data.py` logic in a
`SchwabProvider` class implementing `MarketDataProvider`.
**Original preserved:** `src/data.py` — still the active data source for `main.py`.
**Risk:** Low. `src/data.py` is untouched.

---

## Phase 4 — AWS Storage Layer
**Files moved:** None.
**Files created:** `src/storage/local/local_storage.py` implementing `StorageProvider`.
S3 and DynamoDB adapters are placeholders only — not implemented.
**Risk:** None.

---

## Phase 5 — Candle & Feature Engine
**Files moved:** None.
**What was done:**
- `src/features/indicators/indicators.py` — indicator logic copied from `src/indicators.py`
- `src/indicators.py` converted to a one-line shim: `from src.features.indicators import *`
- `src/features/regimes/regime_classifier.py` — `RegimeClassifier` extracted from signal logic
- `src/features/candles/resampler.py` — `resample()`, `build_higher_tfs()`, `AGG`, `RESAMPLE_RULES`
- `src/features/sessions/session_labels.py` — `get_session()`, `is_rth()`, `calc_vwap()`, etc.
- `src/features/support_resistance/level_catalog.py` — `LevelCatalog`, `PivotLevel`

**Original preserved:** `src/indicators.py` is now a shim. Still importable as `from src.indicators import *`.
Removal scheduled for Phase 17.

**Import verification at Phase 5 complete:**
```
python -X utf8 -c "from src.indicators import calc_smma, calc_adx; print('shim OK')"
python -X utf8 -c "from src.features.indicators import calc_smma; print('direct OK')"
python -X utf8 -c "from src.features.regimes import RegimeClassifier; print('regimes OK')"
python -X utf8 -c "from src.features.candles import build_higher_tfs; print('candles OK')"
python -X utf8 -c "from src.features.sessions import get_session; print('sessions OK')"
python -X utf8 -c "from src.features.support_resistance import LevelCatalog; print('SR OK')"
```

**Risk:** Low. `src/indicators.py` shim preserves all existing imports.

---

## Phase 6 — Candidate Signal Generator
**Files moved:** None.
**What was done:**
- `src/_signals_legacy.py` — copy of original `src/signals.py` at Phase 6 baseline. Read-only. Not imported.
- `src/signals/constants.py` — all strategy constants extracted
- `src/signals/filters/volume.py` — `passes_volume_gate()`, `volume_direction_note()`
- `src/signals/scoring/quality.py` — `signal_quality()`
- `src/signals/candidate_generators/pivot_signal.py` — `check_pivot_setup()`
- `src/signals/candidate_generators/pullback_signal.py` — `check_pullback_setup()`
- `src/signals/candidate_generators/range_scalp.py` — `check_range_scalp()`
- `src/signals/orchestrator.py` — `generate_signals()` re-wired to new modules
- `src/signals/__init__.py` — updated to re-export from `orchestrator` + `constants`

**Package shadowing:** Python's package-over-module preference means `src/signals/` (package) takes
precedence over the old `src/signals.py` (module). `src/signals.py` is NOT deleted but is effectively
shadowed. Callers importing `from src.signals import generate_signals` now hit the new package.

**Original preserved:** `src/_signals_legacy.py` — full original, read-only fallback. Removal scheduled Phase 17.

**Import verification at Phase 6 complete:**
```
python -X utf8 -c "from src.signals import generate_signals, MIN_RR, ADX_TRENDING; print('signals OK')"
python -X utf8 -c "import main; print('main.py OK')"
python -X utf8 -c "import backtest; print('backtest.py OK')"
```

**Known risk:** If someone runs `python -X utf8 -c "import src.signals"` they get the package, not
the old module. The package's `__init__.py` exports the same public API, so no functional difference.
But if any code does `import src.signals as s; s.<private_function>()` on old private names, it would
break. Audit confirms no such usage.

---

## Phase 7 — Backtest Engine
**Files moved:** None.
**What was done:**
- `src/backtesting/engine/walk_forward.py` — `TradeState`, `TradeResolver`, `walk_forward()`
- `src/backtesting/loaders/yfinance_loader.py` — `load_yfinance_1h()`
- `src/backtesting/loaders/schwab_loader.py` — `load_schwab_data()` using `resample()`
- `src/backtesting/analytics/report.py` — `print_report()` + R-dist + alt-exit + quality breakdown
- `src/backtesting/__init__.py` — public API re-exports
- `backtest.py` — converted from 390-line script to 60-line CLI that delegates to `src.backtesting.*`

**Duplication eliminated:**
- `backtest.py` previously defined its own `AGG` and `RESAMPLE_RULES` dicts (identical to `resampler.py`).
  Now uses `build_higher_tfs()` from `src.features.candles` — zero duplication.

**Import verification at Phase 7 complete:**
```
python -X utf8 -c "
from src.backtesting import walk_forward, print_report, load_yfinance_1h, load_schwab_data
from src.backtesting.engine.walk_forward import TradeState, TradeResolver
print('All imports OK')
"
python -X utf8 -c "import backtest; print('backtest.py OK')"
```

**Risk:** Low. `backtest.py` is the only entry point that changed, and it still runs with `python -X utf8 backtest.py`.

---

## What Has NOT Been Moved

These files are still at their original locations and are still the active source of truth:

| File | Role | Removal Target |
|---|---|---|
| `src/data.py` | Active Schwab client used by `main.py` | Phase 17 (after Phase 14) |
| `src/indicators.py` | Shim → `src/features/indicators/` | Phase 17 |
| `src/signals.py` | Shadowed by `src/signals/` package | Phase 17 |
| `src/_signals_legacy.py` | Read-only backup of original `signals.py` | Phase 17 |
| `src/display.py` | Active terminal formatter | Phase 17 (after Phase 11) |
| `main.py` | Active local scanner entry point | Phase 17 (after Phase 14) |
| `backtest.py` | Active CLI entry point (thin wrapper) | Keep — CLI stays |

---

## Phase 8–13 — Inference, Rules, Risk, Alerts, Paper Broker, Dashboard
**Files moved:** None.
**What was done:** All new modules created under `src/` — inference/bucket_engine, rules/rule_engine,
risk/local_risk_engine, alerts/telegram/provider, execution/paper_broker, dashboard/app.
**Shims:** None added. All new code in correct locations from the start.
**Risk:** None. Existing callers unchanged.

---

## Phase 14 — AWS Utilities
**Files created:** `src/aws/cloudwatch/logger.py`, `src/aws/secrets_manager/loader.py`.
**boto3:** Added to `requirements.txt` as optional (AWS deployment only — graceful fallback locally).
**Blocked:** Lambda handler migration, EventBridge, DynamoDB cooldown — all in separate Terraform repo.
**Risk:** None. Both modules import cleanly without boto3; fall back to env vars.

---

## Phase 15 — Tradovate Placeholder Verification
**Files modified:** `src/execution/__init__.py` — added `load_tradovate_broker()` factory.
**Files modified:** `src/execution/tradovate_future/broker.py` — added `__init__` accepting optional deps.
**TradovateBroker:** All 8 methods raise RuntimeError; `is_enabled()` hardcoded False.
**Unlock conditions:** $1,000 account balance + 60 paper trades with positive expectancy.
**Risk:** None. Factory exists but broker is always disabled.

---

## Phase 16 — Testing
**Files created:**

| Test File | Tests | What is covered |
|---|---|---|
| `tests/features/test_indicators.py` | 35 | All 16 indicator functions: SMMA, pivots (standard + fib), get_all_pivots, ema/micro alignment, ATR, swing high/low, pullback touch, ADX, rejection at level, bar close quality, engulfing, momentum consistency |
| `tests/signals/test_volume_filters.py` | 11 | passes_volume_gate, passes_volume_direction_gate, volume_direction_note (all edge cases: threshold, insufficient data, aligned/against) |
| `tests/signals/test_quality_score.py` | 8 | signal_quality A/B/C tier assignment, both directions, with/without pivot level |
| `tests/signals/test_signal_generators.py` | 14 | check_pivot_setup, check_pullback_setup, check_range_scalp — fires, None returns, required fields, R/R minimums, T2 suppression |

**Total suite at Phase 16:** 127 passed, 3 skipped, 0 failures (1.05s).

**Previously existing test files (Phases 7–12):**

| Test File | Tests |
|---|---|
| `tests/backtesting/test_walk_forward.py` | 14 |
| `tests/rules/test_rule_engine.py` | 26 |
| `tests/risk/test_local_risk_engine.py` | 14 |
| `tests/alerts/test_formatter.py` | 9 |
| `tests/execution/test_paper_broker.py` | 10 |

**Deferred:** Integration tests, backtest fixture data, regression tests — all blocked on fixture infrastructure.

---

## Phase 17 — Cleanup
**Dead code deleted:**
- `src/signals.py` (630 lines) — legacy file fully shadowed by `src/signals/` package
- `src/_signals_legacy.py` (630 lines) — read-only backup, never imported
- `src/indicators.py` (4 lines) — shim; only caller (main.py line 11) updated to import directly from `src.features.indicators`

**Files moved:**
- `LOGIC.md` → `docs/logic_reference.md`
- `USER_MANUAL.md` → `docs/user_manual.md`
- `auth_schwab.py` → `scripts/maintenance/auth_schwab.py`
- `backtest_schwab_*.csv`, `backtest_yf_1h.csv` → `data/backtests/`

**Files created:**
- `docs/cleanup_candidates.md` — D-10 closed; tracks deferred cleanup items and false-positive import warnings

**CLAUDE.md updated:** auth_schwab.py path updated to `scripts/maintenance/auth_schwab.py` in two places.

**Verification:** 127 tests passed, 3 skipped, 0 failures. All 5 import checks passed.

---

## Lambda Sync — 2026-04-30 (Phase 17 + Lambda parity)

**Context:** Live Lambda (`mes-signal-bot`) was running pre-Phase 8 signal logic — no quality scoring,
no LEVEL_BLACKLIST, no pullback or range scalp signals. Multiple people receiving signals.

**What was created:**
- `lambda_sync/src/indicators.py` — verbatim copy of `src/features/indicators/indicators.py`
  (adds `rejection_at_level`, `bar_close_quality`, `is_engulfing`, `momentum_consistency`)
- `lambda_sync/src/signals.py` — ~600-line consolidated flat file; all signal logic inlined
  (no package imports). Uses relative import: `from .indicators import ...` (Lambda's src/ is a package)
  Sections: constants, LEVEL_BLACKLIST, LevelCatalog, RegimeClassifier, volume filters,
  signal_quality(), check_pivot_setup(), check_pullback_setup(), check_range_scalp(),
  _calc_market_context(), generate_signals()
  Simplified rule engine: `_QUALITY_SCORE = {'A': 80, 'B': 60, 'C': 40}` (no JSON file loading)

**What was deployed to `AWS Infrastructure/lambda/trading-bot/function/`:**
- `src/indicators.py` — replaced with lambda_sync version
- `src/signals.py` — replaced with lambda_sync version
- `lambda_handler.py` — `format_signal()` surgically replaced; all infrastructure preserved
  (Schwab init, DynamoDB logging, EOD report, credential caching unchanged)

**Deployment:** `cd "AWS Infrastructure\terraform\personal\trading-bot" && terraform apply`
Terraform detected hash change and updated Lambda in-place.

**Verification:** CloudWatch logs show `[A · 80]` or `[B · 60]` in signal output.
Signals at D_FR1/D_S2 no longer appear (filtered by LEVEL_BLACKLIST before generation).

**Known gap remaining:** Signal cooldown window (5–60 min per tf/level/direction) is still in-memory
on Lambda and resets each invocation. DynamoDB dedup by signal_id prevents double-logging the same
timestamp, but the cooldown window is not enforced cloud-side. Deferred.

---

## Known Import Risks

1. ~~**`src/signals.py` still on disk`**~~ — **resolved in Phase 17.** File deleted.

2. ~~**`src/indicators.py` shim**~~ — **resolved in Phase 17.** File deleted.

3. **No tests for import paths** — all import path verification was done manually via one-shot
   `python -c` commands. See Phase 16 for full test suite coverage of indicator and signal logic.
