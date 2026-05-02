from src.features.indicators import (
    bar_close_quality, momentum_consistency, rejection_at_level, is_engulfing,
)


def signal_quality(entry_df, direction: str, pivot_level=None) -> tuple[str, str]:
    """
    Score signal quality from three price action components (0-3 points each):
      1. Bar close quality  — close in upper/lower 35% of bar range
      2. Momentum           — 2+ of last 3 completed bars closed in trade direction
      3. Engulfing bar      — for pivot/pullback signals (pivot_level=None)
         Rejection wick     — for range scalp signals (pivot_level=price)

    Returns (tier, detail_string).  tier ∈ {'A', 'B', 'C'}
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
