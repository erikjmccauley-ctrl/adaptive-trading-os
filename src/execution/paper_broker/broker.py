from datetime import datetime
from typing import Optional

from src.core.contracts.execution import ExecutionProvider, Fill, Order, Position
from src.signals.constants import MES_POINT_VALUE

SLIPPAGE_TICKS = 1        # 1 tick = 0.25 pts = $1.25
FEE_PER_SIDE   = 0.35     # MES commission estimate per side
TIMEOUT_BARS   = {'1m': 60, '5m': 24, '15m': 16, '1h': 48, '4h': 12, '1d': 5}


class PaperBroker(ExecutionProvider):
    """
    Simulated broker for paper trading.
    Fills are fake (entry ± 1 tick slippage). Positions are resolved by monitoring
    bar high/low on each scanner tick. Outcomes are written to LocalStorage and fed
    to the risk engine.
    """

    def __init__(self, storage=None, risk_engine=None, alert_provider=None):
        self._storage        = storage
        self._risk_engine    = risk_engine
        self._alert_provider = alert_provider
        self._position: Optional[Position] = None
        self._signal_id: str  = ''
        self._entry_tf: str   = ''
        self._fill_price: float = 0.0
        self._bars_held: int  = 0

    # ── ExecutionProvider interface ───────────────────────────────────────────

    def is_enabled(self) -> bool:
        return True

    def place_order(self, order: Order) -> Fill:
        slippage_pts = SLIPPAGE_TICKS * 0.25
        if order.direction == 'LONG':
            fill_price = order.entry_price + slippage_pts
        else:
            fill_price = order.entry_price - slippage_pts

        self._position = Position(
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            entry_price=order.entry_price,
            stop_price=order.stop_price,
            target1_price=order.target1_price,
            target2_price=order.target2_price,
            fill_time=datetime.now().isoformat(),
        )
        self._signal_id  = order.signal_id
        self._entry_tf   = order.signal_id.split(':')[0]  # encoded by order_from_signal
        self._fill_price = fill_price
        self._bars_held  = 0

        print(f"  [PAPER] Filled {order.direction} MES @ {fill_price:.2f} "
              f"| Stop {order.stop_price:.2f} | T1 {order.target1_price:.2f}")

        return Fill(order=order, fill_price=fill_price,
                    fill_time=datetime.now().isoformat(), slippage_pts=slippage_pts)

    def check_positions(self, tf_data: dict) -> None:
        """Called every scan. Checks latest bar for stop/target hits."""
        if self._position is None:
            return

        df = tf_data.get(self._entry_tf)
        if df is None or df.empty or len(df) < 2:
            return

        bar = df.iloc[-1]
        bar_high  = float(bar['high'])
        bar_low   = float(bar['low'])
        bar_close = float(bar['close'])
        pos = self._position

        timeout_limit = TIMEOUT_BARS.get(self._entry_tf, 48)
        self._bars_held += 1

        if pos.direction == 'LONG':
            stop_hit   = bar_low  <= pos.stop_price
            target_hit = bar_high >= pos.target1_price
        else:
            stop_hit   = bar_high >= pos.stop_price
            target_hit = bar_low  <= pos.target1_price

        # Both hit same bar → LOSS (conservative, consistent with backtest)
        if stop_hit and target_hit:
            pnl_pts = pos.stop_price - self._fill_price if pos.direction == 'LONG' \
                      else self._fill_price - pos.stop_price
            self._resolve('LOSS', pos.stop_price, pnl_pts)
        elif stop_hit:
            pnl_pts = pos.stop_price - self._fill_price if pos.direction == 'LONG' \
                      else self._fill_price - pos.stop_price
            self._resolve('LOSS', pos.stop_price, pnl_pts)
        elif target_hit:
            pnl_pts = pos.target1_price - self._fill_price if pos.direction == 'LONG' \
                      else self._fill_price - pos.target1_price
            self._resolve('WIN', pos.target1_price, pnl_pts)
        elif self._bars_held >= timeout_limit:
            pnl_pts = bar_close - self._fill_price if pos.direction == 'LONG' \
                      else self._fill_price - bar_close
            self._resolve('TIMEOUT', bar_close, pnl_pts)

    def get_position(self, symbol: str) -> Optional[Position]:
        if self._position and self._position.symbol == symbol:
            return self._position
        return None

    def has_open_position(self) -> bool:
        return self._position is not None

    def flatten_all(self) -> None:
        if self._position is None:
            return
        self._resolve('TIMEOUT', self._position.entry_price, 0.0)

    def get_open_orders(self) -> list[Order]:
        return []

    def cancel_order(self, order: Order) -> bool:
        return False

    def get_daily_pnl(self) -> float:
        if self._storage is None:
            return 0.0
        today = datetime.now().strftime('%Y-%m-%d')
        outcomes = self._storage.read_outcomes(days=1)
        return sum(
            float(o.get('pnl_dollars', 0))
            for o in outcomes
            if o.get('date') == today
        )

    # ── internal ─────────────────────────────────────────────────────────────

    def _resolve(self, result: str, exit_price: float, pnl_pts: float) -> None:
        pos = self._position
        if pos is None:
            return

        pnl_dollars = round(pnl_pts * MES_POINT_VALUE - (FEE_PER_SIDE * 2), 2)
        risk_pts    = abs(pos.entry_price - pos.stop_price)
        r_multiple  = round(pnl_pts / risk_pts, 2) if risk_pts > 0 else 0.0

        outcome = {
            'signal_id':   self._signal_id,
            'date':        datetime.now().strftime('%Y-%m-%d'),
            'outcome':     result,
            'exit_price':  round(exit_price, 2),
            'exit_time':   datetime.now().strftime('%H:%M:%S'),
            'pnl_pts':     round(pnl_pts, 2),
            'pnl_dollars': pnl_dollars,
            'mfe_pts':     '',
            'mae_pts':     '',
            'r_multiple':  r_multiple,
        }

        if self._storage:
            self._storage.write_outcome(outcome)

        if self._risk_engine:
            self._risk_engine.update_daily_state({
                'result':      result,
                'pnl_dollars': pnl_dollars,
            })

        if self._alert_provider:
            sign = '+' if pnl_dollars >= 0 else ''
            self._alert_provider.send_text(
                f"📋 Trade closed: {result}  |  {pos.direction} MES @ {exit_price:.2f}"
                f"  |  P&amp;L: {sign}${pnl_dollars:.2f}"
            )

        emoji = '✅' if result == 'WIN' else ('⏱' if result == 'TIMEOUT' else '❌')
        print(f"  [PAPER] {emoji} {result}: {pos.direction} MES closed @ {exit_price:.2f}"
              f"  |  P&L ${pnl_dollars:+.2f}  ({r_multiple:+.2f}R)")

        self._position   = None
        self._signal_id  = ''
        self._entry_tf   = ''
        self._fill_price = 0.0
        self._bars_held  = 0
