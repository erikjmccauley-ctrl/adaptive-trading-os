"""
RegimeClassifier — standalone ADX-based market regime detector.

Wraps calc_adx() and returns a typed RegimeResult so the dashboard,
inference engine, and future rule engine can query the regime without
importing the full signal generation stack.
"""

from dataclasses import dataclass
from src.features.indicators import calc_adx

import pandas as pd


@dataclass
class RegimeResult:
    adx: float
    regime: str    # 'trending' | 'neutral' | 'ranging'
    adx_tf: str    # which TF the ADX was measured on


# Confirmation TF used for ADX measurement per entry TF — mirrors CONFIRMATION_MAP in signals
_ADX_TF_MAP = {
    '1m':  '15m',
    '5m':  '1h',
    '15m': '4h',
    '1h':  '1d',
    '4h':  '1d',
    '1d':  '1d',
}


class RegimeClassifier:
    """
    Determines the current market regime for a given entry timeframe.

    Usage:
        classifier = RegimeClassifier()
        result = classifier.classify(tf_data, entry_tf='5m')
        print(result.regime)   # 'trending' | 'neutral' | 'ranging'
        print(result.adx)      # e.g. 28.4
    """

    def __init__(self, adx_trending: float = 25.0, adx_ranging: float = 18.0):
        self.adx_trending = adx_trending
        self.adx_ranging  = adx_ranging

    def classify(self, tf_data: dict[str, pd.DataFrame], entry_tf: str) -> RegimeResult:
        """
        Compute ADX on the appropriate confirmation TF and classify the regime.
        Returns RegimeResult with regime='neutral' if data is insufficient.
        """
        adx_tf = _ADX_TF_MAP.get(entry_tf, entry_tf)
        df     = tf_data.get(adx_tf)

        if df is None or df.empty or len(df) < 30:
            return RegimeResult(adx=0.0, regime='neutral', adx_tf=adx_tf)

        try:
            adx_val = calc_adx(df)
        except Exception:
            return RegimeResult(adx=0.0, regime='neutral', adx_tf=adx_tf)

        if adx_val >= self.adx_trending:
            regime = 'trending'
        elif adx_val < self.adx_ranging:
            regime = 'ranging'
        else:
            regime = 'neutral'

        return RegimeResult(adx=round(adx_val, 1), regime=regime, adx_tf=adx_tf)

    def classify_from_df(self, df: pd.DataFrame, adx_tf: str) -> RegimeResult:
        """
        Classify regime directly from a single DataFrame (when tf_data dict isn't available).
        """
        if df is None or df.empty or len(df) < 30:
            return RegimeResult(adx=0.0, regime='neutral', adx_tf=adx_tf)
        try:
            adx_val = calc_adx(df)
        except Exception:
            return RegimeResult(adx=0.0, regime='neutral', adx_tf=adx_tf)

        if adx_val >= self.adx_trending:
            regime = 'trending'
        elif adx_val < self.adx_ranging:
            regime = 'ranging'
        else:
            regime = 'neutral'

        return RegimeResult(adx=round(adx_val, 1), regime=regime, adx_tf=adx_tf)
