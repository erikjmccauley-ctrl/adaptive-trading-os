from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class Order:
    symbol: str
    direction: str          # 'LONG' | 'SHORT'
    quantity: int
    entry_price: float
    stop_price: float
    target1_price: float
    target2_price: Optional[float]
    signal_id: str


@dataclass
class Fill:
    order: Order
    fill_price: float
    fill_time: str
    slippage_pts: float


@dataclass
class Position:
    symbol: str
    direction: str
    quantity: int
    entry_price: float
    stop_price: float
    target1_price: float
    target2_price: Optional[float]
    fill_time: str
    unrealized_pnl: float = 0.0


class ExecutionProvider(ABC):
    """
    Abstract interface for all execution backends.
    Implementations: PaperBroker (active), TradovateBroker (future, disabled).
    """

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return True only when this provider is allowed to place orders."""

    @abstractmethod
    def place_order(self, order: Order) -> Fill:
        """Submit an order and return the resulting fill."""

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Return the open position for symbol, or None if flat."""

    @abstractmethod
    def has_open_position(self) -> bool:
        """True if any position is currently open."""

    @abstractmethod
    def flatten_all(self) -> None:
        """Emergency close of all open positions at market."""

    @abstractmethod
    def get_open_orders(self) -> list[Order]:
        """Return all open (unfilled) orders. Empty list if none."""

    @abstractmethod
    def cancel_order(self, order: Order) -> bool:
        """
        Cancel an open order.
        Returns True if successfully cancelled, False if already filled or not found.
        """

    @abstractmethod
    def get_daily_pnl(self) -> float:
        """Realized P/L for today in dollars."""
