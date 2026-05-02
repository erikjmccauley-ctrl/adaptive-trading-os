# src/execution/tradovate_future — PLACEHOLDER

This folder is a placeholder for future Tradovate API integration.

## Current status: DISABLED

No code in this folder is active. All methods in any class here must:
1. Check `config.live_execution_enabled` and raise `RuntimeError` if False.
2. Check `config.mode == 'live'` and raise `RuntimeError` if not live mode.

## Unlock conditions
- Account balance >= $1,000 (Tradovate API minimum)
- 60+ paper trades completed with positive expectancy
- LIVE_EXECUTION_ENABLED=true set explicitly in config
- Human review and approval of the integration

## When ready, implement
- TradovateProvider(MarketDataProvider) — market data via WebSocket / REST
- TradovateBroker(ExecutionProvider) — order placement, bracket orders, position monitor
- Auth flow: POST /auth/accesstokenrequest → accessToken
- Contract: MESM6 (verify front month before going live)
- Emergency flatten on kill switch trigger

## API endpoints
- Demo: https://demo.tradovateapi.com/v1
- Live: https://live.tradovateapi.com/v1
