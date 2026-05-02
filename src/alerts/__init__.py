import os

from src.alerts.telegram.provider import TelegramProvider


def load_alert_provider(risk_engine=None) -> TelegramProvider | None:
    """
    Returns a TelegramProvider if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set,
    otherwise None (bot runs without Telegram — no crash, no warning).
    """
    token   = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return None

    bucket_engine = None
    try:
        from src.inference.bucket_analysis.bucket_engine import BucketEngine
        bucket_engine = BucketEngine.from_default_csvs()
    except Exception:
        pass

    return TelegramProvider(token, chat_id, risk_engine, bucket_engine)


__all__ = ['TelegramProvider', 'load_alert_provider']
