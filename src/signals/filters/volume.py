from src.signals.constants import MIN_VOLUME_RATIO, VOLUME_DIRECTION_BARS


def passes_volume_gate(entry_df, min_ratio: float = MIN_VOLUME_RATIO) -> bool:
    """3-bar avg volume >= min_ratio × 20-bar avg. Returns True (pass) if data is insufficient."""
    if len(entry_df) < 23:
        return True
    avg_vol_20 = float(entry_df['volume'].iloc[-21:].mean())
    recent_vol = float(entry_df['volume'].iloc[-3:].mean())
    if avg_vol_20 <= 0:
        return True
    return recent_vol >= min_ratio * avg_vol_20


def passes_volume_direction_gate(entry_df, direction: str, threshold: float = 0.45) -> bool:
    """
    Confirm volume pressure is not strongly against the trade direction.
    bullish: up_vol / total >= threshold.  bearish: dn_vol / total >= threshold.
    Returns True (pass) if data is insufficient.
    """
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
    """Returns a short confluence string about volume pressure — informational only."""
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
