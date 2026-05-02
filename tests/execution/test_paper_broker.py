"""
Unit tests for PaperBroker.
No real file I/O — storage and risk_engine are injected mocks.
"""
import pandas as pd
import pytest

from src.core.contracts.execution import Order
from src.execution.paper_broker.broker import PaperBroker, SLIPPAGE_TICKS, TIMEOUT_BARS
from src.execution.paper_broker.order_builder import order_from_signal
from src.signals.constants import MES_POINT_VALUE


# ── helpers ───────────────────────────────────────────────────────────────────

class _MockStorage:
    def __init__(self):
        self.outcomes = []
    def write_outcome(self, o):
        self.outcomes.append(o)
    def read_outcomes(self, days=1):
        return self.outcomes

class _MockRiskEngine:
    def __init__(self):
        self.calls = []
    def update_daily_state(self, outcome):
        self.calls.append(outcome)


def _order(direction='LONG', entry=5000.0, stop=4990.0, target1=5020.0,
           entry_tf='5m', near_level='D_PP'):
    signal_id = f"{entry_tf}:{direction}:{near_level}:120000"
    return Order(symbol='MES', direction=direction, quantity=1,
                 entry_price=entry, stop_price=stop,
                 target1_price=target1, target2_price=None,
                 signal_id=signal_id)


def _broker(storage=None, risk_engine=None):
    return PaperBroker(storage=storage or _MockStorage(),
                       risk_engine=risk_engine or _MockRiskEngine())


def _bar_df(high, low, close, entry_tf='5m', n=2):
    """Build a minimal tf_data dict with a DataFrame whose last bar has the given OHLC."""
    bars = [{'open': close, 'high': close, 'low': close, 'close': close, 'volume': 1000}
            for _ in range(n - 1)]
    bars.append({'open': close, 'high': high, 'low': low, 'close': close, 'volume': 1000})
    return {entry_tf: pd.DataFrame(bars)}


# ── tests ─────────────────────────────────────────────────────────────────────

def test_place_order_creates_position():
    broker = _broker()
    order  = _order()
    broker.place_order(order)
    assert broker.has_open_position()
    pos = broker.get_position('MES')
    assert pos is not None
    assert pos.direction == 'LONG'


def test_fill_price_includes_slippage():
    broker = _broker()
    fill   = broker.place_order(_order(direction='LONG', entry=5000.0))
    assert fill.fill_price == 5000.0 + SLIPPAGE_TICKS * 0.25

    broker2 = _broker()
    fill2   = broker2.place_order(_order(direction='SHORT', entry=5000.0))
    assert fill2.fill_price == 5000.0 - SLIPPAGE_TICKS * 0.25


def test_target_hit_resolves_win():
    storage     = _MockStorage()
    risk_engine = _MockRiskEngine()
    broker      = _broker(storage, risk_engine)
    broker.place_order(_order(direction='LONG', entry=5000.0, stop=4990.0, target1=5020.0))

    # Bar with high above target
    broker.check_positions(_bar_df(high=5025.0, low=4998.0, close=5020.0))

    assert not broker.has_open_position()
    assert len(storage.outcomes) == 1
    assert storage.outcomes[0]['outcome'] == 'WIN'
    assert float(storage.outcomes[0]['pnl_pts']) > 0
    assert len(risk_engine.calls) == 1
    assert risk_engine.calls[0]['result'] == 'WIN'


def test_stop_hit_resolves_loss():
    storage     = _MockStorage()
    risk_engine = _MockRiskEngine()
    broker      = _broker(storage, risk_engine)
    broker.place_order(_order(direction='LONG', entry=5000.0, stop=4990.0, target1=5020.0))

    # Bar with low below stop
    broker.check_positions(_bar_df(high=4999.0, low=4985.0, close=4990.0))

    assert not broker.has_open_position()
    assert storage.outcomes[0]['outcome'] == 'LOSS'
    assert float(storage.outcomes[0]['pnl_pts']) < 0
    assert risk_engine.calls[0]['result'] == 'LOSS'


def test_both_hit_same_bar_is_loss():
    storage = _MockStorage()
    broker  = _broker(storage)
    broker.place_order(_order(direction='LONG', entry=5000.0, stop=4990.0, target1=5020.0))

    # Bar whose range crosses BOTH stop and target
    broker.check_positions(_bar_df(high=5025.0, low=4985.0, close=5000.0))

    assert storage.outcomes[0]['outcome'] == 'LOSS'


def test_timeout_resolves_on_bar_limit():
    storage = _MockStorage()
    broker  = _broker(storage)
    broker.place_order(_order(entry_tf='5m', direction='LONG',
                              entry=5000.0, stop=4990.0, target1=5020.0))

    limit = TIMEOUT_BARS['5m']
    tf_data = _bar_df(high=5005.0, low=4995.0, close=5003.0, entry_tf='5m')

    for _ in range(limit):
        broker.check_positions(tf_data)

    assert not broker.has_open_position()
    assert storage.outcomes[0]['outcome'] == 'TIMEOUT'


def test_resolve_calls_risk_engine():
    risk_engine = _MockRiskEngine()
    broker      = _broker(risk_engine=risk_engine)
    broker.place_order(_order(direction='LONG', entry=5000.0, stop=4990.0, target1=5020.0))
    broker.check_positions(_bar_df(high=5025.0, low=4998.0, close=5020.0))

    assert len(risk_engine.calls) == 1
    call = risk_engine.calls[0]
    assert 'result' in call
    assert 'pnl_dollars' in call
    assert isinstance(call['pnl_dollars'], float)


def test_no_position_check_is_noop():
    storage     = _MockStorage()
    risk_engine = _MockRiskEngine()
    broker      = _broker(storage, risk_engine)
    # No order placed
    broker.check_positions(_bar_df(high=5025.0, low=4985.0, close=5000.0))
    assert len(storage.outcomes) == 0
    assert len(risk_engine.calls) == 0
