"""
MES Signal Bot — consolidated signals module for Lambda.

All logic is inlined here (no local package imports).
Only external deps: pandas, numpy, datetime, dataclasses, typing.
Local dep: src.indicators (flat file in same Lambda src/ directory).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import numpy as np

from .indicators import (
    add_smmAs, ema_alignment, smma_pullback_touch, smma_micro_alignment,
    calc_atr, calc_adx,
    rejection_at_level, bar_close_quality, is_engulfing, momentum_consistency,
    find_swing_low, find_swing_high,
)


# ── Constants ─────────────────────────────────────────────────────────────────

MIN_RR               = 2.0
MIN_RR_SCALP         = 1.5
PROXIMITY_ATR        = 0.6
MIN_VOLUME_RATIO     = 0.5
VOLUME_DIRECTION_BARS = 5
ADX_TRENDING         = 25
ADX_RANGING          = 18
ATR_CONSUMED_LIMIT   = 0.90
ATR_OVEREXTENDED     = 1.10
ACCOUNT_BALANCE      = 250.00
SWING_UNLOCK_BALANCE = 3500.00
MES_POINT_VALUE      = 5.0

CONFIRMATION_MAP = {
    '1m':  ['5m', '15m'],
    '5m':  ['15m', '1h'],
    '15m': ['1h', '4h'],
    '1h':  ['4h', '1d'],
    '4h':  ['1d'],
    '1d':  [],
}

INTRADAY_ONLY = ['1m', '5m', '15m', '1h']
SWING_TFS     = ['4h', '1d']

TF_LABEL = {
    '1m':  '1m  (scalp)',
    '5m':  '5m  (scalp)',
    '15m': '15m (intraday)',
    '1h':  '1H  (intraday)',
    '4h':  '4H  (swing)',
    '1d':  'Daily (swing)',
}

# Levels with confirmed negative edge — signals at these levels are suppressed.
LEVEL_BLACKLIST: set = {
    'D_FR1',   # 0/9 wins across all TFs
    'D_S2',    # 0/5 wins across all TFs
}

TF_DISPLAY = {
    '1m':  ['5m', '15m', '1h'],
    '5m':  ['15m', '1h', '1d'],
    '15m': ['1h', '4h', '1d'],
    '1h':  ['4h', '1d'],
    '4h':  ['1d'],
    '1d':  ['1d'],
}

# ADX is measured on the highest confirmation TF for each entry TF
_ADX_TF_MAP = {
    '1m':  '15m',
    '5m':  '1h',
    '15m': '4h',
    '1h':  '1d',
    '4h':  '1d',
    '1d':  '1d',
}

# Quality score by tier (simplified rule engine for Lambda — no JSON file loading)
_QUALITY_SCORE = {'A': 80, 'B': 60, 'C': 40}


# ── Level Catalog ─────────────────────────────────────────────────────────────

@dataclass
class PivotLevel:
    name:       str
    price:      float
    period:     str
    level_type: str
    role:       str

    def __str__(self):
        return f"{self.name} @ {self.price:.2f}  [{self.period} {self.level_type} {self.role}]"


def _parse_level(name: str, price: float) -> PivotLevel:
    prefix     = name[0]
    period     = {'D': 'daily', 'W': 'weekly', 'M': 'monthly'}.get(prefix, 'unknown')
    suffix     = name[2:]
    is_fib     = suffix.startswith('F')
    level_type = 'fibonacci' if is_fib else 'standard'
    code       = suffix[1:] if is_fib else suffix
    if code == 'PP':
        role = 'pivot'
    elif code.startswith('R'):
        role = 'resistance'
    else:
        role = 'support'
    return PivotLevel(name=name, price=price, period=period,
                      level_type=level_type, role=role)


class LevelCatalog:
    def __init__(self, pivot_dict: dict):
        self._levels = [_parse_level(name, price) for name, price in pivot_dict.items()]

    def all_levels(self):
        return sorted(self._levels, key=lambda l: l.price)

    def levels_near(self, price: float, atr: float, proximity: float = 0.6):
        threshold = proximity * atr
        nearby = [l for l in self._levels if abs(l.price - price) <= threshold]
        return sorted(nearby, key=lambda l: abs(l.price - price))

    def levels_above(self, price: float):
        return sorted([l for l in self._levels if l.price > price], key=lambda l: l.price)

    def levels_below(self, price: float):
        return sorted([l for l in self._levels if l.price < price],
                      key=lambda l: l.price, reverse=True)

    def two_targets(self, price: float, direction: str):
        candidates = self.levels_above(price) if direction == 'long' else self.levels_below(price)
        t1 = candidates[0] if len(candidates) > 0 else None
        t2 = candidates[1] if len(candidates) > 1 else None
        return t1, t2

    def __len__(self):
        return len(self._levels)


# ── Regime Classifier ─────────────────────────────────────────────────────────

@dataclass
class RegimeResult:
    adx:    float
    regime: str   # 'trending' | 'neutral' | 'ranging'
    adx_tf: str


class RegimeClassifier:
    def __init__(self, adx_trending: float = 25.0, adx_ranging: float = 18.0):
        self.adx_trending = adx_trending
        self.adx_ranging  = adx_ranging

    def classify(self, tf_data: dict, entry_tf: str) -> RegimeResult:
        adx_tf = _ADX_TF_MAP.get(entry_tf, entry_tf)
        df     = tf_data.get(adx_tf)

        if df is None or df.empty or len(df) < 30:
            return RegimeResult(adx=0.0, regime='neutral', adx_tf=adx_tf)

        try:
            adx_val = calc_adx(df)
        except Exception:
            return RegimeResult(adx=0.0, regime='neutral', adx_tf=adx_tf)

        if adx_val >= self.adx_trending:
            regime = 'trending'
        elif adx_val < self.adx_ranging:
            regime = 'ranging'
        else:
            regime = 'neutral'

        return RegimeResult(adx=round(adx_val, 1), regime=regime, adx_tf=adx_tf)


# ── Volume Filters ─────────────────────────────────────────────────────────────

def passes_volume_gate(entry_df, min_ratio: float = MIN_VOLUME_RATIO) -> bool:
    """3-bar avg volume >= min_ratio × 20-bar avg. Returns True if data is insufficient."""
    if len(entry_df) < 23:
        return True
    avg_vol_20 = float(entry_df['volume'].iloc[-21:].mean())
    recent_vol = float(entry_df['volume'].iloc[-3:].mean())
    if avg_vol_20 <= 0:
        return True
    return recent_vol >= min_ratio * avg_vol_20


def passes_volume_direction_gate(entry_df, direction: str, threshold: float = 0.45) -> bool:
    n = VOLUME_DIRECTION_BARS
    if len(entry_df) < n + 1:
        return True
    recent    = entry_df.iloc[-(n + 1):-1]
    up_vol    = float(recent[recent['close'] > recent['open']]['volume'].sum())
    dn_vol    = float(recent[recent['close'] < recent['open']]['volume'].sum())
    total_vol = up_vol + dn_vol
    if total_vol <= 0:
        return True
    if direction == 'bullish':
        return up_vol / total_vol >= threshold
    else:
        return dn_vol / total_vol >= threshold


def volume_direction_note(entry_df, direction: str, n_bars: int = VOLUME_DIRECTION_BARS) -> str:
    if len(entry_df) < n_bars + 1:
        return ''
    recent    = entry_df.iloc[-(n_bars + 1):-1]
    up_vol    = float(recent[recent['close'] > recent['open']]['volume'].sum())
    dn_vol    = float(recent[recent['close'] < recent['open']]['volume'].sum())
    total_vol = up_vol + dn_vol
    if total_vol == 0:
        return ''
    up_pct = up_vol / total_vol
    if direction == 'bullish':
        return f"vol {int(up_pct * 100)}% bullish" if up_pct >= 0.55 else f"vol mixed ({int(up_pct * 100)}% bullish)"
    else:
        dn_pct = dn_vol / total_vol
        return f"vol {int(dn_pct * 100)}% bearish" if dn_pct >= 0.55 else f"vol mixed ({int(dn_pct * 100)}% bearish)"


# ── Signal Quality ─────────────────────────────────────────────────────────────

def signal_quality(entry_df, direction: str, pivot_level=None) -> tuple:
    """
    Score signal quality from three price action components (0-3 points).
      1. Bar close quality  — close in upper/lower 35% of bar range
      2. Momentum           — 2+ of last 3 completed bars closed in trade direction
      3. Engulfing bar      — for pivot/pullback (pivot_level=None)
         Rejection wick     — for range scalp (pivot_level=price)

    Returns (tier, detail_string).  tier in {'A', 'B', 'C'}
    """
    score = 0
    parts = []

    cq    = bar_close_quality(entry_df)
    cq_ok = (direction == 'bullish' and cq >= 0.65) or (direction == 'bearish' and cq <= 0.35)
    if cq_ok:
        score += 1
    parts.append(f"close {int(cq * 100)}%")

    mom = momentum_consistency(entry_df, direction, lookback=3)
    if mom >= 2:
        score += 1
    parts.append(f"mom {mom}/3")

    if pivot_level is not None:
        rej = rejection_at_level(entry_df, direction, pivot_level)
        if rej:
            score += 1
        parts.append("wick ✓" if rej else "no wick")
    else:
        engulf = is_engulfing(entry_df, direction)
        if engulf:
            score += 1
        parts.append("engulf ✓" if engulf else "no engulf")

    tier = 'A' if score >= 3 else ('B' if score >= 2 else 'C')
    return tier, '  |  '.join(parts)


# ── Pivot Signal ───────────────────────────────────────────────────────────────

def _build_reason(near_level: str, entry_tf: str, direction: str) -> str:
    dir_word = 'bullish' if direction == 'LONG' else 'bearish'
    return f"Price at {near_level}  |  {TF_LABEL[entry_tf].split('(')[0].strip()} {dir_word} confluence"


def check_pivot_setup(entry_tf, direction, price, entry_df,
                      nearby_levels, catalog, align,
                      market_context, adx_val, adx_tf, regime) -> Optional[dict]:
    mes    = MES_POINT_VALUE
    min_rr = MIN_RR_SCALP if regime == 'ranging' else MIN_RR

    if not passes_volume_gate(entry_df):
        return None
    if not passes_volume_direction_gate(entry_df, direction):
        return None

    consumed    = market_context.get('daily_consumed_pct')
    suppress_t2 = regime == 'ranging' or (consumed is not None and consumed >= ATR_CONSUMED_LIMIT)

    if direction == 'bullish':
        support = [lv for lv in nearby_levels if lv.price <= price]
        if not support:
            return None
        near = max(support, key=lambda lv: lv.price)
        if not rejection_at_level(entry_df, 'bullish', near.price):
            return None
        swing_low = find_swing_low(entry_df, lookback=10)
        stop      = round(swing_low - 0.25, 2)
        t1, t2    = catalog.two_targets(price, 'long')
        if t1 is None:
            return None
        risk   = price - stop
        reward = t1.price - price
        if risk <= 0:
            return None
        rr = round(reward / risk, 2)
        if rr < min_rr:
            return None
        direction_label = 'LONG'

    else:
        resistance = [lv for lv in nearby_levels if lv.price >= price]
        if not resistance:
            return None
        near = min(resistance, key=lambda lv: lv.price)
        if not rejection_at_level(entry_df, 'bearish', near.price):
            return None
        swing_high = find_swing_high(entry_df, lookback=10)
        stop       = round(swing_high + 0.25, 2)
        t1, t2     = catalog.two_targets(price, 'short')
        if t1 is None:
            return None
        risk   = stop - price
        reward = price - t1.price
        if risk <= 0:
            return None
        rr = round(reward / risk, 2)
        if rr < min_rr:
            return None
        direction_label = 'SHORT'

    if suppress_t2:
        t2 = None

    t2_name  = t2.name  if t2 else None
    t2_price = t2.price if t2 else None
    reward2  = None
    if direction_label == 'LONG' and t2_price:
        reward2 = t2_price - price
    elif direction_label == 'SHORT' and t2_price:
        reward2 = price - t2_price

    quality, quality_detail = signal_quality(entry_df, direction)

    return {
        'direction':            direction_label,
        'entry_tf':             entry_tf,
        'tf_label':             TF_LABEL[entry_tf],
        'display_tfs':          TF_DISPLAY[entry_tf],
        'entry':                round(price, 2),
        'stop':                 stop,
        'target1':              round(t1.price, 2),
        'target1_name':         t1.name,
        'target2':              round(t2_price, 2) if t2_price else None,
        'target2_name':         t2_name,
        'near_level':           near.name,
        'risk_pts':             round(risk, 2),
        'reward_pts':           round(reward, 2),
        'reward2_pts':          round(reward2, 2) if reward2 else None,
        'rr':                   rr,
        'risk_per_contract':    round(risk   * mes, 2),
        'reward_per_contract':  round(reward * mes, 2),
        'reward2_per_contract': round(reward2 * mes, 2) if reward2 else None,
        'tf_align':             align,
        'reason':               _build_reason(near.name, entry_tf, direction_label),
        'signal_type':          'pivot',
        'hold_condition':       None,
        'adx':                  round(adx_val, 1) if adx_val is not None else None,
        'adx_tf':               adx_tf,
        'regime':               regime,
        'daily_consumed_pct':   round(consumed * 100, 1) if consumed is not None else None,
        't2_suppressed':        suppress_t2,
        'quality':              quality,
        'quality_detail':       quality_detail,
    }


# ── Pullback Signal ────────────────────────────────────────────────────────────

def _build_pullback_reason(entry_tf: str, direction: str) -> str:
    dir_word = 'bullish' if direction == 'LONG' else 'bearish'
    return f"Pullback to SMMA21 held  |  {TF_LABEL[entry_tf].split('(')[0].strip()} {dir_word} trend continuation"


def check_pullback_setup(entry_tf, direction, price, entry_df,
                         catalog, align,
                         market_context, adx_val, adx_tf, regime) -> Optional[dict]:
    mes    = MES_POINT_VALUE
    min_rr = MIN_RR_SCALP if regime == 'ranging' else MIN_RR

    if not passes_volume_gate(entry_df):
        return None

    consumed    = market_context.get('daily_consumed_pct')
    suppress_t2 = regime == 'ranging' or (consumed is not None and consumed >= ATR_CONSUMED_LIMIT)

    last   = entry_df.iloc[-1]
    smma21 = float(last['smma21'])

    if direction == 'bullish':
        swing_low = find_swing_low(entry_df, lookback=10)
        stop      = round(swing_low - 0.25, 2)
        t1, t2    = catalog.two_targets(price, 'long')
        if t1 is None:
            return None
        risk   = price - stop
        reward = t1.price - price
        if risk <= 0:
            return None
        rr = round(reward / risk, 2)
        if rr < min_rr:
            return None
        direction_label  = 'LONG'
        tf_short         = TF_LABEL[entry_tf].split('(')[0].strip()
        hold_description = f"Hold while {tf_short} closes above SMMA21 ({smma21:.2f}) — exit on close below"

    else:
        swing_high = find_swing_high(entry_df, lookback=10)
        stop       = round(swing_high + 0.25, 2)
        t1, t2     = catalog.two_targets(price, 'short')
        if t1 is None:
            return None
        risk   = stop - price
        reward = price - t1.price
        if risk <= 0:
            return None
        rr = round(reward / risk, 2)
        if rr < min_rr:
            return None
        direction_label  = 'SHORT'
        tf_short         = TF_LABEL[entry_tf].split('(')[0].strip()
        hold_description = f"Hold while {tf_short} closes below SMMA21 ({smma21:.2f}) — exit on close above"

    if suppress_t2:
        t2 = None

    t2_name  = t2.name  if t2 else None
    t2_price = t2.price if t2 else None
    reward2  = None
    if direction_label == 'LONG' and t2_price:
        reward2 = t2_price - price
    elif direction_label == 'SHORT' and t2_price:
        reward2 = price - t2_price

    quality, quality_detail = signal_quality(entry_df, direction)

    return {
        'direction':            direction_label,
        'entry_tf':             entry_tf,
        'tf_label':             TF_LABEL[entry_tf],
        'display_tfs':          TF_DISPLAY[entry_tf],
        'entry':                round(price, 2),
        'stop':                 stop,
        'target1':              round(t1.price, 2),
        'target1_name':         t1.name,
        'target2':              round(t2_price, 2) if t2_price else None,
        'target2_name':         t2_name,
        'near_level':           'SMMA21',
        'risk_pts':             round(risk, 2),
        'reward_pts':           round(reward, 2),
        'reward2_pts':          round(reward2, 2) if reward2 else None,
        'rr':                   rr,
        'risk_per_contract':    round(risk   * mes, 2),
        'reward_per_contract':  round(reward * mes, 2),
        'reward2_per_contract': round(reward2 * mes, 2) if reward2 else None,
        'tf_align':             align,
        'reason':               _build_pullback_reason(entry_tf, direction_label),
        'signal_type':          'pullback',
        'hold_condition':       hold_description,
        'adx':                  round(adx_val, 1) if adx_val is not None else None,
        'adx_tf':               adx_tf,
        'regime':               regime,
        'daily_consumed_pct':   round(consumed * 100, 1) if consumed is not None else None,
        't2_suppressed':        suppress_t2,
        'quality':              quality,
        'quality_detail':       quality_detail,
    }


# ── Range Scalp Signal ─────────────────────────────────────────────────────────

def check_range_scalp(entry_tf, direction, price, entry_df,
                      nearby_levels, catalog, align,
                      market_context, adx_val, adx_tf,
                      vol_note: str, micro_dir: str = 'neutral') -> Optional[dict]:
    mes      = MES_POINT_VALUE
    consumed = market_context.get('daily_consumed_pct')

    if direction == 'bullish':
        support = [lv for lv in nearby_levels if lv.price <= price]
        if not support:
            return None
        near      = max(support, key=lambda lv: lv.price)
        swing_low = find_swing_low(entry_df, lookback=10)
        stop      = round(swing_low - 0.25, 2)
        t1, _     = catalog.two_targets(price, 'long')
        if t1 is None:
            return None
        risk   = price - stop
        reward = t1.price - price
        if risk <= 0:
            return None
        rr = round(reward / risk, 2)
        if rr < MIN_RR_SCALP:
            return None
        direction_label = 'LONG'

    else:
        resistance = [lv for lv in nearby_levels if lv.price >= price]
        if not resistance:
            return None
        near       = min(resistance, key=lambda lv: lv.price)
        swing_high = find_swing_high(entry_df, lookback=10)
        stop       = round(swing_high + 0.25, 2)
        t1, _      = catalog.two_targets(price, 'short')
        if t1 is None:
            return None
        risk   = stop - price
        reward = price - t1.price
        if risk <= 0:
            return None
        rr = round(reward / risk, 2)
        if rr < MIN_RR_SCALP:
            return None
        direction_label = 'SHORT'

    smma_note  = 'smma aligned' if micro_dir == direction else ('smma mixed' if micro_dir == 'neutral' else 'smma against')
    confluence = f"Range scalp at {near.name}  |  {smma_note}"
    if vol_note:
        confluence += f"  |  {vol_note}"

    quality, quality_detail = signal_quality(entry_df, direction, pivot_level=near.price)

    return {
        'direction':            direction_label,
        'entry_tf':             entry_tf,
        'tf_label':             TF_LABEL[entry_tf],
        'display_tfs':          TF_DISPLAY[entry_tf],
        'entry':                round(price, 2),
        'stop':                 stop,
        'target1':              round(t1.price, 2),
        'target1_name':         t1.name,
        'target2':              None,
        'target2_name':         None,
        'near_level':           near.name,
        'risk_pts':             round(risk, 2),
        'reward_pts':           round(reward, 2),
        'reward2_pts':          None,
        'rr':                   rr,
        'risk_per_contract':    round(risk   * mes, 2),
        'reward_per_contract':  round(reward * mes, 2),
        'reward2_per_contract': None,
        'tf_align':             align,
        'reason':               confluence,
        'signal_type':          'range_scalp',
        'hold_condition':       None,
        'adx':                  round(adx_val, 1) if adx_val is not None else None,
        'adx_tf':               adx_tf,
        'regime':               'ranging',
        'daily_consumed_pct':   round(consumed * 100, 1) if consumed is not None else None,
        't2_suppressed':        True,
        'quality':              quality,
        'quality_detail':       quality_detail,
    }


# ── Orchestrator ───────────────────────────────────────────────────────────────

_classifier = RegimeClassifier(adx_trending=ADX_TRENDING, adx_ranging=ADX_RANGING)


def _calc_market_context(tf_data: dict) -> dict:
    ctx = {'daily_atr': None, 'daily_consumed_pct': None}

    daily_df = tf_data.get('1d')
    if daily_df is not None and not daily_df.empty and len(daily_df) >= 14:
        ctx['daily_atr'] = calc_atr(daily_df)

    if ctx['daily_atr']:
        today = datetime.now().date()
        for tf in ['1m', '5m', '15m']:
            df = tf_data.get(tf)
            if df is None or df.empty:
                continue
            today_bars = df[df.index.date == today]
            if today_bars.empty:
                continue
            today_range = float(today_bars['high'].max() - today_bars['low'].min())
            ctx['daily_consumed_pct'] = today_range / ctx['daily_atr']
            break

    return ctx


def generate_signals(tf_data: dict, pivots: dict, market_context: dict = None) -> list:
    """
    Scan all entry timeframes and return valid signals sorted by R/R descending.

    pivots: raw dict[str, float] from get_all_pivots() — e.g. {'D_PP': 5200.0, ...}
    """
    enriched = {}
    for tf, df in tf_data.items():
        if not df.empty and len(df) > 21:
            enriched[tf] = add_smmAs(df)

    align = {tf: ema_alignment(df) for tf, df in enriched.items()}

    if market_context is None:
        market_context = _calc_market_context(tf_data)

    consumed = market_context.get('daily_consumed_pct')
    if consumed is not None and consumed >= ATR_OVEREXTENDED:
        return []

    catalog    = LevelCatalog(pivots)
    signals    = []
    active_tfs = list(CONFIRMATION_MAP.keys()) if ACCOUNT_BALANCE >= SWING_UNLOCK_BALANCE else INTRADAY_ONLY

    # ── Pivot + pullback loop (requires HTF alignment) ────────────────────────
    for entry_tf in active_tfs:
        confirm_tfs = CONFIRMATION_MAP[entry_tf]
        if entry_tf not in enriched:
            continue

        if confirm_tfs:
            if not all(tf in align for tf in confirm_tfs):
                continue
            confirm_directions = [align[tf] for tf in confirm_tfs]
            if len(set(confirm_directions)) != 1:
                continue
            htf_direction = confirm_directions[0]
        else:
            htf_direction = align.get(entry_tf)

        if htf_direction == 'neutral' or htf_direction is None:
            continue

        entry_direction = align.get(entry_tf, 'neutral')
        if entry_direction != htf_direction and entry_direction != 'neutral':
            continue

        result  = _classifier.classify(enriched, entry_tf)
        adx_val = result.adx
        adx_tf  = result.adx_tf
        regime  = result.regime

        entry_df      = enriched[entry_tf]
        price         = float(entry_df['close'].iloc[-1])
        atr_val       = calc_atr(entry_df)
        nearby_levels = [l for l in catalog.levels_near(price, atr_val)
                         if l.name not in LEVEL_BLACKLIST]

        if not nearby_levels:
            continue

        signal = check_pivot_setup(
            entry_tf, htf_direction, price, entry_df,
            nearby_levels, catalog, align,
            market_context, adx_val, adx_tf, regime,
        )
        if signal:
            signals.append(signal)

        pullback_dir = smma_pullback_touch(entry_df)
        if pullback_dir and pullback_dir == htf_direction:
            pb_signal = check_pullback_setup(
                entry_tf, pullback_dir, price, entry_df,
                catalog, align,
                market_context, adx_val, adx_tf, regime,
            )
            if pb_signal:
                signals.append(pb_signal)

    # ── Ranging scalp loop (no HTF confirmation required) ─────────────────────
    seen_scalp_keys: set = set()
    for entry_tf in active_tfs:
        if entry_tf not in enriched:
            continue

        result = _classifier.classify(enriched, entry_tf)
        if result.regime != 'ranging':
            continue

        entry_df      = enriched[entry_tf]
        price         = float(entry_df['close'].iloc[-1])
        atr_val       = calc_atr(entry_df)
        nearby_levels = [l for l in catalog.levels_near(price, atr_val)
                         if l.name not in LEVEL_BLACKLIST]
        if not nearby_levels:
            continue

        micro_dir = smma_micro_alignment(entry_df)

        for try_dir in ['bullish', 'bearish']:
            scalp_key = (entry_tf, try_dir)
            if scalp_key in seen_scalp_keys:
                continue

            vol_note = volume_direction_note(entry_df, try_dir)
            signal   = check_range_scalp(
                entry_tf, try_dir, price, entry_df,
                nearby_levels, catalog, align,
                market_context, result.adx, result.adx_tf,
                vol_note, micro_dir,
            )
            if signal:
                seen_scalp_keys.add(scalp_key)
                signals.append(signal)

    # Assign quality scores (simplified — no JSON rule store on Lambda)
    for sig in signals:
        sig['quality_score'] = _QUALITY_SCORE.get(sig.get('quality', 'C'), 40)
        sig['blocked_by']    = None

    signals.sort(key=lambda x: x['rr'], reverse=True)
    return signals
