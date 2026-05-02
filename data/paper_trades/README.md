# Paper Trades

Manual paper trading log for the live Lambda signal bot.

## Files

**`trade_log.csv`** — one row per signal, updated each trading day after EOD report
- Outcomes sourced from DynamoDB (auto-resolved at 4:05 PM ET) or manually verified via 1m candle check
- `pnl_usd` assumes 1 MES contract, $5/point, no slippage

**`daily_summary.csv`** — one row per trading day
- `win_rate_pct` = wins / (wins + losses), excludes open signals
- `net_pnl_usd` = sum of all resolved P&L for the day

## Workflow

1. EOD report fires at 4:05 PM ET — Lambda auto-resolves outcomes in DynamoDB
2. After market close, copy outcomes from DynamoDB into `trade_log.csv`
3. Add daily row to `daily_summary.csv`

To query DynamoDB directly:
```
aws dynamodb query --table-name mes-signal-log \
  --key-condition-expression "#d = :date" \
  --expression-attribute-names '{"#d":"date"}' \
  --expression-attribute-values '{":date":{"S":"YYYY-MM-DD"}}' \
  --region us-east-1
```

## Goal

30 paper trades minimum before going live. Track by:
- Win rate by signal type (pivot / pullback / range scalp)
- Win rate by quality grade (A / B / C)
- Win rate by level
- Net P&L trend
