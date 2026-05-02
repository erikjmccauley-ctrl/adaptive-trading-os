# src/aws

AWS integration layer. CloudWatch logging, Secrets Manager credential loading,
and placeholders for Lambda handlers and EventBridge definitions.

## Status (Phase 14 — 2026-04-30)

### Built and usable
| Module | File | Notes |
|--------|------|-------|
| CloudWatch logger | `cloudwatch/logger.py` | JSON-structured stdlib logger; CloudWatch captures Lambda stdout — no boto3 needed |
| Secrets Manager loader | `secrets_manager/loader.py` | boto3 with graceful fallback to env vars; returns `{}` if boto3 absent or AWS creds missing |

### Blocked — requires separate infra repo
| Item | Reason |
|------|--------|
| `lambda_handlers/` — Lambda entry points | Code lives in Terraform infra repo; not accessible here |
| EventBridge schedule definitions | Terraform-managed in infra repo |
| S3Storage / DynamoDBStateStore implementations | Needs real AWS infra to validate; deferred |
| `SchwabProvider._init_lambda()` | Needs Lambda `data.py` as reference — not in this repo |
| DynamoDB signal cooldown | Needs Lambda handler to call it |

---

## Module Reference

### `cloudwatch/`

```python
from src.aws.cloudwatch import get_logger, log_signal, log_outcome, log_error

logger = get_logger('my_module')
log_signal(logger, signal_dict)   # event='signal_fired' with key fields
log_outcome(logger, outcome_dict) # event='trade_resolved'
log_error(logger, 'message', exc) # event='error'
```

JSON output format — CloudWatch Insights query example:
```
fields @timestamp, message.direction, message.near_level
| filter message.event = "signal_fired"
| sort @timestamp desc
```

### `secrets_manager/`

```python
from src.aws.secrets_manager import load_telegram_credentials, load_schwab_credentials

tg   = load_telegram_credentials()  # {'bot_token': ..., 'chat_id': ...}
scwb = load_schwab_credentials()    # {'schwab_api_key': ..., 'schwab_app_secret': ...}
```

Both functions fall back to environment variables if boto3 is absent or AWS credentials
are not configured (normal in local dev).

---

## Current Lambda Resources (live as of 2026-04-26)

| Resource | Details |
|----------|---------|
| Function | `mes-signal-bot` |
| Layer | `trading-bot-deps:4` |
| EventBridge | every minute, Mon–Fri 13:00–21:00 UTC |
| DynamoDB | `mes-signal-log` — 90-day TTL |
| Secrets Manager | `trading-bot/telegram` — bot_token, chat_id, schwab_api_key, schwab_app_secret |
| S3 | `mes-signal-bot-tokens-667723749273` — schwab_token.json |

## What Does NOT Belong Here
- Terraform / infrastructure code (stays in infra repo)
- Any trading strategy logic
- `display.py`-style local formatting (Lambda uses `lambda_handler.py` for output)
