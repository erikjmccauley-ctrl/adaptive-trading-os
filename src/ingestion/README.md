# src/ingestion

Raw data ingestion pipeline. Receives OHLCV bars from data source providers, validates
integrity, normalizes schema, and hands off to storage.

## What belongs here
- `collectors/` — future: event-driven bar collection from streaming APIs
- `normalizers/` — future: schema normalization (column names, dtypes, timezone)
- `validators/` — future: OHLCV integrity checks (H≥O, H≥L, H≥C, L≤O, L≤C, volume≥0)

## What does NOT belong here
- Data source auth or API clients (goes in `src/data_sources/`)
- Feature computation (goes in `src/features/`)
- Storage writes (goes in `src/storage/`)

## Status — PLACEHOLDER (Phase 4 scaffolded, not yet implemented)

All subfolders contain empty `__init__.py` only.
This layer is not wired into the live bot or backtest engine yet.
Implementation is part of Phase 14 (AWS Orchestration) when the ingestion pipeline
moves to Lambda-triggered S3 writes.
