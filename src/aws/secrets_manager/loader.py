"""
AWS Secrets Manager credential loader.
Falls back gracefully when boto3 is unavailable (local dev) or when
AWS credentials are not configured. Callers always get a dict — never an exception.

Secret format expected in Secrets Manager (trading-bot/telegram):
{
    "bot_token":         "...",
    "chat_id":           "...",
    "schwab_api_key":    "...",
    "schwab_app_secret": "..."
}
"""
import json
import os

_DEFAULT_SECRET = 'trading-bot/telegram'
_DEFAULT_REGION = 'us-east-1'


def load_secret(
    secret_name: str = _DEFAULT_SECRET,
    region: str = _DEFAULT_REGION,
) -> dict:
    """
    Fetch a Secrets Manager secret and return it as a dict.
    Returns {} if boto3 is not installed, credentials are missing,
    or the secret fetch fails for any reason.
    """
    try:
        import boto3
        client = boto3.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        raw = response.get('SecretString', '{}')
        return json.loads(raw)
    except ImportError:
        return {}
    except Exception:
        return {}


def load_telegram_credentials(
    secret_name: str = _DEFAULT_SECRET,
    region: str = _DEFAULT_REGION,
) -> dict:
    """
    Return Telegram credentials: {'bot_token': str, 'chat_id': str}.
    Falls back to TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID env vars if secret unavailable.
    """
    secret = load_secret(secret_name, region)
    return {
        'bot_token': secret.get('bot_token') or os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'chat_id':   secret.get('chat_id')   or os.getenv('TELEGRAM_CHAT_ID', ''),
    }


def load_schwab_credentials(
    secret_name: str = _DEFAULT_SECRET,
    region: str = _DEFAULT_REGION,
) -> dict:
    """
    Return Schwab credentials: {'schwab_api_key': str, 'schwab_app_secret': str}.
    Falls back to SCHWAB_API_KEY / SCHWAB_APP_SECRET env vars if secret unavailable.
    """
    secret = load_secret(secret_name, region)
    return {
        'schwab_api_key':    secret.get('schwab_api_key')    or os.getenv('SCHWAB_API_KEY', ''),
        'schwab_app_secret': secret.get('schwab_app_secret') or os.getenv('SCHWAB_APP_SECRET', ''),
    }
