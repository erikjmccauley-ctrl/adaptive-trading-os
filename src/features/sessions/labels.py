"""
Session labeling — classify any timestamp into its market session.

Used by:
  - Signal scanner: skip first/last 15 min of RTH (per strategy rules)
  - Dashboard: session context on signal cards
  - Feature engine: tag bars by session for intraday analytics

All logic is US Eastern Time (ET). MES trades on CME Globex so the
market session that matters for intraday strategy is Regular Trading Hours (RTH).
"""

from datetime import datetime, time
import pytz

_ET = pytz.timezone('America/New_York')

# RTH boundaries (ET)
_RTH_OPEN  = time(9, 30)
_RTH_CLOSE = time(16, 0)

# Strategy signal windows — skip first and last 15 min per CLAUDE.md
_SIGNAL_START = time(9, 45)
_SIGNAL_END   = time(15, 45)


def _to_et(ts: datetime) -> datetime:
    """Convert a naive or UTC-aware datetime to ET."""
    if ts.tzinfo is None:
        # Assume UTC if naive (Schwab API returns UTC-based ms timestamps)
        ts = pytz.utc.localize(ts)
    return ts.astimezone(_ET)


def get_session(ts: datetime) -> str:
    """
    Classify a timestamp into its market session.

    Returns one of:
      'pre_market'  — before 9:30 ET
      'rth_open'    — 9:30–9:45 ET (first 15 min, typically volatile)
      'rth'         — 9:45–15:45 ET (main session)
      'rth_close'   — 15:45–16:00 ET (last 15 min)
      'after_hours' — after 16:00 ET or weekend
    """
    et = _to_et(ts)
    t  = et.time()

    if et.weekday() >= 5:   # Saturday=5, Sunday=6
        return 'after_hours'
    if t < _RTH_OPEN:
        return 'pre_market'
    if t < _SIGNAL_START:
        return 'rth_open'
    if t < _SIGNAL_END:
        return 'rth'
    if t < _RTH_CLOSE:
        return 'rth_close'
    return 'after_hours'


def is_rth(ts: datetime) -> bool:
    """True if the timestamp falls within Regular Trading Hours (9:30–16:00 ET)."""
    et = _to_et(ts)
    t  = et.time()
    return et.weekday() < 5 and _RTH_OPEN <= t < _RTH_CLOSE


def is_signal_window(ts: datetime) -> bool:
    """
    True if signals are allowed at this time.
    Enforces the strategy rule: skip first and last 15 minutes of RTH.
    """
    et = _to_et(ts)
    t  = et.time()
    return et.weekday() < 5 and _SIGNAL_START <= t < _SIGNAL_END
