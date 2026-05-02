import pandas as pd
from src.features.candles import resample


def load_schwab_data() -> tuple[dict[str, pd.DataFrame], pd.DataFrame] | tuple[None, None]:
    """
    Returns (base_data_per_tf, daily_data) or (None, None) if Schwab unavailable.
    base_data_per_tf: dict keyed by entry TF ('1m', '5m', '15m', '1h')
    daily_data: 730-day daily bars used as pivot source for all TF backtests.
    """
    try:
        from src.data import fetch_ohlcv
        daily = fetch_ohlcv('1d', 730)
        if daily.empty:
            raise RuntimeError("No daily data returned")
    except Exception as e:
        print(f"  Schwab unavailable: {e}")
        print("  Skipping short-term backtest — re-authenticate with auth_schwab.py if needed")
        return None, None

    from src.data import fetch_ohlcv

    # Schwab API has no native 1h bar; fetch 30m and resample up.
    configs = {
        '1m':  ('1m',  5),
        '5m':  ('5m',  10),
        '15m': ('15m', 20),
        '1h':  ('30m', 30),
    }

    tf_data = {}
    for entry_tf, (fetch_interval, days_back) in configs.items():
        try:
            df = fetch_ohlcv(fetch_interval, days_back)
            if entry_tf == '1h' and not df.empty:
                df = resample(df, '1h')
            tf_data[entry_tf] = df
            if not df.empty:
                print(f"  Schwab {entry_tf}: {len(df)} bars  "
                      f"|  {df.index[0].date()} → {df.index[-1].date()}")
            else:
                print(f"  Schwab {entry_tf}: no data returned")
        except Exception as e:
            print(f"  Schwab {entry_tf}: fetch failed ({e})")
            tf_data[entry_tf] = pd.DataFrame()

    return tf_data, daily
