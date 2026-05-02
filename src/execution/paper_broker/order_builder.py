from datetime import datetime

from src.core.contracts.execution import Order


def order_from_signal(signal: dict) -> Order:
    """Convert a signal dict to an Order. Encodes entry_tf in signal_id for position tracking."""
    ts = datetime.now().strftime('%H%M%S')
    signal_id = (
        f"{signal.get('entry_tf', '')}:"
        f"{signal.get('direction', '')}:"
        f"{signal.get('near_level', '')}:"
        f"{ts}"
    )
    return Order(
        symbol='MES',
        direction=signal['direction'],
        quantity=1,
        entry_price=signal['entry'],
        stop_price=signal['stop'],
        target1_price=signal['target1'],
        target2_price=signal.get('target2'),
        signal_id=signal_id,
    )
