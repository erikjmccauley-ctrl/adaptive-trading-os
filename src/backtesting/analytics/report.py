import pandas as pd


def print_report(trades: list[dict], title: str = '') -> pd.DataFrame:
    """
    Print a formatted backtest report to stdout.
    Returns a DataFrame of all trades (for CSV export or Phase 8 import).
    """
    border = '═' * 56
    print(f"\n{border}")
    print(f"  {title}")
    print(border)

    if not trades:
        print("  No trades generated.")
        print(border)
        return pd.DataFrame()

    df       = pd.DataFrame(trades)
    wins     = df[df['outcome'] == 'WIN']
    losses   = df[df['outcome'] == 'LOSS']
    timeouts = df[df['outcome'] == 'TIMEOUT']
    total    = len(df)
    n_w, n_l, n_t = len(wins), len(losses), len(timeouts)
    win_rate = n_w / total * 100

    gross_win  = wins['pnl_dollars'].sum() if not wins.empty else 0.0
    timed_loss = timeouts[timeouts['pnl_dollars'] < 0]['pnl_dollars'].sum() \
                 if not timeouts.empty else 0.0
    gross_loss = abs((losses['pnl_dollars'].sum() if not losses.empty else 0.0) + timed_loss)
    pf         = gross_win / gross_loss if gross_loss > 0 else float('inf')
    net        = df['pnl_dollars'].sum()
    avg_win    = wins['pnl_dollars'].mean()   if not wins.empty   else 0.0
    avg_loss   = losses['pnl_dollars'].mean() if not losses.empty else 0.0

    equity = df.sort_values('entry_ts')['pnl_dollars'].cumsum()
    max_dd = (equity - equity.cummax()).min()

    df['month'] = pd.to_datetime(df['entry_ts']).dt.to_period('M')
    monthly     = df.groupby('month')['pnl_dollars'].sum()
    sharpe      = (monthly.mean() / monthly.std() * 12**0.5) if len(monthly) > 1 and monthly.std() > 0 else 0.0

    longs  = df[df['direction'] == 'LONG']
    shorts = df[df['direction'] == 'SHORT']
    start  = pd.to_datetime(df['entry_ts'].min()).date()
    end    = pd.to_datetime(df['entry_ts'].max()).date()

    # ── Core stats ──────────────────────────────────────────────────────────────
    print(f"  Period:          {start} → {end}")
    print(f"  Total trades:    {total}")
    print(f"  Wins / Losses:   {n_w} / {n_l}  ({n_t} timeout)")
    print(f"  Win Rate:        {win_rate:.1f}%")
    print()
    print(f"  Net P&L:         ${net:+.2f}  (1 MES contract)")
    print(f"  Gross Win:       ${gross_win:+.2f}")
    print(f"  Gross Loss:      ${-gross_loss:.2f}")
    print(f"  Profit Factor:   {pf:.2f}  (target ≥ 1.5)")
    print(f"  Max Drawdown:    ${max_dd:.2f}")
    print(f"  Avg Win:         ${avg_win:+.2f}")
    print(f"  Avg Loss:        ${avg_loss:+.2f}")
    print(f"  Avg Entry R/R:   {df['rr'].mean():.2f}")
    print(f"  Sharpe:          {sharpe:.2f}")

    # ── Direction breakdown ──────────────────────────────────────────────────────
    print()
    lw = len(longs[longs['outcome'] == 'WIN'])
    sw = len(shorts[shorts['outcome'] == 'WIN'])
    print(f"  Long:   {len(longs):>3}  ({lw} wins  /  ${longs['pnl_dollars'].sum():+.2f})")
    print(f"  Short:  {len(shorts):>3}  ({sw} wins  /  ${shorts['pnl_dollars'].sum():+.2f})")

    # ── R-multiple distribution (Phase 7 addition) ───────────────────────────────
    if 'mfe_r' in df.columns and df['mfe_r'].notna().any():
        print()
        print("  R-Multiple Distribution")
        print("  " + "─" * 28)
        for col, label in (('reached_0_5r', '0.5R'), ('reached_1r', '1.0R'),
                           ('reached_2r', '2.0R'),   ('reached_3r', '3.0R')):
            if col in df.columns:
                pct = df[col].sum() / total * 100
                print(f"    Reached {label}:  {pct:>5.1f}%  (n={int(df[col].sum())})")
        mfe_med = df['mfe_r'].median()
        mae_med = df['mae_r'].median() if 'mae_r' in df.columns else None
        r_med   = df['r_multiple'].median() if 'r_multiple' in df.columns else None
        print(f"    MFE median:   {mfe_med:>5.2f}R")
        if mae_med is not None:
            print(f"    MAE median:   {mae_med:>5.2f}R")
        if r_med is not None:
            print(f"    Actual R med: {r_med:>5.2f}R")

    # ── Alternate exit scenarios (Phase 7 addition) ──────────────────────────────
    if 'reached_1r' in df.columns and 'risk_pts' in df.columns:
        print()
        print("  Alternate Exit Scenarios")
        print("  " + "─" * 28)
        for mult, col in ((1.0, 'reached_1r'), (2.0, 'reached_2r'), (3.0, 'reached_3r')):
            if col not in df.columns:
                continue
            alt_wins   = df[df[col] == True]
            alt_losses = df[df[col] == False]
            n_aw = len(alt_wins)
            n_al = len(alt_losses)
            if n_aw + n_al == 0:
                continue
            alt_win_pct = n_aw / (n_aw + n_al) * 100
            # PnL: winners get mult*risk*MES_VALUE, losers take their actual stop loss
            from src.backtesting.engine.walk_forward import MES_POINT_VALUE
            alt_g_win  = (alt_wins['risk_pts'] * mult * MES_POINT_VALUE).sum()
            alt_g_loss = abs(alt_losses['pnl_dollars'].sum())
            alt_pf     = alt_g_win / alt_g_loss if alt_g_loss > 0 else float('inf')
            alt_net    = alt_g_win - alt_g_loss
            print(f"    Exit at {mult:.0f}R:  WR {alt_win_pct:>4.1f}%  "
                  f"|  PF {alt_pf:.2f}  |  Net ${alt_net:+.0f}")
        print(f"    At pivot (actual):     WR {win_rate:.1f}%  |  PF {pf:.2f}  |  Net ${net:+.0f}")

    # ── Quality tier breakdown (Phase 7 addition) ────────────────────────────────
    if 'quality' in df.columns and df['quality'].notna().any():
        print()
        print("  By Quality Tier")
        print("  " + "─" * 28)
        for tier in ['A', 'B', 'C']:
            grp = df[df['quality'] == tier]
            if grp.empty:
                continue
            g_wins = grp[grp['outcome'] == 'WIN']
            g_loss = grp[grp['outcome'] == 'LOSS']
            g_wr   = len(g_wins) / len(grp) * 100
            g_gw   = g_wins['pnl_dollars'].sum() if not g_wins.empty else 0.0
            g_gl   = abs(g_loss['pnl_dollars'].sum()) if not g_loss.empty else 0.0
            g_pf   = g_gw / g_gl if g_gl > 0 else float('inf')
            print(f"    {tier} tier:  WR {g_wr:>4.1f}%  |  PF {g_pf:.2f}  (n={len(grp)})")

    # ── Signal type breakdown ────────────────────────────────────────────────────
    if 'signal_type' in df.columns and df['signal_type'].notna().any():
        print()
        print("  By Signal Type")
        print("  " + "─" * 28)
        for stype in df['signal_type'].dropna().unique():
            grp  = df[df['signal_type'] == stype]
            g_wr = len(grp[grp['outcome'] == 'WIN']) / len(grp) * 100
            g_net = grp['pnl_dollars'].sum()
            print(f"    {stype:<15}  WR {g_wr:>4.1f}%  |  Net ${g_net:+.0f}  (n={len(grp)})")

    # ── Pivot level breakdown ────────────────────────────────────────────────────
    lvl = (df.groupby('near_level')['pnl_dollars']
           .agg(count='count', total='sum', avg='mean')
           .sort_values('count', ascending=False)
           .head(10))
    if not lvl.empty:
        print()
        print("  Pivot level breakdown (top 10):")
        for name, row in lvl.iterrows():
            print(f"    {name:<12}  {int(row['count']):>3}x  ${row['total']:+7.2f}  avg ${row['avg']:+.2f}")

    # ── Verdict ─────────────────────────────────────────────────────────────────
    print()
    if total < 30:
        print(f"  !! Only {total} trades — statistically insignificant (need 30+ minimum)")

    if pf >= 1.5 and win_rate >= 40 and total >= 30:
        verdict = "EDGE CONFIRMED — proceed to paper trading"
    elif pf >= 1.2:
        verdict = "MARGINAL EDGE — refine or gather more data"
    else:
        verdict = "NO EDGE — do not trade live"

    print(f"  Verdict: {verdict}")
    print(border)

    df = df.drop(columns=['month'], errors='ignore')
    return df
