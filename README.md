# Adaptive Trading OS

MES futures signal bot built on the 3/8/21 SMMA + Pivot Point strategy.
Evolving from a lean signal scanner into a full cloud-native trading OS.

## Quick Start (local scanner)

```bash
cp .env.example .env        # fill in Schwab API credentials
python auth_schwab.py       # one-time OAuth flow
python -X utf8 main.py      # start live scanner
```

## Quick Start (backtest)

```bash
python -X utf8 backtest.py  # runs yfinance 2yr + Schwab short-TF backtests
```

## Strategy

Three signal types on MES (Micro E-mini S&P 500):
- **Pivot signal** — price at support/resistance with full SMMA stack aligned
- **Pullback signal** — trend continuation entry on SMMA21 bounce
- **Range scalp** — pivot-to-pivot in ranging (ADX < 18) markets

See `CLAUDE.md` for full strategy rules, signal output format, and instrument details.

## Architecture

```
src/
├── core/           — contracts (interfaces), config, logging
├── data_sources/   — Schwab provider (live), Tradovate (future, disabled)
├── features/       — indicators, candles, sessions, regimes, S/R catalog
├── signals/        — candidate generators, filters, quality scoring
├── backtesting/    — walk-forward engine with MFE/MAE/R-multiple tracking
├── inference/      — bucket analysis, expectancy, confidence (Phase 8)
├── rules/          — active/candidate rule engine (Phase 9)
├── risk/           — daily limits, kill switch (Phase 10)
├── alerts/         — Telegram provider (Phase 11)
├── execution/      — PaperBroker (Phase 12), Tradovate (disabled)
├── storage/        — LocalStorage (CSV), S3/DynamoDB (Phase 4)
└── aws/            — Lambda handlers, CloudWatch, Secrets Manager
```

## Current Phase

**Phase 7 complete** — Backtest engine with MFE/MAE tracking.
Next: Phase 8 — Inference Engine (bucket analysis, expectancy, rule recommendations).

See `To Do.txt` for the full 17-phase roadmap.

## Safety

- Live execution is **disabled**. `TradovateBroker.is_enabled()` returns `False`.
- `PaperBroker` is the only executable broker (Phase 12).
- `LIVE_EXECUTION_ENABLED` defaults to `false` in `.env.example`.
- Never risk more than 2% per trade. Minimum R/R: 2.0.

## AWS Deployment

Active Lambda function: `mes-signal-bot` (see `CLAUDE.md` → AWS Deployment section).
Lambda code is currently maintained separately. Phase 14 will bring it into this repo.
