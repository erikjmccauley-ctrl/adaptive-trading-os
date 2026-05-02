from src.execution.paper_broker.broker import PaperBroker
from src.execution.tradovate_future.broker import TradovateBroker


def load_paper_broker(storage=None, risk_engine=None, alert_provider=None) -> PaperBroker:
    return PaperBroker(storage, risk_engine, alert_provider)


def load_tradovate_broker(storage=None, risk_engine=None, alert_provider=None) -> TradovateBroker:
    return TradovateBroker(storage, risk_engine, alert_provider)


__all__ = ['PaperBroker', 'load_paper_broker', 'TradovateBroker', 'load_tradovate_broker']
