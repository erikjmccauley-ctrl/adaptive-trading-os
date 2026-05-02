# src/storage

Persistence layer. All implementations satisfy `StorageProvider` from
`src/core/contracts/storage.py`.

## What belongs here
- `interfaces/` — helper types shared across providers
- `local/` — LocalStorage: CSV files for dev mode (no AWS required)
- `s3/` — S3Storage: raw and normalized candle buckets
- `dynamodb/` — DynamoDB tables: signal log, rules, outcomes, risk state, cooldowns
- `athena/` — Athena query builder for analytics and research

## What does NOT belong here
- Any business logic
- Data transformation (goes in `src/features/`)

## Status
- All subfolders empty.
- Existing DynamoDB signal log is in the Lambda (infra repo), not here yet.

## Related TODOs
- Phase 4: Define S3 raw/normalized schemas (docs/data_schema.md)
- Phase 4: Define DynamoDB tables
- Phase 4: Implement LocalStorage (CSV)
- Phase 4: Implement S3Storage and DynamoDBStateStore
- Phase 14: Bring DynamoDB signal log schema into this repo

## DynamoDB tables needed
- `mes-signal-log` — existing: signals fired (partition: date, sort: signal_id), 90-day TTL
- `mes-signal-cooldown` — new: (tf, level, direction) → last_fired timestamp, TTL per TF
- `mes-risk-state` — new: daily risk state (trades, P/L, consecutive losses, kill switch)
- `mes-rules` — new: active and candidate rules
- `mes-outcomes` — new: resolved trade results (linked to signal records)
