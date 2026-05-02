# src/features

Everything computed from raw OHLCV candles. Pure functions and stateless classes only.
No API calls, no storage writes.

## What belongs here
- `indicators/` — SMMA, ATR, ADX, pivot levels, price action helpers
- `candles/` — candle builder, resampler (1m → 5m → 1H, etc.)
- `sessions/` — RTH/pre-market/AH labeling, VWAP
- `regimes/` — ADX regime classifier: trending / neutral / ranging + ATR percentile
- `support_resistance/` — pivot level catalog, level proximity check

## What does NOT belong here
- Signal generation (goes in `src/signals/`)
- Data fetching (goes in `src/data_sources/`)
- Any side effects (I/O, API calls)

## Status — COMPLETE (Phase 5)
- `indicators/` — `indicators.py` migrated from root `src/indicators.py` (now a shim)
- `regimes/` — `RegimeClassifier`, `RegimeResult`, `calc_atr_percentile`, `volatility_label`
- `candles/` — `AGG`, `RESAMPLE_RULES`, `resample()`, `resample_to_higher()`, `build_higher_tfs()`
- `sessions/` — `get_session()`, `is_rth()`, `is_signal_window()`, `calc_vwap()`, `vwap_position()`
- `support_resistance/` — `PivotLevel` dataclass, `LevelCatalog` with proximity and target queries

`src/indicators.py` at repo root is now a one-line shim: `from src.features.indicators import *`
It will be removed in Phase 17 cleanup.
