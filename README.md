# Adaptive Trading OS

A cloud-native futures signal system for MES (Micro E-mini S&P 500) built on a multi-timeframe SMMA + Pivot Point strategy. Designed from the ground up as a production system — not a notebook experiment.

**Live on AWS** since April 2026. Signals fire every minute during market hours, resolve outcomes automatically at EOD, and deliver formatted alerts to Telegram in real time.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Cloud | AWS Lambda · EventBridge · DynamoDB · S3 · Secrets Manager |
| Infrastructure as Code | Terraform |
| Data | Schwab API (live) · yfinance (backtest) |
| Alerts | Telegram Bot API |
| Dashboard | Streamlit |
| Testing | pytest (127 passing, 3 skipped) |

---

## What It Does

The system scans MES futures every 30 seconds locally (every minute on Lambda) and fires structured trade signals when three conditions align:

1. **Price at a key level** — one of 39 standard + Fibonacci pivot points (Daily / Weekly / Monthly)
2. **Trend confirmation** — 3/8/21 SMMA stack aligned across multiple timeframes (1m → Daily)
3. **Regime filter** — ADX-based regime classification routes each setup to the correct signal path

Three signal types are generated depending on market conditions:

| Signal | Condition | Min R/R |
|---|---|---|
| Pivot | Price at S/R + full SMMA alignment + HTF confirmation | 2.0 |
| Pullback | Trend continuation on SMMA21 bounce | 2.0 |
| Range Scalp | ADX < 18 (ranging market) + price at pivot boundary | 1.5 |

Each signal is scored A / B / C by a quality engine and filtered against a rule engine backed by backtest outcomes. Signals at statistically losing levels (e.g. `D_FR1`, `D_S2`) are blacklisted automatically.

---

## Architecture

```
src/
├── core/            — abstract interfaces (MarketDataProvider, ExecutionProvider,
│                      RiskEngine, AlertProvider, StorageProvider)
├── data_sources/    — SchwabProvider (live), Tradovate placeholder (disabled)
├── features/        — indicators (SMMA, ADX, ATR, VWAP), candle resampler,
│                      session labeling, regime classifier, S/R catalog (39 levels)
├── signals/         — pivot / pullback / range scalp generators, volume filter,
│                      ATR gate, quality scoring (A/B/C)
├── backtesting/     — walk-forward engine, MFE/MAE/R-multiple tracking,
│                      alternate exit simulation, trailing stop simulation
├── inference/       — bucket analysis (by TF, level, regime, quality tier),
│                      expectancy, profit factor, confidence labeling, rule recommendations
├── rules/           — JSON-backed rule engine: candidate → active promotion,
│                      retirement, score/block/evaluate
├── risk/            — daily loss limits, max trades/day, consecutive loss
│                      circuit breaker, kill switch
├── alerts/          — Telegram provider, HTML signal card formatter
├── execution/       — PaperBroker (slippage + fee model), Tradovate (disabled)
├── dashboard/       — Streamlit app: signals, rules, paper P&L, bucket performance
└── aws/             — CloudWatch structured logger, Secrets Manager loader
```

---

## Live AWS Deployment

```
EventBridge (every 1 min, Mon–Fri 9:30–4 PM ET)
    └── Lambda Function (mes-signal-bot)
            ├── Schwab API → fetch OHLCV (1m / 5m / 15m / 1H)
            ├── generate_signals() → quality score → rule filter → cooldown check
            ├── DynamoDB (mes-signal-log) → log signal + near_level + quality
            ├── Telegram → formatted HTML alert card
            └── 4:05 PM → EOD report (resolve WIN/LOSS from 1m candles, daily summary)
```

Signal cooldown is persisted in DynamoDB so Lambda's stateless execution model doesn't cause duplicate alerts across invocations.

Credentials (Schwab API keys, Telegram token) are loaded from AWS Secrets Manager on cold start and cached for the lifetime of the container.

---

## Signal Output (Telegram)

```
🟢 LONG MES  [5m (scalp)]  [A · 80] — PULLBACK

Entry:    5,248.50
Stop:     5,241.25  (-$36.25 / 1 ct)
T1:       5,312.50  (+$320.00)  [D_R2]
T2:       5,336.75  (+$441.25)  [W_R1]

TF Align:  15m ✓  |  1H ✓  |  Daily ✓
R/R: 14.33:1  |  TRENDING  |  ADX 31.2 (1H)  |  Range 52%
Reason: Pullback to SMMA21 held  |  5m bullish trend continuation
Hold: Hold while 5m closes above SMMA21 (5,241.00) — exit on close below
⏱ 10:34 AM ET  |  🟢 Live (Schwab)
```

---

## Backtest & Inference

The backtest engine uses walk-forward execution against the same `generate_signals()` function as the live bot — no separate backtest logic, no lookahead bias.

Outputs per trade: outcome, R-multiple, MFE, MAE, time-to-target, time-to-stop, alternate exit results (0.5R / 1R / 2R / 3R).

The inference engine pools backtest results and computes per-bucket statistics:

```
════════════════════════════════════════════════════════
  INFERENCE REPORT  |  60 trades  |  4 files loaded
════════════════════════════════════════════════════════

  BY ENTRY TF
  1h     n= 20  WR  45%  PF 3.64  E +0.81R   Net $+920  [B]
  15m    n= 15  WR  13%  PF 0.55  E -0.60R    Net $+66  [C]
  1m     n= 17  WR   6%  PF 0.33  E -0.74R    Net $-62  [C]

  RULE RECOMMENDATIONS
  ⚠  AVOID    D_FR1: 0/9 wins, PF 0.00 — consider blacklisting
  ⚠  AVOID    D_S2: 0/5 wins, PF 0.00 — consider blacklisting
  ✓  KEEP     1h: 9/20 wins (45%), PF 3.64, net $+920 [B]
```

---

## Risk Management

- Max trades per day · max daily loss · consecutive loss circuit breaker
- Kill switch (manual + auto-trigger on limit breach)
- Min signal quality score threshold
- ATR consumption gate (T2 suppressed at 90%, all signals blocked at 110%)
- Signal cooldown per `(timeframe, level, direction)` tuple
- Live execution disabled by default — `TradovateBroker.is_enabled()` returns `False`

---

## Running Locally

```bash
cp .env.example .env            # add Schwab API credentials
python scripts/maintenance/auth_schwab.py   # one-time OAuth
python -X utf8 main.py          # live scanner (30s interval)

python -X utf8 backtest.py      # walk-forward backtest
python -X utf8 inference.py     # bucket analysis → inference_results.csv
streamlit run src/dashboard/app.py          # dashboard
python -X utf8 -m pytest tests/ -q         # 127 tests
```

---

## Project Status

| Phase | Description | Status |
|---|---|---|
| 1–2 | Repo structure, config, contracts | ✅ Complete |
| 3 | Schwab market data layer | ✅ Complete |
| 5–6 | Feature engine + signal generators | ✅ Complete |
| 7 | Walk-forward backtest engine | ✅ Complete |
| 8 | Inference engine (bucket analysis) | ✅ Complete |
| 9 | Rule engine (promote / retire / block) | ✅ Complete |
| 10 | Risk management layer | ✅ Complete |
| 11 | Telegram alert OS | ✅ Complete |
| 12 | Paper broker | ✅ Complete |
| 13 | Streamlit dashboard | ✅ Complete |
| 14 | AWS orchestration (Lambda, DynamoDB) | ✅ Live |
| 16 | Test suite | ✅ 127 passing |
| 4 | S3 / DynamoDB storage layer | 🔲 Planned |
| 15 | Tradovate live execution adapter | 🔲 Pending funded account |

---

## Notes

Built as a learning-through-building project. Strategy originally taught by trader J. Wolfe (WolfeWinner TradingView layout). All signal logic is independently implemented.

Paper trading in progress — 30-trade minimum before going live on Tradovate.
