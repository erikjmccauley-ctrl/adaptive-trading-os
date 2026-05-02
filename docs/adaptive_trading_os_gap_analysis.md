# Adaptive Trading OS — Gap Analysis
_Generated: 2026-04-29 (Phase 1 baseline). Updated 2026-04-29: Phase 5, 6, 7 complete._
_Items marked ✅ below have been implemented. All others remain as described._

Cross-reference of the current repo against the target Adaptive Trading OS architecture shown in
the visual (`Adaptive Trader/Adaptive Trader Visual.png`).

---

## Already Exists

### Schwab Market Data Provider
- **Path:** `src/data.py`
- **Does:** Authenticates via OAuth, fetches OHLCV for 1m/5m/15m/1H/4H/1D (with resampling),
  builds pivot source from daily/weekly/monthly bars.
- **Assessment:** Usable as-is for migration. Needs to be wrapped in a `MarketDataProvider`
  interface so it can be swapped for Tradovate later.

### Schwab Auth Flow
- **Path:** `auth_schwab.py`
- **Does:** One-time browser OAuth, saves `schwab_token.json`, tests connection.
- **Assessment:** Keep as a maintenance script. Move to `scripts/` in new structure.

### Feature Engine — Indicators ✅ Phase 5
- **Path:** `src/features/indicators/indicators.py` (shim at `src/indicators.py`)
- **Does:** SMMA(3/8/21), standard pivots, Fibonacci pivots, ATR(14), ADX(14), swing H/L,
  micro-alignment, pullback detection, rejection_at_level, bar_close_quality, is_engulfing,
  momentum_consistency.
- **Status:** Migrated to `src/features/indicators/`. Original `src/indicators.py` is a one-line shim.
  `RegimeClassifier` extracted to `src/features/regimes/`. Candle resampler in `src/features/candles/`.
  Session labeling in `src/features/sessions/`. Level catalog in `src/features/support_resistance/`.

### Candidate Signal Generator ✅ Phase 6
- **Path:** `src/signals/` (package; original `src/signals.py` shadowed)
- **Does:** Three signal paths: pivot, pullback, range scalp. ADX regime detection via
  `RegimeClassifier`. Volume filter, ATR gate, signal quality scoring (A/B/C tier).
- **Status:** Fully extracted. Each signal family has its own module. Volume filter, scoring,
  and constants are separate subpackages. Orchestrator wires them together. Public API unchanged.
- **Still fused:** Rule enforcement (R/R check, ATR gate) remains in signal generators rather
  than a separate rule engine. Full separation is Phase 9.

### Backtest Engine ✅ Phase 7
- **Path:** `src/backtesting/` (CLI entry at `backtest.py`)
- **Does:** Walk-forward simulation with `TradeState`/`TradeResolver`, MFE/MAE tracking,
  R-milestone flags (0.5R/1R/2R/3R), trailing stop mode, time-based exit, R-multiple
  distribution, alternate exit simulation, quality-tier breakdown. Dual data sources.
- **Status:** Fully extracted. `backtest.py` is now a 60-line thin CLI.
- **Remaining:** ATR-based and SMMA21-based stop tests (Phase 7 item left `[ ]`).

### Local Display / Alert Formatter (partial)
- **Path:** `src/display.py`
- **Does:** Prints signal boxes, status blocks, no-signal lines in terminal with colorama.
- **Assessment:** Local-only. Covers the "format alert" step but not Telegram delivery. The
  target OS needs a proper Telegram alert OS with formatting, send, error handling, and
  a control interface (approve/reject from Telegram).

### Signal Scanner / Orchestrator
- **Path:** `main.py`
- **Does:** 30s scan loop, market hours gate, multi-TF data fetch, signal generation,
  in-memory dedup with per-TF cooldowns, terminal output.
- **Assessment:** Works locally. Missing: persistence (cooldowns reset on restart), Telegram
  delivery, risk state check before firing, paper broker integration, CloudWatch logging.

### AWS Infrastructure (external repo)
- **Path:** `terraform/personal/trading-bot/` (separate infrastructure repo, NOT in this dir)
- **Does:** Lambda function, EventBridge schedule (every 1m MON-FRI 13:00-21:00 UTC),
  DynamoDB signal log (90-day TTL), Secrets Manager (`trading-bot/telegram`),
  S3 token bucket, Lambda Layer (`trading-bot-deps:4`), IAM least-privilege role.
- **Assessment:** Production-deployed and working. The Lambda code runs `indicators.py` and
  `signals.py` identically to local. Bring Lambda code into this repo.

### Documentation
- **Paths:** `CLAUDE.md`, `LOGIC.md`, `USER_MANUAL.md`, `essay_aws_architecture.md`,
  `essay_for_traders.md`
- **Assessment:** Excellent. Unusually thorough for a project this size. Move to `docs/` in
  new structure. No changes needed to content.

---

## Partially Exists

### Signal Cooldown / Deduplication
- **Existing:** `main.py` `_dedup_signals()` — in-memory dict, resets on restart.
- **Missing:** Persistent cooldown store (DynamoDB or Redis) so Lambda and local bot share
  the same state. Lambda currently has NO dedup at all.
- **Next step:** Implement DynamoDB-backed cooldown table in the risk/state layer. Add to
  `src/risk/daily_state/`.

### ADX Regime Detection ✅ Phase 5
- **Path:** `src/features/regimes/regime_classifier.py`
- **Status:** `RegimeClassifier` extracted and wired into `orchestrator.py` in Phase 6.
  Returns `RegimeResult` with `regime`, `adx_val`, `adx_tf`, `volatility_label` fields.
  Available to any component that imports `from src.features.regimes import RegimeClassifier`.

### Market Context Computation ✅ Phase 5 (partial)
- **Path:** `src/features/sessions/`, `src/features/regimes/`
- **Status:** Session labeling (`get_session()`, `is_rth()`), VWAP (`calc_vwap()`), and ATR
  percentile (`calc_atr_percentile()`) are implemented. These are available but not yet wired
  into the live scanner (`main.py` still uses `_calc_market_context()` from signals.py).
  Full wiring into the live path is part of Phase 14.

### Data Storage
- **Existing:** CSVs in `backtest_results/` (manual, flat).
  DynamoDB signal log (Lambda, in infra repo).
  S3 token bucket (Lambda, in infra repo).
- **Missing:** S3 raw candle storage, S3 normalized candle storage, local dev storage
  fallback, Athena query layer, DynamoDB tables for rules/outcomes.
- **Next step:** Define schemas in `src/storage/` and `docs/data_schema.md`.

### Signal Quality Scoring ✅ Phase 6 (base tier only)
- **Path:** `src/signals/scoring/quality.py`
- **Status:** A/B/C tier scoring extracted to standalone module. Three price-action components:
  bar close quality, momentum consistency, rejection at level. Returns `(tier, detail)` tuple.
  Bucket-level scoring (from inference engine) is Phase 8.

---

## Missing (Not Implemented At All)

### Candle Builder / Normalizer
Dedicated component that ingests raw API bars, validates OHLCV integrity, normalizes schema,
and writes to storage. Currently: raw API data goes directly into indicator calculations
with no validation or normalization layer.

### VWAP Calculation
Not implemented anywhere. The target OS visual explicitly shows VWAP-based setups (VWAP
reclaim/reject). Currently only SMMA and pivots are used.

### Session Labeling
No logic that tags bars as pre-market / RTH open / mid-session / close. The ADX regime
classifier does not account for session context.

### Candidate Setup Families Beyond Current Three
The target OS shows multiple setup families beyond the current three:
- Breakout/retest setup
- VWAP reclaim/reject setup
- Opening range breakout (ORB) setup
- Volatility expansion setup
None of these exist.

### Inference Engine
No bucket analysis, no expectancy computation by setup type, no confidence labeling from
historical results, no rule recommendation output. The backtest generates summary stats but
there is no feedback loop that routes those stats back into the signal scoring system.

### Rule Engine
No candidate rule model, no active rule model, no rule promotion/retirement logic, no rule
versioning. Signal rules (volume filter, ADX thresholds, proximity threshold, etc.) are
hardcoded constants in `src/signals.py`. Nothing is dynamic or data-driven.

### Risk Management Layer
No enforced daily max loss, no max trades per day, no consecutive loss circuit breaker, no
kill switch, no risk state persistence. The 2% rule and R/R minimums are enforced at signal
generation time but there is no independent risk gate that can block all signal delivery.

### Paper Broker Simulator
No paper order model, no fill simulation, no position tracking, no slippage model, no daily
paper P/L. Paper trading is done manually on Tradovate demo — the bot has no visibility into
paper trade outcomes.

### Outcome Tracker
No automated tracking of signal outcomes (win/loss), no MFE/MAE recording, no R-multiple
distribution, no trade journal. The DynamoDB signal log records signals fired but does not
resolve them against price action to determine outcomes.

### Adaptive Learning Loop
No feedback mechanism from outcomes → inference → rule updates. The entire adaptive learning
loop shown in the visual does not exist.

### Dashboard
No Streamlit app, no web UI, no API endpoint. All output is terminal (local) or Telegram
(Lambda).

### Tradovate Adapter (placeholder)
No Tradovate market data integration, no order placement code, no position monitor. The `.env`
has Tradovate API keys but no code uses them. This is correct for now — should be a placeholder
only until account balance reaches $1,000+.

### Execution Provider Interface / Market Data Provider Interface ✅ Phase 3
- **Path:** `src/core/contracts/`
- **Status:** `MarketDataProvider`, `ExecutionProvider`, `StorageProvider`, `AlertProvider`,
  `RiskEngine` abstract base classes are defined. `SchwabProvider` implements `MarketDataProvider`.
  `TradovateBroker` implements `ExecutionProvider` (all methods disabled/raise RuntimeError).
  `LocalStorage` implements `StorageProvider`. `AlertProvider` and `RiskEngine` are interface-only.

### Tests
Zero tests of any kind. No unit tests, no integration tests, no backtest fixtures.

### CloudWatch Structured Logging (local)
The local bot prints to stdout only. The Lambda has CloudWatch but logs are unstructured
(print statements). No structured log events, no custom metrics, no CloudWatch alarms.

### Secrets Manager Integration (local)
Local bot reads from `.env` via `python-dotenv`. No integration with Secrets Manager locally.
Lambda does use Secrets Manager. These should converge in the target OS.

---

## Recommended Refactor Strategy

### Preserve (minimal or no changes needed)
- `src/indicators.py` — clean, modular, no side effects. Move, don't rewrite.
- `auth_schwab.py` — keep as maintenance script; move to `scripts/`.
- `backtest_results/*.csv` — move to `data/backtests/`.
- All documentation files — move to `docs/`.

### Move + Light Refactor
- `src/data.py` → `src/data_sources/schwab/provider.py`
  Wrap existing fetch logic in a `SchwabProvider` class implementing `MarketDataProvider`.
- `src/signals.py` → split into:
  - `src/signals/candidate_generators/pivot_signal.py`
  - `src/signals/candidate_generators/pullback_signal.py`
  - `src/signals/candidate_generators/range_scalp.py`
  - `src/rules/rule_engine/` (volume filter, ADX routing, ATR gate, R/R check)
- `src/display.py` → `src/alerts/formatters/terminal.py` (local)
  Create `src/alerts/telegram/` for Telegram delivery.
- `main.py` → becomes the local dev entrypoint in `scripts/dev/run_local.py`.

### Rewrite / Build From Scratch
- `backtest.py` → expand to `src/backtesting/engine/` with MFE/MAE, R-multiple,
  alternate exit simulation, and proper metric reporting.
- Signal cooldown → `src/risk/daily_state/` with DynamoDB backing.

### Build First (highest leverage on the OS)
1. **Folder structure + interfaces** (defines the shape of everything else)
2. **MarketDataProvider + SchwabProvider** (data in = everything works)
3. **StorageProvider** (local CSV + S3 paths for dev vs. AWS)
4. **Risk Engine** (kill switch + daily limits) — safety before anything else runs in paper mode
5. **Paper Broker** (position tracking so outcomes can be measured)

### Deprecate Later (after Lambda code is merged)
- `essay_for_traders.md` — useful as reference but not part of the OS
- `essay_aws_architecture.md` — superseded by `docs/aws_architecture.md`

### Never Touch (until explicitly enabled)
- Tradovate execution code — build placeholder interfaces only, keep `LIVE_EXECUTION_ENABLED=false`
