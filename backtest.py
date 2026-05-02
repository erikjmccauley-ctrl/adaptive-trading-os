#!/usr/bin/env python3
"""
Walk-forward backtest for MES SMMA + Pivot Point strategy.

  Section 1 — Long-term  (yfinance) : ~2yr of 1H bars, 1H entry w/ 4H + Daily confirm
  Section 2 — Short-term (Schwab)   : max available per TF — 1m (5d), 5m (10d), 15m (20d), 1H (30d)

Usage: python -X utf8 backtest.py
"""

from src.backtesting import walk_forward, print_report, load_yfinance_1h, load_schwab_data
from src.signals import CONFIRMATION_MAP


# ─── Section 1: yfinance long-term 1H backtest ───────────────────────────────

def run_yf_backtest():
    print("\n" + "─" * 56)
    print("  SECTION 1 — Long-Term  (yfinance ~2yr, 1H entry)")
    print("─" * 56)

    data = load_yfinance_1h()
    if data.empty or len(data) < 200:
        print("  Not enough data returned — skipping")
        return

    print(f"  Walking forward through {len(data)} bars...")
    trades = walk_forward(data, '1h', daily_data=None, warmup_bars=100)
    print(f"  Complete — {len(trades)} trades simulated")

    confirm = ' + '.join(CONFIRMATION_MAP.get('1h', []))
    df = print_report(trades, f"1H ENTRY  |  yfinance ~2yr  |  {confirm} confirmation")
    if not df.empty:
        df.to_csv('backtest_yf_1h.csv', index=False)
        print("  Full trade log saved → backtest_yf_1h.csv")


# ─── Section 2: Schwab short-term per-TF backtests ───────────────────────────

def run_schwab_backtest():
    print("\n" + "─" * 56)
    print("  SECTION 2 — Short-Term  (Schwab max history, per TF)")
    print("─" * 56)

    tf_bases, daily = load_schwab_data()
    if tf_bases is None:
        return

    warmup_map = {'1m': 40, '5m': 40, '15m': 50, '1h': 40}

    for entry_tf in ['1m', '5m', '15m', '1h']:
        base   = tf_bases.get(entry_tf)
        warmup = warmup_map[entry_tf]

        if base is None or base.empty:
            print(f"\n  {entry_tf.upper()}: no data returned — skipping")
            continue
        if len(base) < warmup * 2:
            print(f"\n  {entry_tf.upper()}: only {len(base)} bars — not enough for backtest")
            continue

        print(f"\n  Walking {entry_tf.upper()} ({len(base)} bars "
              f"|  {base.index[0].date()} → {base.index[-1].date()})...")
        trades = walk_forward(base, entry_tf, daily_data=daily, warmup_bars=warmup)
        print(f"  Complete — {len(trades)} trades simulated")

        confirm = ' + '.join(CONFIRMATION_MAP.get(entry_tf, []) or ['own TF only'])
        df = print_report(
            trades,
            f"{entry_tf.upper()} ENTRY  |  Schwab  |  {confirm} confirmation",
        )
        if not df.empty:
            fname = f'backtest_schwab_{entry_tf}.csv'
            df.to_csv(fname, index=False)
            print(f"  Full trade log saved → {fname}")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    run_yf_backtest()
    run_schwab_backtest()
    print("\n  Done.")
