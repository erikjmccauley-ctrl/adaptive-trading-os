from __future__ import annotations
from dataclasses import dataclass
import glob
import pandas as pd

from src.inference.confidence.confidence import assign_confidence
from src.inference.expectancy.stats import compute_stats

BUCKET_DIMENSIONS = ('signal_type', 'quality', 'regime', 'entry_tf', 'near_level', 'direction')


@dataclass
class BucketResult:
    key: dict            # e.g. {'signal_type': 'pivot'} or {'entry_tf': '1h', 'regime': 'trending'}
    n: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float
    avg_win_r: float | None
    avg_loss_r: float | None
    expectancy_r: float | None
    profit_factor: float | None
    net_pnl: float
    avg_mfe_r: float | None
    avg_mae_r: float | None
    confidence: str      # 'A' | 'B' | 'C' | 'insufficient-data'

    def key_label(self) -> str:
        if not self.key:
            return 'ALL'
        return '  |  '.join(f'{k}={v}' for k, v in self.key.items())


class BucketEngine:
    def __init__(self, trades: list[dict]):
        self._trades = trades
        self._df = pd.DataFrame(trades) if trades else pd.DataFrame()

    @classmethod
    def from_csvs(cls, *paths: str) -> 'BucketEngine':
        """Load and pool trade records from one or more CSV files."""
        frames = []
        for p in paths:
            try:
                frames.append(pd.read_csv(p))
            except FileNotFoundError:
                pass
        if not frames:
            return cls([])
        df = pd.concat(frames, ignore_index=True)
        # Coerce bool columns that may have been read as strings
        for col in ('reached_0_5r', 'reached_1r', 'reached_2r', 'reached_3r'):
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper() == 'TRUE'
        return cls(df.to_dict('records'))

    @classmethod
    def from_default_csvs(cls) -> 'BucketEngine':
        """Load all backtest_*.csv files found in the current directory."""
        paths = sorted(glob.glob('backtest_*.csv'))
        return cls.from_csvs(*paths)

    def _make_result(self, key: dict, subset: list[dict]) -> BucketResult:
        s = compute_stats(subset)
        conf = assign_confidence(s['n'], s['win_rate'], s['profit_factor'])
        return BucketResult(
            key=key,
            n=s['n'],
            wins=s['wins'],
            losses=s['losses'],
            timeouts=s['timeouts'],
            win_rate=s['win_rate'],
            avg_win_r=s['avg_win_r'],
            avg_loss_r=s['avg_loss_r'],
            expectancy_r=s['expectancy_r'],
            profit_factor=s['profit_factor'],
            net_pnl=s['net_pnl'],
            avg_mfe_r=s['avg_mfe_r'],
            avg_mae_r=s['avg_mae_r'],
            confidence=conf,
        )

    def overall(self) -> BucketResult:
        return self._make_result({}, self._trades)

    def bucket(self, *keys: str) -> list[BucketResult]:
        """
        Group trades by the given field names and return a BucketResult per group.
        Results sorted by n descending.

        Example:
            engine.bucket('signal_type')
            engine.bucket('entry_tf', 'regime')
        """
        if not self._trades:
            return []
        df = self._df.copy()
        for k in keys:
            if k not in df.columns:
                raise ValueError(f"Unknown bucket dimension: '{k}'. "
                                 f"Valid: {BUCKET_DIMENSIONS}")
        groups = df.groupby(list(keys), sort=False)
        results = []
        for group_key, group_df in groups:
            if not isinstance(group_key, tuple):
                group_key = (group_key,)
            key_dict = dict(zip(keys, group_key))
            subset = group_df.to_dict('records')
            results.append(self._make_result(key_dict, subset))
        results.sort(key=lambda r: r.n, reverse=True)
        return results

    def to_dataframe(self, *dimensions: str) -> pd.DataFrame:
        """
        Return a flat DataFrame of BucketResults across all requested single dimensions.
        Useful for CSV export.
        """
        rows = []
        for dim in dimensions:
            for b in self.bucket(dim):
                row = {'dimension': dim, 'key_value': b.key.get(dim, '')}
                row.update({
                    'n': b.n, 'wins': b.wins, 'losses': b.losses, 'timeouts': b.timeouts,
                    'win_rate': b.win_rate, 'avg_win_r': b.avg_win_r,
                    'avg_loss_r': b.avg_loss_r, 'expectancy_r': b.expectancy_r,
                    'profit_factor': b.profit_factor, 'net_pnl': b.net_pnl,
                    'avg_mfe_r': b.avg_mfe_r, 'avg_mae_r': b.avg_mae_r,
                    'confidence': b.confidence,
                })
                rows.append(row)
        return pd.DataFrame(rows)
