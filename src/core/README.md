# src/core

Shared utilities used by every other layer. No trading logic here.

## What belongs here
- Config loading (`config/`) — reads .env locally, Secrets Manager on Lambda
- Structured logging (`logging/`) — wraps Python logging + CloudWatch emission
- Time utilities (`time_utils/`) — market hours gate, session labels, timezone helpers
- Abstract contracts (`contracts/`) — ABCs that all providers implement
- Custom exceptions (`exceptions/`) — typed errors for the OS

## What does NOT belong here
- Any trading strategy logic
- Any API calls (Schwab, Tradovate, Telegram)
- Any pandas/numpy computation

## Status
- `contracts/` — implemented (5 interfaces: MarketDataProvider, ExecutionProvider,
  StorageProvider, AlertProvider, RiskEngine)
- `config/` — implemented (Config dataclass + get_config() with env/Secrets Manager routing)
- `logging/` — empty
- `time_utils/` — empty
- `exceptions/` — empty

## Related TODOs
- Phase 2: Create structured logger (wraps print for local, CloudWatch for Lambda)
- Phase 2: Create market hours and session label utilities
- Phase 2: Create custom exception types (DataFetchError, SignalError, RiskVetoError)
