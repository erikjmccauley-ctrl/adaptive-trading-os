"""
MES Signal Bot
Strategy: 3/8/21 SMMA + Daily/Weekly/Monthly Pivot Points
Scans: 1m / 5m / 15m / 1H / 4H / Daily — fires on any timeframe with a valid setup
"""
import time
import sys
from datetime import datetime, timedelta, time as dtime

from src.data import get_multi_tf_data, get_pivot_source_ohlc
from src.features.indicators import get_all_pivots, add_smmAs, ema_alignment
from src.signals import generate_signals
from src.display import print_signals, print_status, print_no_signal, print_header
from src.risk import load_risk_engine
from src.alerts import load_alert_provider
from src.storage.local.storage import LocalStorage
from src.execution import load_paper_broker
from src.execution.paper_broker.order_builder import order_from_signal
from colorama import Fore

_risk_engine    = load_risk_engine()
_alert_provider = load_alert_provider(risk_engine=_risk_engine)
_storage        = LocalStorage()
_paper_broker   = load_paper_broker(_storage, _risk_engine, _alert_provider)

SCAN_INTERVAL = 30    # seconds
STATUS_EVERY  = 10    # print full status block every N scans

MARKET_OPEN  = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)

# How long to suppress re-fires of the same (TF, pivot level, direction) setup.
# Prevents the same signal from flooding every 30s scan.
SIGNAL_COOLDOWN = {
    '1m':  timedelta(minutes=5),
    '5m':  timedelta(minutes=15),
    '15m': timedelta(minutes=30),
    '1h':  timedelta(hours=1),
    '4h':  timedelta(hours=4),
    '1d':  timedelta(hours=8),
}

_signal_history: dict = {}   # (entry_tf, near_level, direction) → last fired datetime


def is_market_hours():
    now = datetime.now().time()
    return MARKET_OPEN <= now <= MARKET_CLOSE


def get_alignment(tf_data):
    result = {}
    for tf, df in tf_data.items():
        if not df.empty and len(df) > 21:
            result[tf] = ema_alignment(add_smmAs(df))
        else:
            result[tf] = 'neutral'
    return result


def _dedup_signals(signals):
    """Drop signals that already fired recently at the same (TF, level, direction)."""
    now = datetime.now()
    fresh = []
    for sig in signals:
        key = (sig['entry_tf'], sig['near_level'], sig['direction'])
        # Range scalps get half the cooldown — they can legitimately repeat each bounce
        cooldown = SIGNAL_COOLDOWN.get(sig['entry_tf'], timedelta(minutes=15))
        if sig.get('signal_type') == 'range_scalp':
            cooldown = cooldown // 2
        last = _signal_history.get(key)
        if last is None or (now - last) > cooldown:
            fresh.append(sig)
    return fresh


def _record_signals(signals):
    now = datetime.now()
    for sig in signals:
        key = (sig['entry_tf'], sig['near_level'], sig['direction'])
        _signal_history[key] = now


def main():
    print_header()
    scan_count = 0

    while True:
        try:
            if not is_market_hours():
                print(f"{Fore.YELLOW}  [{datetime.now().strftime('%I:%M %p')}]  "
                      f"Market closed — checking again in 5 min...")
                time.sleep(300)
                continue

            print(f"{Fore.WHITE}  Scanning all timeframes...", end='\r')

            tf_data      = get_multi_tf_data()
            _paper_broker.check_positions(tf_data)
            pivot_source = get_pivot_source_ohlc()
            pivots       = get_all_pivots(pivot_source)
            align        = get_alignment(tf_data)

            five_min = tf_data.get('5m')
            if five_min is None or five_min.empty:
                print(f"{Fore.RED}  No data — retrying in 30s...")
                time.sleep(30)
                continue

            price = float(five_min['close'].iloc[-1])

            if scan_count % STATUS_EVERY == 0:
                print_status(price, pivots, align)

            signals = generate_signals(tf_data, pivots)
            signals = _dedup_signals(signals)

            # Risk gate — filter signals that breach daily limits or kill switch
            fresh = []
            for sig in signals:
                allowed, reason = _risk_engine.validate_trade_intent(sig)
                if allowed:
                    fresh.append(sig)
                else:
                    print(f"{Fore.RED}  [RISK BLOCKED] {sig.get('entry_tf','')} "
                          f"{sig.get('direction','')} — {reason}")
            signals = fresh

            if signals:
                _risk_engine.record_signal_fired()
                _record_signals(signals)
                print_signals(signals)
                if _alert_provider:
                    for sig in signals:
                        _alert_provider.send_signal(sig)
                if not _paper_broker.has_open_position():
                    _paper_broker.place_order(order_from_signal(signals[0]))
            else:
                print_no_signal(align)

            scan_count += 1
            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}  Signal bot stopped. Good trading.")
            sys.exit(0)
        except Exception as e:
            print(f"{Fore.RED}  Error: {e} — retrying in 30s...")
            time.sleep(30)


if __name__ == "__main__":
    main()
