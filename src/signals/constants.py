MIN_RR               = 2.0
MIN_RR_SCALP         = 1.5
PROXIMITY_ATR        = 0.6
MIN_VOLUME_RATIO     = 0.5
VOLUME_DIRECTION_BARS = 5
ADX_TRENDING         = 25
ADX_RANGING          = 18
ATR_CONSUMED_LIMIT   = 0.90
ATR_OVEREXTENDED     = 1.10
ACCOUNT_BALANCE      = 250.00   # update as account grows
SWING_UNLOCK_BALANCE = 3500.00
MES_POINT_VALUE      = 5.0

CONFIRMATION_MAP = {
    '1m':  ['5m', '15m'],
    '5m':  ['15m', '1h'],
    '15m': ['1h', '4h'],
    '1h':  ['4h', '1d'],
    '4h':  ['1d'],
    '1d':  [],
}

INTRADAY_ONLY = ['1m', '5m', '15m', '1h']
SWING_TFS     = ['4h', '1d']

TF_LABEL = {
    '1m':  '1m  (scalp)',
    '5m':  '5m  (scalp)',
    '15m': '15m (intraday)',
    '1h':  '1H  (intraday)',
    '4h':  '4H  (swing)',
    '1d':  'Daily (swing)',
}

# Levels with confirmed negative edge from backtest inference (0% win rate, n >= 5).
# Signals at these levels are suppressed until evidence improves.
# Source: inference engine — update via `python -X utf8 inference.py` after each batch.
LEVEL_BLACKLIST: set[str] = {
    'D_FR1',   # 0/9 wins across all TFs
    'D_S2',    # 0/5 wins across all TFs
}

TF_DISPLAY = {
    '1m':  ['5m', '15m', '1h'],
    '5m':  ['15m', '1h', '1d'],
    '15m': ['1h', '4h', '1d'],
    '1h':  ['4h', '1d'],
    '4h':  ['1d'],
    '1d':  ['1d'],
}
