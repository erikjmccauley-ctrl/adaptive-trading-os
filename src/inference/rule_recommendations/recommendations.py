from __future__ import annotations
from src.inference.bucket_analysis.bucket_engine import BucketResult


def generate_recommendations(buckets: list[BucketResult], dimension: str) -> list[str]:
    """
    Surface rule recommendations from a single-dimension bucket analysis.

    Tags:
      ⚠  AVOID  — consistent 0% win rate (n >= 5), no profit
      ✓  KEEP   — best performing bucket with positive edge
      ℹ  WATCH  — zero wins but small sample (n < 10); or noteworthy outlier

    Does not generate recommendations for empty or trivially small samples (n < 3).
    """
    recs: list[str] = []
    if not buckets:
        return recs

    valid = [b for b in buckets if b.n >= 3]
    if not valid:
        return recs

    best = max(valid, key=lambda b: b.net_pnl)

    for b in valid:
        val = b.key.get(dimension, str(b.key))
        pf_str = f'PF {b.profit_factor:.2f}' if b.profit_factor is not None else 'PF n/a'
        n_wins = b.wins

        # AVOID: zero wins with enough sample to be meaningful
        if b.win_rate == 0.0 and b.n >= 5:
            recs.append(
                f'⚠  AVOID    {val}: 0/{b.n} wins, {pf_str} — '
                f'consider blacklisting or requiring extra confluence'
            )
            continue

        # AVOID: near-zero win rate with negative edge and decent sample
        if b.win_rate < 0.15 and b.n >= 8 and (b.profit_factor or 0) < 0.5:
            recs.append(
                f'⚠  AVOID    {val}: {n_wins}/{b.n} wins ({b.win_rate:.0%}), {pf_str} — '
                f'weak edge, consider filter'
            )
            continue

        # KEEP: best performing bucket with positive edge
        if b is best and b.net_pnl > 0 and b.n >= 5:
            conf_tag = f'[{b.confidence}]' if b.confidence not in ('insufficient-data',) else ''
            recs.append(
                f'✓  KEEP     {val}: {n_wins}/{b.n} wins ({b.win_rate:.0%}), '
                f'{pf_str}, net ${b.net_pnl:+.0f} {conf_tag} — current behavior correct'
            )
            continue

        # WATCH: zero wins but small sample
        if b.win_rate == 0.0 and b.n < 5:
            recs.append(
                f'ℹ  WATCH    {val}: 0/{b.n} wins — insufficient data, monitor'
            )
            continue

        # WATCH: positive edge but below confidence threshold
        if b.confidence == 'B' and b is not best:
            recs.append(
                f'ℹ  WATCH    {val}: {n_wins}/{b.n} wins ({b.win_rate:.0%}), '
                f'{pf_str} [B] — positive edge, build sample'
            )

    return recs
