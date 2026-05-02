# src/backtesting

Walk-forward backtest engine. No lookahead.
Must always use the exact same `generate_signals()` as the live bot — no drift.

## What belongs here
- `engine/` — `walk_forward()`, `TradeState`, `TradeResolver` (MFE/MAE/R-multiple tracking)
- `analytics/` — `print_report()`: metrics, R-multiple distribution, alt-exit scenarios, quality tier breakdown
- `loaders/` — `load_yfinance_1h()`, `load_schwab_data()`
- `exits/` — future: extended exit simulation modes (placeholder)
- `metrics/` — future: standalone metric computation (placeholder)
- `reports/` — future: report generation separated from printing (placeholder)

## What does NOT belong here
- Live data fetching (use `src/data_sources/`)
- Signal generation changes — backtest must match live exactly

## Status — COMPLETE (Phase 7)
`backtest.py` at repo root is now a thin CLI entry point — all logic is in `src/backtesting/`.

### Trade record fields (Phase 7 additions)
`mfe_pts`, `mae_pts`, `mfe_r`, `mae_r`, `r_multiple`, `bars_held`,
`reached_0_5r`, `reached_1r`, `reached_2r`, `reached_3r`,
`signal_type`, `quality`, `regime`, `adx`

### Walk-forward rules (do not change)
- No lookahead: SMMA and pivots computed from data available at each bar
- Pivots derived from `iloc[-2]` of daily slice (yesterday's completed bar)
- Both stop and target hit same bar → LOSS (conservative)
- Timeout → mark-to-market at bar close
- Trailing stop mode: trail to breakeven after 1R, to 1R after 2R (optional flag)
