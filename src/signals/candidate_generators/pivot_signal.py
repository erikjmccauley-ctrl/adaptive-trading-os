from src.features.indicators import rejection_at_level, find_swing_low, find_swing_high
from src.signals.constants import (
    MIN_RR, MIN_RR_SCALP, ATR_CONSUMED_LIMIT, MES_POINT_VALUE, TF_LABEL, TF_DISPLAY,
)
from src.signals.filters.volume import passes_volume_gate, passes_volume_direction_gate
from src.signals.scoring.quality import signal_quality


def _build_reason(near_level: str, entry_tf: str, direction: str) -> str:
    dir_word = 'bullish' if direction == 'LONG' else 'bearish'
    return f"Price at {near_level}  |  {TF_LABEL[entry_tf].split('(')[0].strip()} {dir_word} confluence"


def check_pivot_setup(entry_tf, direction, price, entry_df,
                      nearby_levels, catalog, align,
                      market_context, adx_val, adx_tf, regime) -> dict | None:
    """
    Pivot-proximity signal. Entry at a tested support/resistance level with full HTF alignment.
    nearby_levels: list[PivotLevel] from catalog.levels_near(price, atr_val).
    """
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
