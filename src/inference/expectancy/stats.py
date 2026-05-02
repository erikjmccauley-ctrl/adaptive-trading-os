from __future__ import annotations
import statistics


def compute_stats(trades: list[dict]) -> dict:
    """
    Compute per-bucket statistics from a list of trade records.
    All trades must have the Phase 7 fields: outcome, r_multiple, pnl_dollars, mfe_r, mae_r.
    """
    n = len(trades)
    if n == 0:
        return {
            'n': 0, 'wins': 0, 'losses': 0, 'timeouts': 0,
            'win_rate': 0.0, 'avg_win_r': None, 'avg_loss_r': None,
            'expectancy_r': None, 'profit_factor': None,
            'net_pnl': 0.0, 'avg_mfe_r': None, 'avg_mae_r': None,
        }

    wins     = [t for t in trades if t.get('outcome') == 'WIN']
    losses   = [t for t in trades if t.get('outcome') == 'LOSS']
    timeouts = [t for t in trades if t.get('outcome') == 'TIMEOUT']

    win_rate = len(wins) / n

    win_rs  = [float(t['r_multiple']) for t in wins  if t.get('r_multiple') is not None]
    loss_rs = [float(t['r_multiple']) for t in losses if t.get('r_multiple') is not None]

    avg_win_r  = statistics.mean(win_rs)  if win_rs  else None
    avg_loss_r = statistics.mean(loss_rs) if loss_rs else None

    if avg_win_r is not None and avg_loss_r is not None:
        expectancy_r = win_rate * avg_win_r + (1 - win_rate) * avg_loss_r
    else:
        expectancy_r = None

    gross_win  = sum(float(t['pnl_dollars']) for t in wins)
    gross_loss = abs(sum(float(t['pnl_dollars']) for t in losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else None

    net_pnl = sum(float(t['pnl_dollars']) for t in trades)

    mfe_rs = [float(t['mfe_r']) for t in trades if t.get('mfe_r') is not None]
    mae_rs = [float(t['mae_r']) for t in trades if t.get('mae_r') is not None]
    avg_mfe_r = statistics.mean(mfe_rs) if mfe_rs else None
    avg_mae_r = statistics.mean(mae_rs) if mae_rs else None

    return {
        'n':            n,
        'wins':         len(wins),
        'losses':       len(losses),
        'timeouts':     len(timeouts),
        'win_rate':     win_rate,
        'avg_win_r':    round(avg_win_r,  2) if avg_win_r  is not None else None,
        'avg_loss_r':   round(avg_loss_r, 2) if avg_loss_r is not None else None,
        'expectancy_r': round(expectancy_r, 2) if expectancy_r is not None else None,
        'profit_factor': round(profit_factor, 2) if profit_factor is not None else None,
        'net_pnl':      round(net_pnl, 2),
        'avg_mfe_r':    round(avg_mfe_r, 2) if avg_mfe_r is not None else None,
        'avg_mae_r':    round(avg_mae_r, 2) if avg_mae_r is not None else None,
    }
