# tests

All automated tests. Structure mirrors `src/`.

## Subfolders
- `unit/` — one test file per src/ module, no I/O, no API calls
- `integration/` — end-to-end signal flow (data → features → signals → risk → alert)
- `backtesting/` — verify walk-forward correctness (no lookahead, deterministic output)
- `fixtures/` — sample OHLCV DataFrames, expected signal outputs, mock pivot sets

## Status
- Zero tests exist. All subfolders are empty.

## Related TODOs
- Phase 16: Unit tests for indicators, signal generators, risk engine, paper broker
- Phase 16: Integration test for full signal flow
- Phase 16: Backtest regression tests (known input → known output)

## Rules
- Tests never call real Schwab API or Telegram
- Backtest tests use fixture data from tests/fixtures/
- Unit tests must pass with no .env file present
