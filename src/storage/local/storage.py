"""
LocalStorage — CSV + JSON file-based storage for local dev mode.

No AWS required. All data written to the data/ directory.
Satisfies StorageProvider so the rest of the OS doesn't need to know
whether it's talking to DynamoDB or local files.

File layout:
  data/normalized/{tf}.csv          — normalized candles per timeframe
  data/raw/signals/signals_{date}.csv — signals fired on a given date
  data/raw/outcomes.csv             — resolved trade outcomes
  data/raw/cooldowns.json           — signal cooldown records (keyed by tf+level+dir)
"""

import csv
import json
import os
import pandas as pd
from datetime import datetime, date
from typing import Optional

from src.core.contracts.storage import StorageProvider

_BASE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
_NORMALIZED_DIR = os.path.join(_BASE, 'normalized')
_SIGNALS_DIR    = os.path.join(_BASE, 'raw', 'signals')
_OUTCOMES_FILE  = os.path.join(_BASE, 'raw', 'outcomes.csv')
_COOLDOWN_FILE  = os.path.join(_BASE, 'raw', 'cooldowns.json')

_SIGNAL_FIELDS = [
    'signal_id', 'date', 'time', 'direction', 'entry_tf', 'tf_label',
    'entry', 'stop', 'target1', 'target1_name', 'target2', 'target2_name',
    'near_level', 'rr', 'regime', 'adx', 'quality', 'signal_type',
    'daily_consumed_pct',
]

_OUTCOME_FIELDS = [
    'signal_id', 'date', 'outcome', 'exit_price', 'exit_time',
    'pnl_pts', 'pnl_dollars', 'mfe_pts', 'mae_pts', 'r_multiple',
]


class LocalStorage(StorageProvider):
    """
    File-based storage implementation for local development.
    Thread-safety: not guaranteed — single-process use only.
    """

    def __init__(self, base_dir: str | None = None):
        self._base        = base_dir or _BASE
        self._norm_dir    = os.path.join(self._base, 'normalized')
        self._signals_dir = os.path.join(self._base, 'raw', 'signals')
        self._outcomes    = os.path.join(self._base, 'raw', 'outcomes.csv')
        self._cooldowns   = os.path.join(self._base, 'raw', 'cooldowns.json')
        self._ensure_dirs()

    # ── StorageProvider interface ─────────────────────────────────────────────

    def write_signal(self, signal: dict) -> None:
        today = datetime.now().strftime('%Y-%m-%d')
        path  = os.path.join(self._signals_dir, f'signals_{today}.csv')
        row   = self._signal_to_row(signal)
        self._append_csv(path, _SIGNAL_FIELDS, row)

    def read_signals(self, date_str: str) -> list[dict]:
        path = os.path.join(self._signals_dir, f'signals_{date_str}.csv')
        if not os.path.exists(path):
            return []
        return self._read_csv(path)

    def write_candles(self, tf: str, df: pd.DataFrame) -> None:
        path = os.path.join(self._norm_dir, f'{tf}.csv')
        df.to_csv(path)

    def read_candles(self, tf: str, days: int = 30) -> pd.DataFrame:
        path = os.path.join(self._norm_dir, f'{tf}.csv')
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if df.empty:
            return df
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        return df[df.index >= cutoff]

    def write_outcome(self, outcome: dict) -> None:
        self._append_csv(self._outcomes, _OUTCOME_FIELDS, outcome)

    def read_outcomes(self, days: int = 90) -> list[dict]:
        if not os.path.exists(self._outcomes):
            return []
        rows = self._read_csv(self._outcomes)
        cutoff = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
        return [r for r in rows if r.get('date', '') >= cutoff]

    def get_cooldown_record(self, key: tuple) -> Optional[str]:
        """key = (entry_tf, near_level, direction)"""
        store = self._load_cooldowns()
        return store.get(self._cooldown_key(key))

    def set_cooldown_record(self, key: tuple, fired_at: str) -> None:
        store = self._load_cooldowns()
        store[self._cooldown_key(key)] = fired_at
        self._save_cooldowns(store)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        for d in [self._norm_dir, self._signals_dir,
                  os.path.dirname(self._outcomes)]:
            os.makedirs(d, exist_ok=True)

    @staticmethod
    def _cooldown_key(key: tuple) -> str:
        return '|'.join(str(k) for k in key)

    def _load_cooldowns(self) -> dict:
        if not os.path.exists(self._cooldowns):
            return {}
        with open(self._cooldowns, 'r') as f:
            return json.load(f)

    def _save_cooldowns(self, store: dict) -> None:
        with open(self._cooldowns, 'w') as f:
            json.dump(store, f, indent=2)

    @staticmethod
    def _signal_to_row(signal: dict) -> dict:
        now = datetime.now()
        return {
            'signal_id':          f"{now.strftime('%Y%m%d_%H%M%S')}_{signal.get('direction', '')}_{signal.get('near_level', '')}",
            'date':               now.strftime('%Y-%m-%d'),
            'time':               now.strftime('%H:%M:%S'),
            'direction':          signal.get('direction', ''),
            'entry_tf':           signal.get('entry_tf', ''),
            'tf_label':           signal.get('tf_label', ''),
            'entry':              signal.get('entry', ''),
            'stop':               signal.get('stop', ''),
            'target1':            signal.get('target1', ''),
            'target1_name':       signal.get('target1_name', ''),
            'target2':            signal.get('target2', ''),
            'target2_name':       signal.get('target2_name', ''),
            'near_level':         signal.get('near_level', ''),
            'rr':                 signal.get('rr', ''),
            'regime':             signal.get('regime', ''),
            'adx':                signal.get('adx', ''),
            'quality':            signal.get('quality', ''),
            'signal_type':        signal.get('signal_type', ''),
            'daily_consumed_pct': signal.get('daily_consumed_pct', ''),
        }

    @staticmethod
    def _append_csv(path: str, fieldnames: list, row: dict) -> None:
        write_header = not os.path.exists(path)
        with open(path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    @staticmethod
    def _read_csv(path: str) -> list[dict]:
        with open(path, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
