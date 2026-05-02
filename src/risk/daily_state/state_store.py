import json
import os
from datetime import date

from src.core.contracts.risk_engine import DailyRiskState


class RiskStateStore:
    def __init__(self, path: str = 'risk/daily_state.json'):
        self._path = path

    def load(self) -> DailyRiskState:
        if os.path.exists(self._path):
            try:
                with open(self._path, 'r') as f:
                    data = json.load(f)
                today = str(date.today())
                if data.get('date') == today:
                    return DailyRiskState(
                        date=data['date'],
                        trades_taken=data.get('trades_taken', 0),
                        daily_pnl=data.get('daily_pnl', 0.0),
                        consecutive_losses=data.get('consecutive_losses', 0),
                        kill_switch_active=data.get('kill_switch_active', False),
                        kill_switch_reason=data.get('kill_switch_reason', ''),
                    )
                # Stale date — new trading day. Preserve kill switch across rollover.
                return DailyRiskState(
                    date=today,
                    trades_taken=0,
                    daily_pnl=0.0,
                    consecutive_losses=0,
                    kill_switch_active=data.get('kill_switch_active', False),
                    kill_switch_reason=data.get('kill_switch_reason', ''),
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return DailyRiskState(
            date=str(date.today()),
            trades_taken=0,
            daily_pnl=0.0,
            consecutive_losses=0,
            kill_switch_active=False,
            kill_switch_reason='',
        )

    def save(self, state: DailyRiskState) -> None:
        os.makedirs(os.path.dirname(self._path) if os.path.dirname(self._path) else '.', exist_ok=True)
        with open(self._path, 'w') as f:
            json.dump({
                'date': state.date,
                'trades_taken': state.trades_taken,
                'daily_pnl': state.daily_pnl,
                'consecutive_losses': state.consecutive_losses,
                'kill_switch_active': state.kill_switch_active,
                'kill_switch_reason': state.kill_switch_reason,
            }, f, indent=2)
