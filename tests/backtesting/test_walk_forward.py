"""
Smoke test for walk_forward(). No network calls — uses synthetic price data.
Verifies: returns list of dicts, all Phase 7 fields present, field types correct,
TradeState and TradeResolver are importable.
"""
import numpy as np
import pandas as pd
import pytest

from src.backtesting import walk_forward, print_report
from src.backtesting.engine.walk_forward import TradeState, TradeResolver


PHASE_7_FIELDS = {
    "entry_ts", "entry", "stop", "target1", "direction", "entry_tf",
    "rr", "outcome", "exit_price", "exit_ts", "pnl_pts", "pnl_dollars",
    "risk_pts", "mfe_pts", "mae_pts", "mfe_r", "mae_r", "r_multiple",
    "bars_held", "reached_0_5r", "reached_1r", "reached_2r", "reached_3r",
    "signal_type", "quality", "regime", "adx",
}


def _make_synthetic_df(n=300, seed=42):
    np.random.seed(seed)
    dates = pd.date_range("2025-01-02 09:30", periods=n, freq="1h")
    close = 5000 + np.cumsum(np.random.randn(n) * 8)
    spread = np.abs(np.random.randn(n) * 3) + 1
    return pd.DataFrame(
        {
            "open": close - spread / 2,
            "high": close + spread,
            "low": close - spread,
            "close": close,
            "volume": np.random.randint(500, 5000, n).astype(float),
        },
        index=dates,
    )


def test_imports():
    assert callable(walk_forward)
    assert callable(print_report)
    assert TradeState is not None
    assert TradeResolver is not None


def test_walk_forward_returns_list():
    df = _make_synthetic_df()
    trades = walk_forward(df, "1h", warmup_bars=50)
    assert isinstance(trades, list)


def test_walk_forward_trade_fields():
    df = _make_synthetic_df()
    trades = walk_forward(df, "1h", warmup_bars=50)
    if not trades:
        pytest.skip("No trades generated on synthetic data — increase bars or lower warmup")
    for field in PHASE_7_FIELDS:
        assert field in trades[0], f"Missing Phase 7 field: {field}"


def test_walk_forward_field_types():
    df = _make_synthetic_df()
    trades = walk_forward(df, "1h", warmup_bars=50)
    if not trades:
        pytest.skip("No trades generated on synthetic data")
    t = trades[0]
    assert isinstance(t["mfe_pts"], float)
    assert isinstance(t["mae_pts"], float)
    assert isinstance(t["r_multiple"], float)
    assert isinstance(t["bars_held"], int)
    assert isinstance(t["reached_1r"], bool)
    assert t["outcome"] in ("WIN", "LOSS", "TIMEOUT")
    assert t["direction"] in ("LONG", "SHORT")


def test_walk_forward_no_lookahead_warmup():
    # Verify warmup_bars is respected: reduce bars so barely enough for warmup
    df = _make_synthetic_df(n=60)
    trades = walk_forward(df, "1h", warmup_bars=50)
    # Should not crash even with tiny dataset
    assert isinstance(trades, list)


def test_trailing_stop_flag():
    df = _make_synthetic_df()
    # Should not raise
    trades = walk_forward(df, "1h", warmup_bars=50, trailing_stop=True)
    assert isinstance(trades, list)


def test_print_report_returns_dataframe():
    df = _make_synthetic_df()
    trades = walk_forward(df, "1h", warmup_bars=50)
    if not trades:
        pytest.skip("No trades generated on synthetic data")
    result = print_report(trades, "Smoke test")
    assert hasattr(result, "columns"), "print_report should return a DataFrame"


# --- TradeResolver unit tests (no signal generation needed) ---

def _make_trade_state(direction="LONG", entry=5000.0, stop=4990.0, target=5020.0):
    sig = {
        "entry_tf": "1h", "rr": 2.0, "near_level": "D_PP",
        "signal_type": "pivot", "quality": "A", "regime": "trending", "adx": 28.0,
        "target1_name": "D_R1",
    }
    state = TradeState(
        entry=entry, stop=stop, target1=target,
        direction=direction, risk=abs(entry - stop),
        entry_idx=0, entry_ts=pd.Timestamp("2025-01-02 10:30"),
        signal=sig,
    )
    return state


def test_resolver_win():
    resolver = TradeResolver(timeout_bars=48)
    state = _make_trade_state()
    bar = pd.Series({"open": 5001, "high": 5025, "low": 5001, "close": 5020, "volume": 1000})
    result = resolver.update(state, bar, bar_idx=1)
    assert result == "WIN"
    assert state.mfe_pts > 0
    assert state.bars_held == 1


def test_resolver_loss():
    resolver = TradeResolver(timeout_bars=48)
    state = _make_trade_state()
    bar = pd.Series({"open": 4999, "high": 4999, "low": 4985, "close": 4990, "volume": 1000})
    result = resolver.update(state, bar, bar_idx=1)
    assert result == "LOSS"
    assert state.mae_pts > 0


def test_resolver_both_hit_same_bar_is_loss():
    resolver = TradeResolver(timeout_bars=48)
    state = _make_trade_state()
    # Bar that hits both stop (low ≤ 4990) and target (high ≥ 5020)
    bar = pd.Series({"open": 5000, "high": 5025, "low": 4985, "close": 5000, "volume": 1000})
    result = resolver.update(state, bar, bar_idx=1)
    assert result == "LOSS", "Conservative rule: both hit same bar → LOSS"


def test_resolver_timeout():
    resolver = TradeResolver(timeout_bars=5)
    state = _make_trade_state()
    bar = pd.Series({"open": 5002, "high": 5005, "low": 4995, "close": 5002, "volume": 1000})
    for i in range(1, 6):
        result = resolver.update(state, bar, bar_idx=i)
    assert result == "TIMEOUT"


def test_resolver_r_milestones():
    resolver = TradeResolver(timeout_bars=48)
    state = _make_trade_state(entry=5000, stop=4990, target=5020)  # risk=10
    # High reaches 5015 = 1.5R
    bar = pd.Series({"open": 5001, "high": 5015, "low": 5001, "close": 5010, "volume": 1000})
    resolver.update(state, bar, bar_idx=1)
    assert state.reached_0_5r is True   # 0.5R = 5005
    assert state.reached_1r is True     # 1R  = 5010
    assert state.reached_2r is False    # 2R  = 5020 — not reached


def test_resolver_trade_record_fields():
    resolver = TradeResolver(timeout_bars=48)
    state = _make_trade_state()
    bar = pd.Series({"open": 5001, "high": 5025, "low": 5001, "close": 5020, "volume": 1000})
    outcome = resolver.update(state, bar, bar_idx=1)
    exit_p = resolver.exit_price(state, outcome, bar["close"])
    record = resolver.to_trade_record(state, outcome, exit_p, pd.Timestamp("2025-01-02 11:30"))
    for field in PHASE_7_FIELDS:
        assert field in record, f"Missing field in trade record: {field}"
