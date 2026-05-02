import os
import requests

from src.core.contracts.alerts import AlertProvider
from src.alerts.formatters.signal_card import format_signal_card

_API_BASE = 'https://api.telegram.org/bot{token}/sendMessage'
_TIMEOUT  = 10


class TelegramProvider(AlertProvider):
    def __init__(self, token: str, chat_id: str, risk_engine=None, bucket_engine=None):
        self._token = token
        self._chat_id = chat_id
        self._risk_engine   = risk_engine
        self._bucket_engine = bucket_engine

    # ── AlertProvider interface ───────────────────────────────────────────────

    def send_signal(self, signal: dict) -> bool:
        risk_state   = self._risk_engine.get_daily_state() if self._risk_engine else None
        bucket_stats = self._get_bucket(signal) if self._bucket_engine else None
        text = format_signal_card(signal, risk_state, bucket_stats)
        return self._post(text)

    def send_report(self, report: dict) -> bool:
        date    = report.get('date', '')
        fired   = report.get('signals_fired', 0)
        taken   = report.get('trades_taken', 0)
        pnl     = report.get('daily_pnl', 0.0)
        ks      = report.get('kill_switch_active', False)
        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        ks_str  = '\n⛔ Kill switch active' if ks else ''
        text = (
            f"📈 <b>EOD Report — MES  |  {date}</b>\n\n"
            f"Signals fired: {fired}\n"
            f"Trades taken:  {taken}\n"
            f"Daily P&amp;L:     {pnl_str}{ks_str}"
        )
        return self._post(text)

    def send_error(self, message: str) -> bool:
        return self._post(f"⚠️ {message}")

    def send_text(self, message: str) -> bool:
        return self._post(message)

    # ── internal ─────────────────────────────────────────────────────────────

    def _post(self, text: str) -> bool:
        url = _API_BASE.format(token=self._token)
        try:
            resp = requests.post(
                url,
                json={'chat_id': self._chat_id, 'text': text, 'parse_mode': 'HTML'},
                timeout=_TIMEOUT,
            )
            if not resp.ok:
                print(f"[Telegram] send failed: {resp.status_code} {resp.text[:120]}")
            return resp.ok
        except Exception as exc:
            print(f"[Telegram] send error: {exc}")
            return False

    def _get_bucket(self, signal: dict):
        """Return BucketResult for this signal's near_level + regime, or None."""
        near_level = signal.get('near_level')
        regime     = signal.get('regime')
        if not near_level or not regime:
            return None
        try:
            results = self._bucket_engine.bucket('near_level', 'regime')
            for br in results:
                if br.key.get('near_level') == near_level and br.key.get('regime') == regime:
                    return br
        except Exception:
            pass
        return None
