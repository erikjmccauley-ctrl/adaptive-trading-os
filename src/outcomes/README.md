# src/outcomes

Trade outcome tracking. Resolves signals against price action to determine win/loss,
then records MFE, MAE, and R-multiples for the inference engine to consume.

## What belongs here
- `tracking/` — resolve signal outcomes from subsequent price bars
- `mfe_mae/` — max favorable excursion / max adverse excursion per trade
- `r_multiple/` — how many R's did price actually move (not just whether stop/target hit)
- `trade_journal/` — structured trade log (DynamoDB + CSV)

## What does NOT belong here
- Signal generation
- Execution logic

## Status
- All subfolders empty.
- The current Lambda DynamoDB log records signals but does NOT resolve outcomes.
  Outcome resolution is the missing piece that enables the inference engine.

## Related TODOs
- Phase 7 (backtest): MFE/MAE tracking is part of the expanded backtest engine
- Phase 12 (paper broker): paper fills feed outcomes tracking in real time
