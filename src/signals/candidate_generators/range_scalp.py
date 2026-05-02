from src.features.indicators import find_swing_low, find_swing_high
from src.signals.constants import MIN_RR_SCALP, MES_POINT_VALUE, TF_LABEL, TF_DISPLAY
from src.signals.scoring.quality import signal_quality


def check_range_scalp(entry_tf, direction, price, entry_df,
                      nearby_levels, catalog, align,
                      market_context, adx_val, adx_tf,
                      vol_note: str, micro_dir: str = 'neutral') -> dict | None:
    """
    Ranging market scalp — pivot to pivot within a defined range.
    No HTF confirmation required. Direction is determined by price position at the level.
    SMMA micro-alignment and volume are confluence notes, not hard filters.
    """
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
