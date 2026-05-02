# src/data_sources

Market data providers. All implementations must satisfy `MarketDataProvider` from
`src/core/contracts/market_data.py`.

## What belongs here
- `schwab/` — SchwabProvider: wraps existing `src/data.py` Schwab API logic
- `tradovate_future/` — placeholder only (disabled until account >= $1,000)
- `interfaces/` — any helper types or enums shared across providers

## What does NOT belong here
- Feature computation (goes in `src/features/`)
- Storage (goes in `src/storage/`)
- Any trading logic

## Status
- `schwab/` — empty placeholder (existing logic still in `src/data.py` during transition)
- `tradovate_future/` — placeholder only, all methods must raise NotImplementedError
- `interfaces/` — empty

## Related TODOs
- Phase 3: Create SchwabProvider class wrapping existing fetch logic
- Phase 3: Add data validation and gap detection
- Phase 15: Tradovate placeholder (keep disabled)

## Note on the LOCAL vs LAMBDA Schwab provider
The local `src/data.py` uses `.env` + local `schwab_token.json`.
The Lambda version uses Secrets Manager + S3 token bucket.
The SchwabProvider class should handle both paths via the config loader.
