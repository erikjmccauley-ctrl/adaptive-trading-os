# Folder Architecture Plan
_Generated: 2026-04-29_

Target folder structure for the Adaptive Trading OS. Based on the architecture visual and
gap analysis. Designed so every major OS component has a home and imports stay clean.

---

## Design Principles

1. Each OS layer is a separate top-level `src/` subdirectory — no cross-layer tangling.
2. Interfaces live in `src/core/contracts/` — code depends on contracts, not concrete providers.
3. Local dev and AWS deployments share the same `src/` — environment switches via config, not code.
4. Tradovate execution code is isolated under `src/execution/tradovate_future/` and
   disabled by default (`LIVE_EXECUTION_ENABLED=false`).
5. Lambda handlers in `src/aws/lambda_handlers/` import from the same `src/` modules as
   local scripts. No separate Lambda code tree.
6. Tests mirror the `src/` structure.

---

## Target Structure

```
Trading Bot/                              ← repo root (rename to adaptive-trading-os/ later)
│
├── README.md
├── To Do.txt                             ← master task tracker
├── .env.example                          ← placeholder keys only
├── .gitignore                            ← must include .env, schwab_token.json
├── requirements.txt                      ← unified (replaces current)
├── pyproject.toml                        ← project metadata + tool config
│
├── docs/
│   ├── repo_inventory.md                 ← Phase 1 output (this session)
│   ├── adaptive_trading_os_gap_analysis.md
│   ├── folder_architecture_plan.md
│   ├── refactor_log.md                   ← tracks every file move
│   ├── cleanup_candidates.md             ← Phase 9 output
│   ├── security_findings.md              ← secrets audit
│   ├── aws_architecture.md               ← replaces essay_aws_architecture.md
│   ├── operating_modes.md                ← research / paper / live modes
│   ├── risk_policy.md                    ← risk rules + kill switch behavior
│   ├── data_schema.md                    ← S3 / DynamoDB / Athena schemas
│   └── tradovate_future_integration.md   ← placeholder: what Tradovate needs
│
├── src/
│   │
│   ├── core/                             ← shared utilities, no business logic
│   │   ├── config/                       ← config loader (reads .env / Secrets Manager)
│   │   ├── logging/                      ← structured logger (local + CloudWatch)
│   │   ├── time_utils/                   ← market hours, session labels, timezone
│   │   ├── contracts/                    ← abstract interfaces (see below)
│   │   └── exceptions/                   ← custom exception types
│   │
│   ├── data_sources/                     ← market data providers
│   │   ├── interfaces/                   ← MarketDataProvider ABC
│   │   ├── schwab/                       ← SchwabProvider (wraps current src/data.py)
│   │   └── tradovate_future/             ← placeholder only, disabled
│   │
│   ├── ingestion/                        ← raw data → normalized candles
│   │   ├── collectors/                   ← scheduled fetchers (per TF)
│   │   ├── normalizers/                  ← schema normalization, OHLCV validation
│   │   └── validators/                   ← completeness checks, gap detection
│   │
│   ├── storage/                          ← persistence layer
│   │   ├── interfaces/                   ← StorageProvider ABC
│   │   ├── local/                        ← CSV / file-based (dev mode)
│   │   ├── s3/                           ← S3 raw + normalized candle buckets
│   │   ├── dynamodb/                     ← signal log, rules, outcomes, risk state
│   │   └── athena/                       ← query builder for analytics
│   │
│   ├── features/                         ← everything computed from candles
│   │   ├── indicators/                   ← SMMA, ATR, ADX, pivots (current indicators.py)
│   │   ├── candles/                      ← candle builder, resampler
│   │   ├── sessions/                     ← RTH/pre-market/AH labeling, VWAP
│   │   ├── regimes/                      ← ADX regime classifier (trending/neutral/ranging)
│   │   └── support_resistance/           ← pivot level catalog, level proximity
│   │
│   ├── signals/                          ← candidate signal generation
│   │   ├── candidate_generators/
│   │   │   ├── pivot_signal.py           ← extracted from current signals.py
│   │   │   ├── pullback_signal.py        ← extracted from current signals.py
│   │   │   ├── range_scalp.py            ← extracted from current signals.py
│   │   │   ├── breakout_retest.py        ← new (future)
│   │   │   ├── vwap_reclaim.py           ← new (future)
│   │   │   ├── opening_range_breakout.py ← new (future)
│   │   │   └── volatility_expansion.py   ← new (future)
│   │   ├── scoring/                      ← quality tier + inference-weighted score
│   │   └── filters/                      ← volume filter, ATR gate (extracted from signals.py)
│   │
│   ├── backtesting/                      ← backtest engine
│   │   ├── engine/                       ← walk-forward core (current backtest.py base)
│   │   ├── exits/                        ← stop/target, trailing stop, time-based exits
│   │   ├── metrics/                      ← MFE/MAE, R-multiple, drawdown, Sharpe
│   │   └── reports/                      ← output formatting, CSV export
│   │
│   ├── inference/                        ← performance → signal confidence
│   │   ├── bucket_analysis/              ← group trades by setup family, regime, level
│   │   ├── expectancy/                   ← win rate, avg win/loss, expectancy per bucket
│   │   ├── confidence/                   ← score signals by historical bucket stats
│   │   └── rule_recommendations/         ← surface candidate rule changes
│   │
│   ├── rules/                            ← rule engine
│   │   ├── active_rules/                 ← current live rules (JSON / DynamoDB backed)
│   │   ├── candidate_rules/              ← rules in testing / promotion queue
│   │   ├── promotion/                    ← logic to promote candidate → active
│   │   ├── rule_engine/                  ← evaluate_signal(), score_signal(), block_signal()
│   │   └── versioning/                   ← rule version history
│   │
│   ├── risk/                             ← risk management layer
│   │   ├── interfaces/                   ← RiskEngine ABC
│   │   ├── limits/                       ← max trades/day, max loss, consecutive loss limit
│   │   ├── daily_state/                  ← persistent state (DynamoDB-backed)
│   │   ├── kill_switch/                  ← emergency halt all signal delivery
│   │   └── validators/                   ← validate_trade_intent() per signal
│   │
│   ├── alerts/                           ← notification layer
│   │   ├── interfaces/                   ← AlertProvider ABC
│   │   ├── telegram/                     ← send_signal(), send_eod_report(), send_error()
│   │   ├── formatters/                   ← terminal formatter (local), Telegram card formatter
│   │   └── controls/                     ← Telegram command handling (approve/reject if added)
│   │
│   ├── execution/                        ← trade execution
│   │   ├── interfaces/                   ← ExecutionProvider ABC
│   │   ├── paper_broker/                 ← fill simulator, position tracker, P/L, slippage
│   │   ├── order_models/                 ← Order, Fill, Position data classes
│   │   ├── position_monitor/             ← track open positions, check stops/targets
│   │   └── tradovate_future/             ← placeholder only, all methods raise NotImplemented
│   │
│   ├── outcomes/                         ← trade result tracking
│   │   ├── tracking/                     ← resolve signal outcomes from price data
│   │   ├── mfe_mae/                      ← max favorable / adverse excursion per trade
│   │   ├── r_multiple/                   ← R distribution (how many R's did it actually move)
│   │   └── trade_journal/                ← structured trade log (DynamoDB + CSV)
│   │
│   ├── dashboard/                        ← visualization
│   │   ├── streamlit/                    ← main dashboard app
│   │   ├── api/                          ← FastAPI endpoints (optional)
│   │   └── components/                   ← reusable UI components
│   │
│   └── aws/                              ← AWS integration
│       ├── lambda_handlers/              ← lambda_handler.py (bring from infra repo)
│       ├── eventbridge/                  ← schedule definitions
│       ├── cloudwatch/                   ← structured logging, metric publishing
│       ├── secrets_manager/              ← credential loading for Lambda
│       └── iam/                          ← IAM policy notes (not Terraform — just docs)
│
├── data/
│   ├── raw/                              ← raw API responses (local dev only)
│   ├── normalized/                       ← normalized candles (local dev)
│   ├── backtests/                        ← backtest CSVs (move from backtest_results/)
│   ├── reports/                          ← generated reports
│   └── sample/                           ← small fixture datasets for tests
│
├── tests/
│   ├── unit/                             ← one file per src/ module
│   ├── integration/                      ← end-to-end signal flow tests
│   ├── backtesting/                      ← backtest correctness tests
│   └── fixtures/                         ← sample OHLCV data, expected outputs
│
├── scripts/
│   ├── dev/
│   │   ├── run_local.py                  ← current main.py (moved)
│   │   └── run_backtest.py               ← current backtest.py (moved)
│   ├── deployment/
│   │   ├── deploy_lambda.sh
│   │   └── build_lambda_layer.sh
│   ├── maintenance/
│   │   └── refresh_schwab_token.py       ← current auth_schwab.py (moved)
│   └── cleanup/
│       └── archive_old_files.sh
│
└── archive/
    ├── deprecated/
    │   └── YYYY-MM-DD/                   ← date-stamped archived files
    └── old_versions/
```

---

## Core Contracts (src/core/contracts/)

These abstract interfaces are defined first. All concrete implementations depend on them.

### MarketDataProvider
```python
class MarketDataProvider(ABC):
    def get_multi_tf_data(self) -> dict[str, pd.DataFrame]: ...
    def get_pivot_source_ohlc(self) -> dict[str, pd.DataFrame]: ...
    def is_live(self) -> bool: ...
```

### ExecutionProvider
```python
class ExecutionProvider(ABC):
    def place_order(self, order: Order) -> Fill: ...
    def get_position(self, symbol: str) -> Position | None: ...
    def flatten_all(self) -> None: ...
    def is_enabled(self) -> bool: ...
```

### StorageProvider
```python
class StorageProvider(ABC):
    def write_signal(self, signal: dict) -> None: ...
    def read_signals(self, date: str) -> list[dict]: ...
    def write_candles(self, tf: str, df: pd.DataFrame) -> None: ...
    def read_candles(self, tf: str) -> pd.DataFrame: ...
```

### AlertProvider
```python
class AlertProvider(ABC):
    def send_signal(self, signal: dict) -> None: ...
    def send_report(self, report: dict) -> None: ...
    def send_error(self, message: str) -> None: ...
```

### RiskEngine
```python
class RiskEngine(ABC):
    def validate_trade_intent(self, signal: dict) -> bool: ...
    def update_daily_state(self, outcome: dict) -> None: ...
    def trigger_kill_switch(self, reason: str) -> None: ...
    def is_kill_switch_active(self) -> bool: ...
```

---

## Existing File → New Location Map

| Current Path | New Path | Action |
|---|---|---|
| `src/indicators.py` | `src/features/indicators/indicators.py` | Move |
| `src/data.py` | `src/data_sources/schwab/provider.py` | Move + wrap in class |
| `src/signals.py` | `src/signals/candidate_generators/` (split) + `src/rules/rule_engine/` | Refactor |
| `src/display.py` | `src/alerts/formatters/terminal.py` | Move |
| `main.py` | `scripts/dev/run_local.py` | Move |
| `backtest.py` | `src/backtesting/engine/` + `scripts/dev/run_backtest.py` | Refactor |
| `auth_schwab.py` | `scripts/maintenance/refresh_schwab_token.py` | Move |
| `backtest_results/*.csv` | `data/backtests/` | Move |
| `essay_aws_architecture.md` | `docs/aws_architecture.md` | Move |
| `essay_for_traders.md` | `docs/strategy_for_traders.md` | Move |
| `LOGIC.md` | `docs/logic_reference.md` | Move |
| `USER_MANUAL.md` | `docs/user_manual.md` | Move |
| `charts/` | `charts/` (keep in place) | No change |

**Note:** File moves happen in Phase 6 only — after scaffolding is verified and imports
are mapped. Do not move files as part of Phase 1.
