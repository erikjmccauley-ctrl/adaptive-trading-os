"""
Config loader — reads from .env (local dev) or AWS Secrets Manager (Lambda).

Usage:
    from src.core.config import get_config
    cfg = get_config()
    key = cfg.schwab_api_key
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class Config:
    # Schwab
    schwab_api_key: str = ''
    schwab_app_secret: str = ''
    schwab_redirect_uri: str = 'https://127.0.0.1:8182'
    schwab_token_path: str = 'schwab_token.json'

    # Telegram
    telegram_bot_token: str = ''
    telegram_chat_id: str = ''

    # AWS
    aws_region: str = 'us-east-1'
    s3_raw_bucket: str = ''
    s3_normalized_bucket: str = ''
    dynamodb_signals_table: str = 'mes-signal-log'
    dynamodb_rules_table: str = ''
    dynamodb_outcomes_table: str = ''
    dynamodb_risk_table: str = ''

    # Tradovate (future — keep disabled)
    tradovate_client_id: str = ''
    tradovate_client_secret: str = ''
    tradovate_environment: str = 'demo'
    live_execution_enabled: bool = False

    # Operating mode
    mode: str = 'paper'       # 'research' | 'paper' | 'live'
    log_level: str = 'INFO'


def _load_from_env() -> Config:
    """Load config from environment variables (set via .env + python-dotenv)."""
    def _bool(key: str, default: bool = False) -> bool:
        return os.getenv(key, str(default)).lower() in ('true', '1', 'yes')

    return Config(
        schwab_api_key=os.getenv('SCHWAB_API_KEY', ''),
        schwab_app_secret=os.getenv('SCHWAB_APP_SECRET', ''),
        schwab_redirect_uri=os.getenv('SCHWAB_REDIRECT_URI', 'https://127.0.0.1:8182'),
        schwab_token_path=os.getenv('SCHWAB_TOKEN_PATH', 'schwab_token.json'),

        telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
        telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID', ''),

        aws_region=os.getenv('AWS_REGION', 'us-east-1'),
        s3_raw_bucket=os.getenv('S3_RAW_BUCKET', ''),
        s3_normalized_bucket=os.getenv('S3_NORMALIZED_BUCKET', ''),
        dynamodb_signals_table=os.getenv('DYNAMODB_SIGNALS_TABLE', 'mes-signal-log'),
        dynamodb_rules_table=os.getenv('DYNAMODB_RULES_TABLE', ''),
        dynamodb_outcomes_table=os.getenv('DYNAMODB_OUTCOMES_TABLE', ''),
        dynamodb_risk_table=os.getenv('DYNAMODB_RISK_TABLE', ''),

        tradovate_client_id=os.getenv('TRADOVATE_CLIENT_ID', ''),
        tradovate_client_secret=os.getenv('TRADOVATE_CLIENT_SECRET', ''),
        tradovate_environment=os.getenv('TRADOVATE_ENVIRONMENT', 'demo'),
        live_execution_enabled=_bool('LIVE_EXECUTION_ENABLED', False),

        mode=os.getenv('TRADING_MODE', 'paper'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
    )


def _load_from_secrets_manager(secret_name: str) -> Config:
    """Load credentials from AWS Secrets Manager (Lambda path)."""
    import json
    import boto3

    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response['SecretString'])

    cfg = _load_from_env()   # get non-secret config from env vars
    cfg.schwab_api_key      = secret.get('schwab_api_key', '')
    cfg.schwab_app_secret   = secret.get('schwab_app_secret', '')
    cfg.telegram_bot_token  = secret.get('bot_token', '')
    cfg.telegram_chat_id    = secret.get('chat_id', '')
    return cfg


@lru_cache(maxsize=1)
def get_config() -> Config:
    """
    Return the singleton Config instance.
    Detects Lambda vs. local by checking for AWS_LAMBDA_FUNCTION_NAME env var.
    """
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        secret_name = os.getenv('SECRETS_MANAGER_SECRET', 'trading-bot/telegram')
        return _load_from_secrets_manager(secret_name)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return _load_from_env()
