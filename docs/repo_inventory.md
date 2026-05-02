# Repo Inventory
_Generated: 2026-04-29 — Phase 1 baseline. Updated header: Phase 7 complete as of 2026-04-29._
_For current src/ structure see the README.md inside each subdirectory._

---

## Current Folder Tree

```
Trading Bot/
├── main.py                          — live local scanner
├── backtest.py                      — walk-forward backtest engine
├── auth_schwab.py                   — one-time Schwab OAuth flow
├── requirements.txt                 — 6 Python deps
├── .env                             ⚠ CONTAINS REAL SECRETS
├── schwab_token.json                ⚠ LIVE OAUTH TOKEN — never commit
├── CLAUDE.md                        — project instructions for Claude
├── LOGIC.md                         — full code logic reference
├── USER_MANUAL.md                   — trader usage guide
├── essay_aws_architecture.md        — AWS architecture writeup
├── essay_for_traders.md             — strategy explanation
│
├── src/
│   ├── __init__.py                  — empty
│   ├── data.py                      — Schwab API client + multi-TF fetch (active)
│   ├── indicators.py                — SHIM → src/features/indicators/ (Phase 5)
│   ├── signals.py                   — SHADOWED by src/signals/ package (Phase 6)
│   ├── _signals_legacy.py           — read-only backup of original signals.py
│   ├── display.py                   — terminal output formatting (active)
│   │
│   ├── core/                        — interfaces, config, logging (Phase 2-3)
│   ├── data_sources/                — SchwabProvider (Phase 3)
│   ├── features/                    — indicators, candles, sessions, regimes, S/R (Phase 5)
│   ├── signals/                     — pivot/pullback/range_scalp generators (Phase 6)
│   ├── backtesting/                 — walk-forward engine, analytics, loaders (Phase 7)
│   ├── storage/                     — LocalStorage (Phase 3), S3/DynamoDB (Phase 4, partial)
│   ├── execution/                   — TradovateBroker placeholder (disabled)
│   ├── inference/                   — Phase 8 placeholder
│   ├── rules/                       — Phase 9 placeholder
│   ├── risk/                        — Phase 10 placeholder
│   ├── alerts/                      — Phase 11 placeholder
│   └── ingestion/                   — Phase 14 placeholder
│
├── backtest_results/
│   ├── backtest_schwab_1m.csv
│   ├── backtest_schwab_5m.csv
│   ├── backtest_schwab_15m.csv
│   ├── backtest_schwab_1h.csv
│   └── backtest_yf_1h.csv
│
├── charts/
│   ├── image.png
│   └── Scalp.png
│
├── Adaptive Trader/
│   ├── Prompt                       — master rebuild spec (this document's origin)
│   └── Adaptive Trader Visual.png   — target OS architecture diagram
│
└── docs/                            — created 2026-04-29 (this folder)
    ├── repo_inventory.md
    ├── adaptive_trading_os_gap_analysis.md
    ├── folder_architecture_plan.md
    └── (more to follow)
```

**Note:** Lambda code (`lambda/trading-bot/function/`) is referenced in CLAUDE.md but lives in a
separate Terraform/infrastructure repository — it is NOT present in this local repo.

---

## File-by-File Assessment

### `main.py` — 125 lines
**Purpose:** Local live scanner loop. 30-second interval, market hours gate (9:30–4:00 ET),
signal deduplication by `(tf, level, direction)` key with per-TF cooldowns.
**Status:** Actively used. Works correctly.
**Maps to OS:** Scanner / Orchestrator layer.
**Notes:** Cooldown dict is in-memory only — does not persist across restarts. The Lambda version
lacks this dedup because Lambda is stateless. This is a known gap documented in `essay_aws_architecture.md`.

---

### `backtest.py` — ~60 lines (thin CLI after Phase 7)
**Purpose:** Walk-forward backtest CLI entry point. Delegates entirely to `src.backtesting.*`. Section 1: yfinance 2yr 1H bars. Section 2: Schwab
short-TF (1m/5m/15m/1H). Uses the exact same `generate_signals()` as the live bot.
Outputs: win rate, profit factor, drawdown, Sharpe, per-pivot-level breakdown. Saves CSVs.
**Status:** Actively used. Walk-forward logic is clean (no lookahead).
**Maps to OS:** Backtest Engine.
**Notes:** Exit logic is binary (T1 or stop, conservative). No MFE/MAE tracking. No R-multiple
distribution. No alternate exit simulation. These are all missing features listed in the target OS.

---

### `auth_schwab.py` — 62 lines
**Purpose:** One-time browser OAuth flow for Schwab. Saves `schwab_token.json`. Runs a test
quote after auth.
**Status:** Actively used (run once; re-run when token expires ~7 days).
**Maps to OS:** Data Sources / Schwab auth.
**Notes:** Hardcodes `callback_url='https://127.0.0.1:8182'` — fine for local dev, not relevant
to Lambda (Lambda uses S3 token path).

---

### `src/data.py` — 122 lines
**Purpose:** Schwab API client initialization (using `.env` credentials + `schwab_token.json`),
multi-TF OHLCV fetching (1m/5m/15m/30m→1H/1D), 4H resampling from 1H, daily pivot source build.
**Status:** Actively used.
**Maps to OS:** Data Sources / Schwab provider.
**Notes:** This is the LOCAL version. The Lambda version has a different init path (S3 token,
Secrets Manager creds, no dotenv). Do NOT treat these as interchangeable.

---

### `src/indicators.py` — 224 lines
**Purpose:** All technical calculations: SMMA(3/8/21), standard pivots, Fibonacci pivots,
ATR(14), ADX(14), swing high/low, micro-alignment, pullback touch detection, rejection_at_level,
bar_close_quality, is_engulfing, momentum_consistency.
**Status:** Actively used. Identical between local and Lambda.
**Maps to OS:** Feature Engine / indicators layer.
**Notes:** Clean, modular, no side effects. Good candidate for direct migration.

---

### `src/signals.py` — 630 lines
**Purpose:** Core signal logic. Three paths: pivot signal, pullback signal, range scalp.
Includes: ADX regime detection, volume filter, ATR consumption check, signal quality tier (A/B/C),
market context computation, R/R enforcement, target selection.
**Status:** Actively used. Identical between local and Lambda.
**Maps to OS:** Candidate Signal Generator + Rule Engine (currently fused — should be separated).
**Notes:** Signal generation and rule application are not separated. Everything is hardcoded in
this one file. The target OS separates these into distinct layers. This file is the biggest
refactor candidate.

---

### `src/display.py` — 147 lines
**Purpose:** Terminal output: signal box, status block (price + pivots + alignment), no-signal
line, header.
**Status:** Actively used (local only — Lambda has its own formatter in `lambda_handler.py`).
**Maps to OS:** Alert formatter / Telegram formatter (partial).
**Notes:** Local-only concern. In the target OS, this becomes a Telegram card formatter plus a
dashboard renderer.

---

### `requirements.txt`
**Contents:** `yfinance`, `schwab-py`, `pandas`, `numpy`, `colorama`, `python-dotenv`
**Status:** Active.
**Notes:** `yfinance` is local-only (used by `backtest.py`). `colorama` is local-only
(terminal colors). Neither belongs in the Lambda layer. No version pins (only `>=`).
The target OS will need additional deps: `boto3`, `streamlit`, `fastapi`, `pytest`, etc.

---

### `.env` — ⚠ SECURITY RISK
**Contents (keys only, values redacted):**
- `TRADOVATE_API_KEY`
- `TRADOVATE_API_SECRET`
- `TRADOVATE_APP_ID`
- `TRADOVATE_APP_VERSION`
- `TRADOVATE_DEMO`
- `SCHWAB_API_KEY`
- `SCHWAB_APP_SECRET`
**Status:** Contains live credentials.
**Risk:** If committed to git, these credentials are exposed. No `.gitignore` was found in this
directory.

---

### `schwab_token.json` — ⚠ SECURITY RISK
**Contents:** Live Schwab OAuth session token (access + refresh tokens).
**Status:** Required for live bot operation. Re-run `auth_schwab.py` when expired (~7 days).
**Risk:** If committed, grants immediate access to the Schwab account. Must never be committed.

---

### `CLAUDE.md` — Documentation
Full project instructions, strategy spec, signal types, constants, file structure, AWS deployment
details, backtest params, and upgrade roadmap. Source of truth for Claude sessions.

---

### `LOGIC.md` — Documentation
Exact code walkthrough in execution order. Covers data pipeline, indicator math, signal paths A
and B, quality tier scoring, main loop behavior, and all constants. Extremely useful for onboarding.

---

### `USER_MANUAL.md` — Documentation
Trader-facing guide. Pre-trade checklist, how to read signals, paper trading instructions, account
management. Not relevant to the refactor.

---

### `essay_aws_architecture.md` — Documentation
Detailed AWS architecture writeup: Lambda, EventBridge, Secrets Manager, S3, DynamoDB, IAM, cost
analysis. Explains the stateless cooldown gap between local and Lambda.

---

### `essay_for_traders.md` — Documentation
Plain-English explanation of the strategy for non-technical traders. No code relevance.

---

### `backtest_results/*.csv` — Data
Five backtest output files from previous runs. Schema:
`entry_ts, entry, stop, target1, target1_name, direction, entry_tf, rr, near_level,
outcome, exit_price, exit_ts, pnl_pts, pnl_dollars, month`
**Status:** Historical outputs. Safe to keep.

---

### `charts/*.png` — Reference images
Two TradingView screenshots for setup analysis. Not used by any code.

---

### `Adaptive Trader/` — Planning
Target OS spec and architecture diagram. Not code. Source of this entire rebuild effort.

---

## Summary: Active vs. Unused vs. Unsafe

| File | Status |
|------|--------|
| main.py | Active |
| backtest.py | Active |
| auth_schwab.py | Active (on-demand) |
| src/data.py | Active |
| src/indicators.py | Active |
| src/signals.py | Active |
| src/display.py | Active (local only) |
| src/__init__.py | Active (empty, required) |
| requirements.txt | Active |
| CLAUDE.md | Active (documentation) |
| LOGIC.md | Active (documentation) |
| USER_MANUAL.md | Active (documentation) |
| essay_aws_architecture.md | Reference |
| essay_for_traders.md | Reference |
| backtest_results/*.csv | Historical data |
| charts/*.png | Reference images |
| .env | Active ⚠ SECRETS |
| schwab_token.json | Active ⚠ LIVE TOKEN |
| Adaptive Trader/ | Planning docs |

**No duplicate files found.**
**No unused Python modules found.**
**No hardcoded API keys found in .py files** (all secrets go through `.env` / dotenv).
**No .gitignore found** — `.env` and `schwab_token.json` are unprotected.

---

## Missing: Lambda Code
CLAUDE.md documents a live Lambda deployment (`mes-signal-bot`) with this structure:
```
lambda/trading-bot/function/
├── lambda_handler.py
└── src/
    ├── data.py       (different init path — S3 token, no dotenv)
    ├── indicators.py (identical to local)
    ├── signals.py    (identical to local)
    └── report.py     (DynamoDB logging, EOD report)
```
This code lives in a separate Terraform/infrastructure repo and is not present here.
For the Adaptive Trading OS, the Lambda code should be brought into this repo under `src/aws/`.
