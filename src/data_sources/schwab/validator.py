"""
OHLCV validation and gap detection for Schwab API responses.
Called by SchwabProvider before returning data to callers.
"""

from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd


# Minimum bars required for each TF before the DataFrame is considered usable
# (SMMA21 needs at least 21 bars to converge; padding for safety)
MIN_BARS = {
    '1m':  30,
    '5m':  30,
    '15m': 30,
    '1h':  30,
    '4h':  20,
    '1d':  14,
}

# Expected bar spacing in minutes (used for gap detection)
TF_MINUTES = {
    '1m':  1,
    '5m':  5,
    '15m': 15,
    '1h':  60,
    '4h':  240,
    '1d':  1440,
}

REQUIRED_COLUMNS = {'open', 'high', 'low', 'close', 'volume'}


@dataclass
class ValidationResult:
    tf: str
    original_bars: int
    valid_bars: int
    nan_rows_dropped: int
    gaps: list[tuple] = field(default_factory=list)  # (gap_start, gap_end) pairs
    warnings: list[str] = field(default_factory=list)
    is_usable: bool = True

    def __str__(self):
        status = 'OK' if self.is_usable else 'UNUSABLE'
        parts = [
            f"[{self.tf}] {status}  {self.valid_bars} bars",
        ]
        if self.nan_rows_dropped:
            parts.append(f"{self.nan_rows_dropped} NaN rows dropped")
        if self.gaps:
            parts.append(f"{len(self.gaps)} gap(s) detected")
        return '  |  '.join(parts)


def validate_ohlcv(df: pd.DataFrame, tf: str) -> tuple[pd.DataFrame, ValidationResult]:
    """
    Validate and clean an OHLCV DataFrame from Schwab.

    Returns (cleaned_df, result) where result describes what was found/fixed.
    If the DataFrame is unusable (missing columns, too few bars), is_usable=False.
    Callers should check result.is_usable before proceeding.
    """
    result = ValidationResult(
        tf=tf,
        original_bars=len(df),
        valid_bars=0,
    )

    if df.empty:
        result.is_usable = False
        result.warnings.append("Empty DataFrame returned from API")
        return df, result

    # Check required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        result.is_usable = False
        result.warnings.append(f"Missing columns: {missing}")
        return df, result

    # Strip timezone if present (keep index timezone-naive for consistency)
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df = df.copy()
        df.index = df.index.tz_localize(None)

    # Drop NaN rows
    before = len(df)
    df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
    result.nan_rows_dropped = before - len(df)

    # Drop rows with zero or negative prices (data corruption)
    price_cols = ['open', 'high', 'low', 'close']
    bad_price = (df[price_cols] <= 0).any(axis=1)
    if bad_price.any():
        result.warnings.append(f"{bad_price.sum()} rows with zero/negative price dropped")
        df = df[~bad_price]

    result.valid_bars = len(df)

    # Minimum bar check
    min_bars = MIN_BARS.get(tf, 30)
    if result.valid_bars < min_bars:
        result.is_usable = False
        result.warnings.append(
            f"Only {result.valid_bars} bars — need {min_bars} minimum for {tf}"
        )

    # Gap detection (only for intraday TFs where gaps during RTH are suspicious)
    if tf in TF_MINUTES and tf != '1d' and len(df) >= 2:
        result.gaps = _detect_gaps(df, tf)
        if result.gaps:
            result.warnings.append(f"{len(result.gaps)} time gap(s) in {tf} data")

    return df, result


def _detect_gaps(df: pd.DataFrame, tf: str) -> list[tuple]:
    """
    Find time windows where bars are missing beyond 2× the expected bar spacing.
    Skips gaps that span a weekend or obvious off-hours window.
    Returns list of (gap_start, gap_end) tuples.
    """
    expected_minutes = TF_MINUTES[tf]
    threshold_minutes = expected_minutes * 2.5   # allow some wiggle for rounding
    gaps = []

    times = df.index.to_series()
    deltas = times.diff().dropna()

    for ts, delta in deltas.items():
        delta_minutes = delta.total_seconds() / 60
        if delta_minutes > threshold_minutes:
            gap_start = times[times.index < ts].iloc[-1]
            gap_end = ts
            # Skip weekend gaps (Friday close → Monday open)
            if gap_start.weekday() == 4 and gap_end.weekday() == 0:
                continue
            # Skip overnight gaps (gap > 8h is just close-to-open)
            if delta_minutes > 480:
                continue
            gaps.append((gap_start, gap_end))

    return gaps
