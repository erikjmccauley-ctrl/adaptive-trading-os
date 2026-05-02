from src.risk.daily_state.local_risk_engine import LocalRiskEngine
from src.risk.daily_state.state_store import RiskStateStore


def load_risk_engine(path: str = 'risk/daily_state.json') -> LocalRiskEngine:
    store = RiskStateStore(path)
    return LocalRiskEngine(store)


__all__ = ['LocalRiskEngine', 'RiskStateStore', 'load_risk_engine']
