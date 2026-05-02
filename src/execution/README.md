# src/execution

Trade execution layer. All implementations satisfy `ExecutionProvider` from
`src/core/contracts/execution.py`.

## What belongs here
- `interfaces/` — any helper types shared across execution providers
- `paper_broker/` — PaperBroker: fill simulation, position tracking, slippage model, P/L
- `order_models/` — Order, Fill, Position data classes (defined in contracts; this folder
  holds any extended models)
- `position_monitor/` — checks open position against current price for stop/target hits
- `tradovate_future/` — PLACEHOLDER ONLY. All methods raise NotImplementedError.
  Never enabled until LIVE_EXECUTION_ENABLED=true AND account >= $1,000.

## What does NOT belong here
- Signal generation
- Risk validation (happens before execution, in `src/risk/`)
- Data fetching

## Status
- All subfolders empty.
- PaperBroker is the ONLY executable broker until live trading is unlocked.

## Related TODOs
- Phase 12: Implement PaperBroker (fill engine, position tracker, slippage, P/L)
- Phase 15: Tradovate placeholder only — keep disabled

## SAFETY RULE
The Tradovate adapter must check `config.live_execution_enabled` on every method call
and raise RuntimeError if it is False. There must be no path to a real order unless
the flag is explicitly set and the account minimum is met.
