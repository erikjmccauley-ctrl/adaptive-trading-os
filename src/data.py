import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SYMBOL_SCHWAB = "/MES"
TOKEN_PATH    = "schwab_token.json"

_schwab_client = None
_initialized   = False

_AGG = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}

_TF_CONFIG = {
    '1m':  {'interval': '1m',  'days_back': 5},
    '5m':  {'interval': '5m',  'days_back': 10},
    '15m': {'interval': '15m', 'days_back': 20},
    '1h':  {'interval': '30m', 'days_back': 30},   # Schwab has no 1h bar; fetch 30m, resample up
    '1d':  {'interval': '1d',  'days_back': 730},
}


def _init_schwab():
    global _schwab_client, _initialized
    if _initialized:
        return

    api_key    = os.getenv('SCHWAB_API_KEY')
    app_secret = os.getenv('SCHWAB_APP_SECRET')

    if not api_key or not app_secret:
        raise RuntimeError("SCHWAB_API_KEY / SCHWAB_APP_SECRET missing from .env")
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(f"{TOKEN_PATH} not found — run auth_schwab.py to authenticate")

    import schwab
    _schwab_client = schwab.auth.easy_client(
        api_key=api_key,
        app_secret=app_secret,
        callback_url='https://127.0.0.1:8182',
        token_path=TOKEN_PATH,
    )
    _initialized = True
    print("  [Schwab] Connected — real-time data active")


def _candles_to_df(candles):
    df = pd.DataFrame(candles)
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df = df.set_index('datetime')
    df.index.name = None
    return df[['open', 'high', 'low', 'close', 'volume']].dropna()


def fetch_ohlcv(interval='5m', days_back=10):
    _init_schwab()
    from schwab.client import Client
    C = Client.PriceHistory

    end   = datetime.now()
    start = end - timedelta(days=days_back)

    if interval == '1d':
        # Schwab Frequency enum has no daily constant. Use period-based request:
        # period=TWO_DAYS (value=2) with period_type=YEAR → 2 years of daily bars.
        # frequency=EVERY_MINUTE (value=1) is the correct integer for daily frequency.
        resp = _schwab_client.get_price_history(
            SYMBOL_SCHWAB,
            period_type=C.PeriodType.YEAR,
            period=C.Period.TWO_DAYS,
            frequency_type=C.FrequencyType.DAILY,
            frequency=C.Frequency.EVERY_MINUTE,
        )
    else:
        freq_map = {
            '1m':  (C.FrequencyType.MINUTE, C.Frequency.EVERY_MINUTE),
            '5m':  (C.FrequencyType.MINUTE, C.Frequency.EVERY_FIVE_MINUTES),
            '15m': (C.FrequencyType.MINUTE, C.Frequency.EVERY_FIFTEEN_MINUTES),
            '30m': (C.FrequencyType.MINUTE, C.Frequency.EVERY_THIRTY_MINUTES),
        }
        ft, f = freq_map[interval]
        resp = _schwab_client.get_price_history(
            SYMBOL_SCHWAB,
            frequency_type=ft,
            frequency=f,
            start_datetime=start,
            end_datetime=end,
            need_extended_hours_data=False,
        )
    data = resp.json()
    if data.get('empty', True) or not data.get('candles'):
        return pd.DataFrame()
    return _candles_to_df(data['candles'])


def _resample_4h(df_1h):
    if df_1h.empty:
        return df_1h
    return df_1h.resample('4h').agg(_AGG).dropna()


def get_multi_tf_data():
    data = {}
    for tf, cfg in _TF_CONFIG.items():
        df = fetch_ohlcv(cfg['interval'], cfg['days_back'])
        if tf == '1h' and not df.empty:
            df = df.resample('1h').agg(_AGG).dropna()
        data[tf] = df

    data['4h'] = _resample_4h(data.get('1h', pd.DataFrame()))
    return data


def get_pivot_source_ohlc():
    daily = fetch_ohlcv('1d', 730)
    if daily.empty:
        raise RuntimeError("No daily data returned from Schwab — check token")
    weekly  = daily.resample('W').agg(_AGG).dropna()
    monthly = daily.resample('ME').agg(_AGG).dropna()
    return {'daily': daily, 'weekly': weekly, 'monthly': monthly}
