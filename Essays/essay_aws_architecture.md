# MES Signal Bot — Architecture & Cloud Design

## What It Is

The MES Signal Bot is a fully automated, cloud-native trading signal system built on AWS. It monitors the Micro E-mini S&P 500 futures contract (MES) in real time, applies a rules-based multi-timeframe technical strategy, and delivers trade signals to a phone via Telegram — every minute of every trading day, without a computer running at home.

The bot does not place trades. It detects setups, computes entries, stops, and targets, determines risk/reward, classifies the market regime, and delivers a complete, actionable signal. The trader makes the final call.

---

## Why Serverless

The first version of this bot ran locally. A Python script, a loop, a terminal window. It worked — until the computer slept, the internet dropped, or I stepped away. That version couldn't be trusted.

The requirements for a production signal system are simple: it needs to run exactly when the market is open, it needs to run every minute without fail, and it needs to cost as close to nothing as possible given the small account size it's supporting.

AWS Lambda meets all three. A Lambda function has no idle cost. It runs on-demand, exits in seconds, and scales without configuration. For a task that executes for roughly 120 seconds per hour during a 6.5-hour trading window, the annual compute cost is effectively zero — well within the free tier. An always-on EC2 instance running the same logic would cost $8–15/month and require patching, monitoring, and restart logic. Lambda requires none of that.

The tradeoff is statefulness. Lambda containers are ephemeral and cannot hold in-memory state across invocations. Every design decision in this project flows from that constraint.

---

## Architecture

```
EventBridge Scheduler (every 1 min, Mon–Fri 13:00–21:00 UTC)
    │
    ▼
AWS Lambda — mes-signal-bot (Python 3.13, 512 MB, 120s timeout)
    │
    ├── Secrets Manager ──── Telegram bot_token, chat_id
    │                        Schwab API key + secret
    │
    ├── S3 ─────────────── schwab_token.json (OAuth session token)
    │
    ├── Schwab API ─────── Real-time OHLCV data (1m, 5m, 15m, 1H, 4H, Daily)
    │
    ├── DynamoDB ────────── mes-signal-log (signal history, 90-day TTL)
    │
    └── Telegram API ────── Signal delivery to phone
```

### EventBridge Scheduler

The scheduler fires every minute, Monday through Friday, between 13:00 and 21:59 UTC (9:00–17:59 EDT). This bracket is intentionally wider than the 9:30–4:00 ET trading window — the Lambda itself enforces that gate internally. The extra width costs nothing: invocations outside market hours return in under one second.

A cron-based EventBridge schedule was chosen over a rate-based one for the day-of-week filter. Rate schedules don't support `MON-FRI` — they fire every day. The cron expression `cron(* 13-21 ? * MON-FRI *)` handles this cleanly.

### Lambda Function

The function is written in Python 3.13. On cold start, it calls Secrets Manager once to load credentials, initializes the Schwab client, pulls the OAuth token from S3, and caches everything in the container's global scope. Subsequent warm invocations skip the init entirely — the container is already configured.

The core execution path on each invocation:

1. Check market hours — return early if outside session
2. Check for 4:05 PM ET — if so, pull today's signals from DynamoDB and send the end-of-day report
3. Pull OHLCV data from Schwab across all timeframes
4. Calculate SMMA (3/8/21), ADX, ATR, pivot points, swing highs/lows
5. Run signal detection — filter blacklisted levels (D_FR1, D_S2), evaluate pivot / pullback / range scalp setups, score quality (A/B/C)
6. If signals found: log to DynamoDB, send Telegram card with quality tier and score

### Lambda vs Local Codebase

The Lambda function and the local development codebase have intentionally diverged. They share the same trading logic but have different initialization paths and different supporting infrastructure.

**Lambda code structure** (lives in `AWS Infrastructure\lambda\trading-bot\function\` — the Terraform infra repo on Desktop):
```
lambda/trading-bot/function/
├── lambda_handler.py   — entry point, Telegram formatting, EOD report
└── src/
    ├── data.py         — Schwab init using S3 token (no dotenv, no local files)
    ├── indicators.py   — SMMA, ADX, ATR, pivots, price-action helpers (synced from local)
    ├── signals.py      — generate_signals() + LEVEL_BLACKLIST + quality scoring A/B/C
    │                     + pullback signals + range scalp signals (Phase 17 parity — synced 2026-04-30)
    └── report.py       — DynamoDB logging, WIN/LOSS tracking
```

**Local codebase** (this repo) is a full Adaptive Trading OS with 17 layers:
```
src/
├── features/       — indicators, candles/resampler, sessions, regimes, S/R catalog
├── signals/        — pivot, pullback, range scalp generators, filters, scoring
├── risk/           — LocalRiskEngine, kill switch, daily loss limits
├── alerts/         — TelegramProvider, HTML signal cards with quality + bucket stats
├── execution/      — PaperBroker, TradovateBroker (placeholder)
├── rules/          — RuleEngine, candidate/active rule JSON store
├── inference/      — BucketEngine, expectancy, confidence labeling
├── backtesting/    — walk_forward, analytics, loaders
├── dashboard/      — Streamlit app (4 tabs)
└── aws/            — CloudWatch logger, Secrets Manager loader
```

**Sync rules:**
- `indicators.py` and `signals.py`: use `lambda_sync/` in the Trading Bot repo as the canonical staging area. `lambda_sync/src/signals.py` is a consolidated flat file with all signal logic inlined (no package imports). Copy both files to `AWS Infrastructure/lambda/trading-bot/function/src/` and run `terraform apply`.
- `lambda_handler.py`: only `format_signal()` changes with strategy updates. Schwab init, DynamoDB logging, and EOD report infrastructure must not be replaced.
- `data.py`: never copy from local to Lambda. Lambda's `data.py` uses S3 token handling; local uses dotenv. Only sync fetch/resample logic if it changes — the init block must stay Lambda-specific.
- Everything else in local `src/` (risk, alerts, dashboard, etc.): Lambda-only when account infrastructure justifies it

### Lambda Layer

The bot depends on pandas, numpy, requests, and the Schwab client library. These cannot be bundled inside the function package — Lambda has a 50 MB compressed limit for direct uploads, and the data science stack alone exceeds that.

The solution is a Lambda Layer: the dependencies are packaged separately, uploaded to S3, and attached to the function as a versioned layer. The layer is built for Amazon Linux 2023 on x86_64 using Docker, which ensures the compiled extensions (numpy's C bindings, etc.) match the Lambda execution environment exactly. Building natively on Windows and uploading would produce binaries that crash on Lambda.

The current layer is `trading-bot-deps:6`. Terraform manages the layer lifecycle — it detects changes via S3 object etag, creates a new layer version, and updates the function's layer ARN automatically on the next apply.

### Secrets Manager

All credentials — Telegram bot token, Telegram chat ID, Schwab API key, and Schwab app secret — are stored in a single Secrets Manager secret (`trading-bot/telegram`). The Lambda IAM role has `secretsmanager:GetSecretValue` permission scoped to that one ARN. Nothing is in environment variables.

The secret is loaded once per container lifetime. On a warm invocation, Secrets Manager is never called — the cached `_creds` tuple is used directly. This eliminates latency and avoids hitting Secrets Manager API rate limits on busy days.

The local codebase also has a Secrets Manager loader (`src/aws/secrets_manager/loader.py`) that gracefully falls back to `.env` variables when boto3 is absent or AWS credentials aren't configured. This allows the same credential-loading pattern to work in both Lambda and local development without code changes.

### S3 Token Store

The Schwab API uses OAuth 2.0. The access token expires every 30 minutes; the refresh token expires after 7 days. The local bot handles refresh automatically and writes the updated token back to `schwab_token.json`. Lambda needs the same file — but Lambda has no persistent local filesystem.

The token is stored in a private, versioned S3 bucket. On Lambda cold start, the Schwab client downloads the current token from S3. After a successful token refresh, it uploads the new token back. Versioning is enabled so that a bad refresh doesn't permanently break the bot — the previous version can be restored.

The Lambda IAM role has `s3:GetObject` and `s3:PutObject` scoped to `schwab_token.json` specifically. No other objects in the bucket are accessible.

When the Lambda shows 🟡 delayed data (refresh token expired):
```
python scripts/maintenance/auth_schwab.py
aws s3 cp schwab_token.json s3://mes-signal-bot-tokens-667723749273/schwab_token.json
```

### DynamoDB Signal Log

Every signal that fires is written to DynamoDB with:
- Partition key: `date` (YYYY-MM-DD)
- Sort key: `signal_id` (timestamp + direction + level)
- TTL: 90 days from signal time

At 4:05 PM ET, the Lambda queries the current date's signals, computes win/loss outcomes where available, and sends an end-of-day summary to Telegram. The 90-day TTL means the table self-manages — no cleanup job needed.

DynamoDB on-demand billing was chosen over provisioned capacity. Signal volume is low (0–10 writes per day) and sporadic. On-demand costs nothing at that scale and requires no capacity planning.

### CloudWatch Logging

The local codebase includes a structured CloudWatch logger (`src/aws/cloudwatch/logger.py`). It uses stdlib `logging` with a JSON formatter — no boto3 required, because CloudWatch captures Lambda's stdout automatically.

Every signal and trade outcome is logged as a structured JSON event:
```json
{"level": "INFO", "logger": "signal", "ts": "...", "message": {
  "event": "signal_fired",
  "direction": "LONG",
  "entry_tf": "5m",
  "near_level": "D_PP",
  "quality": "B",
  "quality_score": 72,
  "rr": 3.1,
  "regime": "trending"
}}
```

This structure enables CloudWatch Logs Insights queries:
```
fields @timestamp, message.direction, message.near_level
| filter message.event = "signal_fired"
| sort @timestamp desc
```

### IAM Design

The Lambda execution role follows least privilege:

- `secretsmanager:GetSecretValue` — one secret ARN
- `logs:CreateLogStream` + `logs:PutLogEvents` — one log group ARN
- `s3:GetObject` + `s3:PutObject` — one object key in one bucket
- `dynamodb:PutItem` + `dynamodb:Query` + `dynamodb:UpdateItem` — one table ARN

No wildcards. No `*` resources. The role cannot read other secrets, access other S3 paths, or touch other DynamoDB tables.

---

## Infrastructure as Code

The entire AWS deployment is managed with Terraform. The trading bot lives at `terraform/personal/trading-bot/` in a separate infrastructure repository, isolated from shared environment modules (VPC, IAM baseline, etc.).

Terraform state is stored in S3 with the existing state bucket (`erikmcc-tf-state-2025`). The Lambda function package is built using Terraform's `archive_file` data source, which zips the `function/` directory on every plan and computes a SHA256 hash. Terraform only updates the Lambda when the hash changes — no manual uploads, no console deployments.

The deployment workflow for any strategy code change:

1. Edit local strategy files in `src/features/indicators/` or `src/signals/`
2. Mirror the changes to `lambda_sync/src/indicators.py` or `lambda_sync/src/signals.py` (the consolidated Lambda-compatible flat files)
3. Copy to `AWS Infrastructure\lambda\trading-bot\function\src\`
4. `cd "AWS Infrastructure\terraform\personal\trading-bot" && terraform apply`

Terraform handles the rest: repackages the function zip, detects the SHA256 hash change, updates Lambda in-place.

---

## Cost

The bot runs for approximately 390 invocations per trading day (6.5 hours × 60 minutes). At 512 MB and ~2s average duration, each invocation costs roughly $0.000002. Annual cost: under $1.00. DynamoDB, S3, Secrets Manager, and CloudWatch Logs all fall within free tier at this usage level. EventBridge Scheduler has no cost for standard schedules.

---

## What Comes Next

**Signal cooldown in Lambda:** The cooldown dictionary that prevents duplicate signals in the local bot is in-memory and resets on every invocation. The Lambda version relies on DynamoDB deduplication by `signal_id` (timestamp + direction + level), which prevents logging the same signal twice but doesn't enforce the cooldown window that prevents re-fires of the same setup for 5–60 minutes. A DynamoDB-backed cooldown store with per-key TTLs would make Lambda behavior identical to the local bot.

**Tradovate API integration:** When account balance reaches $1,000, the Tradovate API becomes available. The local codebase already has a `TradovateBroker` placeholder (`src/execution/tradovate_future/broker.py`) with all required methods stubbed. At that point the bot moves from signal delivery to order execution — a significant scope expansion that will require independent testing before live capital is involved.

**Lambda code migration into this repo:** The Lambda handler and its supporting `src/` files currently live in the Terraform infra repo. The `lambda_sync/` folder in the Trading Bot repo is the staging area for syncs — it holds the canonical Lambda-compatible flat files but does not replace the infra repo. Full migration into this repo (enabling unified testing and version control alongside strategy code) is deferred until the infra repo structure is ready for consolidation.
