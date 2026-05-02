# src/alerts

Alert and notification layer. All implementations satisfy `AlertProvider` from
`src/core/contracts/alerts.py`.

## What belongs here
- `formatters/signal_card.py` — pure HTML formatter for Telegram signal cards
- `telegram/provider.py` — TelegramProvider: send_signal(), send_report(), send_error(), send_text()
- `interfaces/` — placeholder for shared types
- `controls/` — placeholder for future Telegram command handling

## What does NOT belong here
- Signal generation
- Risk validation
- Execution

## Status — COMPLETE (Phase 11)

### What's wired
- `load_alert_provider(risk_engine)` in `src/alerts/__init__.py` — call once at startup
- Returns `TelegramProvider` if `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` are set, else `None`
- `main.py` calls `send_signal(sig)` for each passing signal after `print_signals()`
- Includes risk state (trades left, P&L, kill switch) and bucket stats (if backtest CSVs present)

### What's implemented but not yet wired
- `send_report(report)` — EOD summary card; Phase 12 will trigger this after paper trades resolve
- `send_error(message)` — available for Lambda failure alerts; not called from main.py yet

## Credentials
Set in `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```
Same credentials as the Lambda (`trading-bot/telegram` secret in Secrets Manager).
If either env var is missing, Telegram silently disables — bot runs terminal-only.

## Note on Lambda
The Lambda still formats its own Telegram messages in `lambda_handler.py`. When Lambda
code moves into this repo (Phase 14), it will use this formatter instead.
