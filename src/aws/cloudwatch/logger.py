"""
CloudWatch structured logger.
Emits JSON lines that CloudWatch Logs Insights can query with field filters.
Uses stdlib logging only — no boto3 required. CloudWatch captures Lambda stdout.

Example Insights query:
    fields @timestamp, message.direction, message.near_level
    | filter message.event = "signal_fired"
    | sort @timestamp desc
"""
import json
import logging
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            'level':   record.levelname,
            'logger':  record.name,
            'ts':      datetime.now(timezone.utc).isoformat(),
        }
        msg = record.getMessage()
        try:
            payload['message'] = json.loads(msg)
        except (json.JSONDecodeError, TypeError):
            payload['message'] = msg
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that emits JSON-structured lines for CloudWatch Insights."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_signal(logger: logging.Logger, signal: dict) -> None:
    """Emit a structured signal_fired event."""
    logger.info(json.dumps({
        'event':         'signal_fired',
        'direction':     signal.get('direction'),
        'entry_tf':      signal.get('entry_tf'),
        'near_level':    signal.get('near_level'),
        'quality':       signal.get('quality'),
        'quality_score': signal.get('quality_score'),
        'rr':            signal.get('rr'),
        'regime':        signal.get('regime'),
        'signal_type':   signal.get('signal_type'),
    }))


def log_outcome(logger: logging.Logger, outcome: dict) -> None:
    """Emit a structured trade_resolved event."""
    logger.info(json.dumps({
        'event':       'trade_resolved',
        'signal_id':   outcome.get('signal_id'),
        'outcome':     outcome.get('outcome'),
        'pnl_dollars': outcome.get('pnl_dollars'),
        'r_multiple':  outcome.get('r_multiple'),
        'exit_price':  outcome.get('exit_price'),
    }))


def log_error(logger: logging.Logger, message: str, exc: Exception | None = None) -> None:
    """Emit a structured error event."""
    payload: dict = {'event': 'error', 'message': message}
    if exc:
        payload['exception'] = str(exc)
    logger.error(json.dumps(payload))
