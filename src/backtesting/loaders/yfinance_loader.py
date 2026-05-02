import pandas as pd
import yfinance as yf

SYMBOL_YF = "MES=F"


def load_yfinance_1h() -> pd.DataFrame:
    """Downloads ~2yr of MES 1H bars from yfinance. Returns empty DataFrame on failure."""
    print("  Downloading MES=F 1H bars from yfinance (up to 2yr)...")
    df = yf.Ticker(SYMBOL_YF).history(interval='1h', period='730d')
    if df.empty:
        print("  ERROR: yfinance returned no data — check ticker and internet connection")
        return pd.DataFrame()
    df.columns = [c.lower() for c in df.columns]
    df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    print(f"  Got {len(df)} bars  |  {df.index[0].date()} → {df.index[-1].date()}")
    return df
