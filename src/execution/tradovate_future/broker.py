"""
Tradovate execution adapter — PLACEHOLDER ONLY.

All methods raise RuntimeError. Nothing here executes until:
  1. LIVE_EXECUTION_ENABLED=true in config
  2. Account balance >= $1,000
  3. Explicit human sign-off on the integration

Do not remove the safety checks. Do not call these methods from any live path.
"""

from src.core.contracts.execution import ExecutionProvider, Order, Fill, Position
from typing import Optional


class TradovateBroker(ExecutionProvider):

    def __init__(self, storage=None, risk_engine=None, alert_provider=None):
        self._storage        = storage
        self._risk_engine    = risk_engine
        self._alert_provider = alert_provider

    def is_enabled(self) -> bool:
        return False   # always False until explicitly unlocked

    def place_order(self, order: Order) -> Fill:
        raise RuntimeError(
            "TradovateBroker is disabled. Set LIVE_EXECUTION_ENABLED=true "
            "and ensure account balance >= $1,000 before enabling."
        )

    def get_position(self, symbol: str) -> Optional[Position]:
        raise RuntimeError("TradovateBroker is disabled.")

    def has_open_position(self) -> bool:
        raise RuntimeError("TradovateBroker is disabled.")

    def flatten_all(self) -> None:
        raise RuntimeError("TradovateBroker is disabled.")

    def get_open_orders(self) -> list:
        raise RuntimeError("TradovateBroker is disabled.")

    def cancel_order(self, order) -> bool:
        raise RuntimeError("TradovateBroker is disabled.")

    def get_daily_pnl(self) -> float:
        raise RuntimeError("TradovateBroker is disabled.")
