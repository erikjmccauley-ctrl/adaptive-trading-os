# data

Local data storage for dev mode. Not used by Lambda (Lambda reads from S3/DynamoDB).

## Subfolders
- `raw/` — raw API responses as received from Schwab (gitignored)
- `normalized/` — normalized OHLCV candles after validation (gitignored)
- `backtests/` — backtest output CSVs (move from `backtest_results/`)
- `reports/` — generated summary reports
- `sample/` — small fixture datasets safe to commit (used by tests)

## Note
`raw/` and `normalized/` are gitignored — they can be large and are regenerated from
the API. `backtests/` and `sample/` are committed.
