from abc import ABC, abstractmethod


class AlertProvider(ABC):
    """
    Abstract interface for all notification backends.
    Implementations: TelegramProvider (active), TerminalProvider (local dev).
    """

    @abstractmethod
    def send_signal(self, signal: dict) -> bool:
        """
        Format and deliver a trade signal.
        Returns True on success, False on delivery failure.
        """

    @abstractmethod
    def send_report(self, report: dict) -> bool:
        """
        Format and deliver an end-of-day summary report.
        Returns True on success.
        """

    @abstractmethod
    def send_error(self, message: str) -> bool:
        """
        Deliver an error/warning notification.
        Used for Lambda failures, token expiry, data gaps, kill switch events.
        """

    @abstractmethod
    def send_text(self, message: str) -> bool:
        """Send a raw text message (debug / status)."""
