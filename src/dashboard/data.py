"""
Dashboard data loaders. All heavy I/O goes through here with Streamlit TTL caching
so widget interactions don't re-read files on every rerender.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from src.core.contracts.risk_engine import DailyRiskState
from src.risk.daily_state.state_store import RiskStateStore
from src.rules.rule_engine.models import Rule
from src.rules.rule_engine.rule_store import RuleStore
from src.storage.local.storage import LocalStorage


# ── today's signals ───────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_todays_signals() -> list[dict]:
    today = datetime.now().strftime('%Y-%m-%d')
    return LocalStorage().read_signals(today)


# ── outcomes ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_outcomes(days: int = 30) -> pd.DataFrame:
    rows = LocalStorage().read_outcomes(days=days)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in ('pnl_dollars', 'r_multiple', 'pnl_pts'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    return df


# ── bucket analysis ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_bucket_analysis(dimension: str) -> pd.DataFrame | None:
    try:
        from src.inference.bucket_analysis.bucket_engine import BucketEngine
        engine  = BucketEngine.from_default_csvs()
        results = engine.bucket(dimension)
        if not results:
            return None
        rows = []
        for br in results:
            rows.append({
                dimension:      br.key.get(dimension, ''),
                'n':            br.n,
                'wins':         br.wins,
                'losses':       br.losses,
                'win_rate':     round(br.win_rate * 100, 1) if br.win_rate is not None else None,
                'profit_factor': round(br.profit_factor, 2) if br.profit_factor is not None else None,
                'expectancy_r': round(br.expectancy_r, 3) if br.expectancy_r is not None else None,
                'net_pnl':      round(br.net_pnl, 2),
                'confidence':   br.confidence,
            })
        return pd.DataFrame(rows)
    except Exception:
        return None


@st.cache_data(ttl=300)
def total_backtest_trades() -> int:
    try:
        from src.inference.bucket_analysis.bucket_engine import BucketEngine
        engine = BucketEngine.from_default_csvs()
        return engine.overall().n
    except Exception:
        return 0


# ── risk state ────────────────────────────────────────────────────────────────

def load_risk_state() -> DailyRiskState:
    return RiskStateStore().load()


# ── rules ─────────────────────────────────────────────────────────────────────

def load_rules() -> tuple[list[Rule], list[Rule]]:
    store = RuleStore()
    return store.load_active(), store.load_candidates()


def promote_rule(rule_id: str) -> None:
    RuleStore().promote(rule_id)


def retire_rule(rule_id: str) -> None:
    RuleStore().retire(rule_id)
