from src.features.indicators import find_swing_low, find_swing_high
from src.signals.constants import (
    MIN_RR, MIN_RR_SCALP, ATR_CONSUMED_LIMIT, MES_POINT_VALUE, TF_LABEL, TF_DISPLAY,
)
from src.signals.filters.volume import passes_volume_gate
from src.signals.scoring.quality import signal_quality


def _build_pullback_reason(entry_tf: str, direction: str) -> str:
    dir_word = 'bullish' if direction == 'LONG' else 'bearish'
    return f"Pullback to SMMA21 held  |  {TF_LABEL[entry_tf].split('(')[0].strip()} {dir_word} trend continuation"


def check_pullback_setup(entry_tf, direction, price, entry_df,
                         catalog, align,
                         market_context, adx_val, adx_tf, regime) -> dict | None:
    """
    Trend continuation signal — entry on SMMA21 pullback bounce.
    No pivot proximity required for entry; pivots used only for targets.
    Hold condition: stay in while price closes on the trend side of SMMA21.
    """
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
