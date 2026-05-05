from __future__ import annotations
import glob
import pandas as pd

from src.inference.bucket_analysis.bucket_engine import BucketEngine, BucketResult, BUCKET_DIMENSIONS
from src.inference.confidence.confidence import assign_confidence
from src.inference.expectancy.stats import compute_stats
from src.inference.rule_recommendations.recommendations import generate_recommendations

__all__ = [
    'BucketEngine', 'BucketResult', 'assign_confidence',
    'compute_stats', 'generate_recommendations', 'run_inference',
]

# ── formatting helpers ────────────────────────────────────────────────────────

_W = 56  # report width

def _bar():
    print('═' * _W)

def _sep():
    print('─' * _W)

def _fmt_pf(pf: float | None) -> str:
    if pf is None:
        return 'PF  n/a'
    if pf > 99:
        return 'PF  inf'
    return f'PF {pf:4.2f}'

def _fmt_e(e: float | None) -> str:
    if e is None:
        return 'E    n/a'
    sign = '+' if e >= 0 else ''
    return f'E {sign}{e:.2f}R'

def _fmt_wr(wr: float) -> str:
    return f'WR {wr:4.0%}'

def _fmt_net(net: float) -> str:
    sign = '+' if net >= 0 else ''
    return f'Net ${sign}{net:.0f}'

def _fmt_conf(conf: str) -> str:
    return f'[{conf}]'

def _bucket_row(label: str, b: BucketResult, label_width: int = 14) -> str:
    lbl = label.ljust(label_width)
    return (f'  {lbl}  n={b.n:3d}  {_fmt_wr(b.win_rate)}  '
            f'{_fmt_pf(b.profit_factor)}  {_fmt_e(b.expectancy_r)}  '
            f'{_fmt_net(b.net_pnl):>10}  {_fmt_conf(b.confidence)}')


# ── section printers ──────────────────────────────────────────────────────────

def _print_section(title: str, buckets: list[BucketResult],
                   key_field: str, label_width: int = 14,
                   max_rows: int = 12) -> None:
    print(f'\n  {title}')
    _sep()
    if not buckets:
        print('  (no data)')
        return
    for b in buckets[:max_rows]:
        label = b.key.get(key_field, str(b.key))
        print(_bucket_row(label, b, label_width))


def _print_recommendations(engine: BucketEngine) -> None:
    print('\n  RULE RECOMMENDATIONS')
    _sep()
    all_recs: list[str] = []
    for dim in ('near_level', 'signal_type', 'entry_tf', 'quality', 'regime'):
        try:
            buckets = engine.bucket(dim)
            recs = generate_recommendations(buckets, dim)
            all_recs.extend(recs)
        except Exception:
            pass
    if all_recs:
        for r in all_recs:
            print(f'  {r}')
    else:
        print('  (no recommendations — insufficient data across all dimensions)')


# ── public entry point ────────────────────────────────────────────────────────

def run_inference(
    trades: list[dict] | None = None,
    csv_paths: list[str] | None = None,
    title: str = '',
) -> pd.DataFrame:
    """
    Run the full inference analysis and print a formatted report.

    Priority:
      1. `trades` list — if provided, use directly (programmatic path)
      2. `csv_paths` — load and pool the given CSV files
      3. Default — glob all backtest_*.csv in the current directory

    Returns a DataFrame of all BucketResults across standard dimensions
    (one row per dimension + key_value combination). Save with .to_csv().
    """
    if trades is not None:
        engine = BucketEngine(trades)
        source_label = f'{len(trades)} trades (programmatic)'
    elif csv_paths:
        engine = BucketEngine.from_csvs(*csv_paths)
        source_label = f'{engine.overall().n} trades  |  {len(csv_paths)} files loaded'
    else:
        paths = sorted(glob.glob('data/backtests/backtest_*.csv'))
        engine = BucketEngine.from_csvs(*paths)
        source_label = f'{engine.overall().n} trades  |  {len(paths)} files loaded'

    overall = engine.overall()

    # ── header ────────────────────────────────────────────────────────────────
    _bar()
    hdr = f'  INFERENCE REPORT  |  {source_label}'
    if title:
        hdr += f'  |  {title}'
    print(hdr)
    _bar()

    # ── overall ───────────────────────────────────────────────────────────────
    print('\n  OVERALL')
    _sep()
    print(f'  Trades: {overall.n}  |  '
          f'{_fmt_wr(overall.win_rate)}  |  '
          f'{_fmt_pf(overall.profit_factor)}  |  '
          f'{_fmt_e(overall.expectancy_r)}  |  '
          f'{_fmt_net(overall.net_pnl)}')
    if overall.avg_mfe_r is not None:
        print(f'  MFE avg: {overall.avg_mfe_r:.2f}R  |  MAE avg: {overall.avg_mae_r:.2f}R')

    # ── standard single-dimension sections ────────────────────────────────────
    sections = [
        ('BY SIGNAL TYPE',  'signal_type', 16),
        ('BY QUALITY TIER', 'quality',     14),
        ('BY REGIME',       'regime',      14),
        ('BY ENTRY TF',     'entry_tf',    14),
    ]
    for title_str, dim, lw in sections:
        try:
            buckets = engine.bucket(dim)
            _print_section(title_str, buckets, dim, label_width=lw)
        except Exception:
            pass

    # ── pivot level (top 12) ──────────────────────────────────────────────────
    try:
        level_buckets = engine.bucket('near_level')
        _print_section('BY PIVOT LEVEL  (top 12 by n)', level_buckets,
                       'near_level', label_width=10, max_rows=12)
    except Exception:
        pass

    # ── recommendations ───────────────────────────────────────────────────────
    _print_recommendations(engine)

    # ── data quality warnings ─────────────────────────────────────────────────
    print()
    min_n = min((b.n for b in engine.bucket('entry_tf')), default=0)
    max_n = max((b.n for b in engine.bucket('entry_tf')), default=0)
    if max_n < 30:
        print(f'  !! All buckets insufficient-data — need 10+ per bucket, 30+ for A-grade')
    if max_n > 0 and min_n < 10:
        print(f'  !! Some TFs have < 10 trades — short-TF results are noise')
    print(f'  !! Paper trade to build sample: target 30+ per setup family')
    _bar()

    # ── return flat DataFrame ─────────────────────────────────────────────────
    dims = [d for _, d, _ in sections] + ['near_level']
    return engine.to_dataframe(*dims)
