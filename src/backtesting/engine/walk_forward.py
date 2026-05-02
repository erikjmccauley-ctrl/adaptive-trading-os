from dataclasses import dataclass, field
import pandas as pd

from src.features.candles import build_higher_tfs, resample
from src.features.indicators import get_all_pivots
from src.signals import generate_signals

MES_POINT_VALUE = 5.0
SMMA_WINDOW     = 600   # rolling base-TF bars for SMMA (600x1H ≈ 38 calendar days)
PIVOT_WINDOW    = 2000  # rolling base-TF bars for pivot derivation (yfinance path)

TIMEOUT_BARS = {
    '1m':  60,   # 1 hour
    '5m':  24,   # 2 hours
    '15m': 16,   # 4 hours
    '1h':  48,   # 2 trading days
}


@dataclass
class TradeState:
    entry:     float
    stop:      float
    target1:   float
    direction: str    # 'LONG' | 'SHORT'
    risk:      float  # abs(entry - stop), locked at entry
    entry_idx: int
    entry_ts:  object
    signal:    dict   # full signal dict — carries metadata into the trade record

    # Running accumulators
    current_stop:  float = 0.0   # may trail upward/downward
    mfe_pts:       float = 0.0
    mae_pts:       float = 0.0
    bars_held:     int   = 0
    reached_0_5r:  bool  = False
    reached_1r:    bool  = False
    reached_2r:    bool  = False
    reached_3r:    bool  = False

    def __post_init__(self):
        self.current_stop = self.stop


class TradeResolver:
    def __init__(self, timeout_bars: int, trailing_stop: bool = False):
        self._timeout  = timeout_bars
        self._trailing = trailing_stop

    def update(self, state: TradeState, bar: pd.Series, bar_idx: int) -> str | None:
        """
        Update running MFE/MAE/R-milestone accumulators.
        Return 'WIN' | 'LOSS' | 'TIMEOUT' | None (trade still open).
        Conservative: if stop and target both hit in same bar → LOSS.
        """
        hi  = float(bar['high'])
        lo  = float(bar['low'])
        cls = float(bar['close'])

        state.bars_held += 1

        # MFE / MAE
        if state.direction == 'LONG':
            favorable = hi - state.entry
            adverse   = state.entry - lo
        else:
            favorable = state.entry - lo
            adverse   = hi - state.entry

        if favorable > state.mfe_pts:
            state.mfe_pts = favorable
        if adverse > state.mae_pts:
            state.mae_pts = adverse

        # R-milestone flags
        if state.risk > 0:
            for mult, attr in ((0.5, 'reached_0_5r'), (1.0, 'reached_1r'),
                               (2.0, 'reached_2r'),   (3.0, 'reached_3r')):
                if favorable >= mult * state.risk:
                    setattr(state, attr, True)

        # Trailing stop logic — moves stop to breakeven after 1R, to 1R after 2R
        if self._trailing and state.risk > 0:
            if state.reached_2r:
                trail_level = state.entry + state.risk if state.direction == 'LONG' else state.entry - state.risk
            elif state.reached_1r:
                trail_level = state.entry
            else:
                trail_level = None
            if trail_level is not None:
                if state.direction == 'LONG':
                    state.current_stop = max(state.current_stop, trail_level)
                else:
                    state.current_stop = min(state.current_stop, trail_level)

        # Resolve
        if state.direction == 'LONG':
            hit_stop   = lo <= state.current_stop
            hit_target = hi >= state.target1
        else:
            hit_stop   = hi >= state.current_stop
            hit_target = lo <= state.target1

        if hit_stop and hit_target:
            return 'LOSS'   # conservative: both hit same bar → stop wins
        if hit_stop:
            return 'LOSS'
        if hit_target:
            return 'WIN'
        if (bar_idx - state.entry_idx) >= self._timeout:
            return 'TIMEOUT'
        return None

    def exit_price(self, state: TradeState, outcome: str, bar_close: float) -> float:
        if outcome == 'WIN':
            return state.target1
        if outcome == 'LOSS':
            return state.current_stop
        return bar_close  # TIMEOUT: mark-to-market

    def to_trade_record(self, state: TradeState, outcome: str,
                        exit_price: float, exit_ts) -> dict:
        pnl_pts = (exit_price - state.entry) if state.direction == 'LONG' \
                  else (state.entry - exit_price)
        mfe_r = round(state.mfe_pts / state.risk, 2) if state.risk > 0 else None
        mae_r = round(state.mae_pts / state.risk, 2) if state.risk > 0 else None
        r_mul = round(pnl_pts / state.risk, 2)       if state.risk > 0 else None

        sig = state.signal
        return {
            # Existing fields
            'entry_ts':      state.entry_ts,
            'entry':         state.entry,
            'stop':          state.stop,
            'target1':       state.target1,
            'target1_name':  sig.get('target1_name'),
            'direction':     state.direction,
            'entry_tf':      sig.get('entry_tf'),
            'rr':            sig.get('rr'),
            'near_level':    sig.get('near_level'),
            'outcome':       outcome,
            'exit_price':    round(exit_price, 2),
            'exit_ts':       exit_ts,
            'pnl_pts':       round(pnl_pts, 2),
            'pnl_dollars':   round(pnl_pts * MES_POINT_VALUE, 2),
            # New Phase 7 fields
            'risk_pts':      round(state.risk, 2),
            'mfe_pts':       round(state.mfe_pts, 2),
            'mae_pts':       round(state.mae_pts, 2),
            'mfe_r':         mfe_r,
            'mae_r':         mae_r,
            'r_multiple':    r_mul,
            'bars_held':     state.bars_held,
            'reached_0_5r':  state.reached_0_5r,
            'reached_1r':    state.reached_1r,
            'reached_2r':    state.reached_2r,
            'reached_3r':    state.reached_3r,
            # Signal metadata
            'signal_type':   sig.get('signal_type'),
            'quality':       sig.get('quality'),
            'regime':        sig.get('regime'),
            'adx':           sig.get('adx'),
        }


def walk_forward(
    base_data: pd.DataFrame,
    entry_tf: str,
    daily_data: pd.DataFrame | None = None,
    warmup_bars: int = 50,
    trailing_stop: bool = False,
) -> list[dict]:
    """
    Walk-forward simulation. No lookahead — pivots and SMMAs computed strictly
    from data available at each bar.

    base_data    : DataFrame at entry_tf bar resolution (OHLCV)
    entry_tf     : '1m' | '5m' | '15m' | '1h'
    daily_data   : Pre-fetched daily bars used as pivot source (Schwab path).
                   Pass None to derive pivots from base_data (yfinance path).
    warmup_bars  : Bars skipped at the start for SMMA convergence.
    trailing_stop: If True, stop trails to breakeven after 1R, to 1R after 2R.
    Returns list of trade record dicts.
    """
    timeout  = TIMEOUT_BARS.get(entry_tf, 48)
    resolver = TradeResolver(timeout, trailing_stop)
    n        = len(base_data)
    trades   = []
    state    = None   # TradeState | None

    for i in range(warmup_bars, n):
        bar = base_data.iloc[i]

        # ── Resolve open trade ─────────────────────────────────────────────
        if state is not None:
            outcome = resolver.update(state, bar, i)
            if outcome is not None:
                ep     = resolver.exit_price(state, outcome, float(bar['close']))
                record = resolver.to_trade_record(state, outcome, ep, base_data.index[i])
                trades.append(record)
                state = None
            continue

        # ── Build TF slices (no lookahead) ────────────────────────────────
        s0   = max(0, i - SMMA_WINDOW + 1)
        hist = base_data.iloc[s0:i + 1]

        tf_data = build_higher_tfs(hist, entry_tf)

        # ── Pivot source ───────────────────────────────────────────────────
        if daily_data is not None:
            # Schwab path: slice pre-fetched daily bars up to current bar's date.
            bar_date = base_data.index[i].date()
            pv_1d    = daily_data[daily_data.index.date <= bar_date]
        else:
            # yfinance path: resample base_data to daily within the pivot window.
            p0    = max(0, i - PIVOT_WINDOW + 1)
            pv_1d = resample(base_data.iloc[p0:i + 1], '1d')

        pv_1w = resample(pv_1d, 'W')
        pv_1m = resample(pv_1d, 'ME')

        if len(pv_1d) < 3 or len(pv_1w) < 2 or len(pv_1m) < 2:
            continue

        pivots = get_all_pivots({'daily': pv_1d, 'weekly': pv_1w, 'monthly': pv_1m})
        if not pivots:
            continue

        signals = generate_signals(tf_data, pivots)
        if not signals:
            continue

        sig  = signals[0]   # take highest R/R signal
        risk = abs(sig['entry'] - sig['stop'])
        state = TradeState(
            entry     = sig['entry'],
            stop      = sig['stop'],
            target1   = sig['target1'],
            direction = sig['direction'],
            risk      = risk,
            entry_idx = i,
            entry_ts  = base_data.index[i],
            signal    = sig,
        )

    return trades
