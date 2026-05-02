from datetime import date

from src.core.contracts.risk_engine import DailyRiskState, RiskEngine
from src.risk.daily_state.state_store import RiskStateStore
from src.risk.limits import (  # src/risk/limits/__init__.py
    MAX_CONSECUTIVE_LOSSES,
    MAX_DAILY_LOSS_PCT,
    MAX_TRADES_PER_DAY,
    MIN_QUALITY_SCORE,
)


class LocalRiskEngine(RiskEngine):
    def __init__(self, store: RiskStateStore):
        self._store = store

    # ── gating ───────────────────────────────────────────────────────────────

    def validate_trade_intent(self, signal: dict) -> tuple[bool, str]:
        state = self._store.load()
        if state.kill_switch_active:
            return False, f'Kill switch active: {state.kill_switch_reason}'
        if state.trades_taken >= MAX_TRADES_PER_DAY:
            return False, f'Daily trade limit reached ({MAX_TRADES_PER_DAY})'
        if MIN_QUALITY_SCORE > 0:
            score = signal.get('quality_score', 0)
            if score < MIN_QUALITY_SCORE:
                return False, f'Quality score {score} below minimum {MIN_QUALITY_SCORE}'
        return True, ''

    # ── state updates ─────────────────────────────────────────────────────────

    def record_signal_fired(self) -> None:
        """Increment trade counter when a signal is displayed. Called by main.py."""
        state = self._store.load()
        state.trades_taken += 1
        self._store.save(state)

    def update_daily_state(self, outcome: dict) -> None:
        """Record a resolved trade outcome. Called by Phase 12 paper broker."""
        state = self._store.load()
        pnl = outcome.get('pnl_dollars', 0.0)
        state.daily_pnl += pnl
        if outcome.get('result') == 'LOSS':
            state.consecutive_losses += 1
        else:
            state.consecutive_losses = 0
        if state.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            state.kill_switch_active = True
            state.kill_switch_reason = f'Auto: {MAX_CONSECUTIVE_LOSSES} consecutive losses'
        from src.signals.constants import ACCOUNT_BALANCE
        if state.daily_pnl <= -(ACCOUNT_BALANCE * MAX_DAILY_LOSS_PCT):
            state.kill_switch_active = True
            state.kill_switch_reason = 'Auto: daily loss limit breached'
        self._store.save(state)

    # ── manual controls ───────────────────────────────────────────────────────

    def trigger_kill_switch(self, reason: str) -> None:
        state = self._store.load()
        state.kill_switch_active = True
        state.kill_switch_reason = reason
        self._store.save(state)

    def reset_daily_state(self) -> None:
        """Reset trades/pnl/losses for a new day. Does NOT clear kill switch."""
        state = self._store.load()
        state.date = str(date.today())
        state.trades_taken = 0
        state.daily_pnl = 0.0
        state.consecutive_losses = 0
        self._store.save(state)

    # ── read ──────────────────────────────────────────────────────────────────

    def get_daily_state(self) -> DailyRiskState:
        return self._store.load()

    def is_kill_switch_active(self) -> bool:
        return self._store.load().kill_switch_active
