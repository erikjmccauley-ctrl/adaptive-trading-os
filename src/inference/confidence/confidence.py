def assign_confidence(n: int, win_rate: float, profit_factor: float | None) -> str:
    """
    Returns 'A' | 'B' | 'C' | 'insufficient-data'.

    Thresholds are conservative: with < 60 total trades in the current dataset,
    nothing reaches A. That is correct — do not claim confidence that isn't earned.
    """
    if n < 10:
        return 'insufficient-data'
    pf = profit_factor if profit_factor is not None else 0.0
    if n >= 30 and win_rate >= 0.45 and pf >= 2.0:
        return 'A'
    if win_rate >= 0.35 and pf >= 1.0:
        return 'B'
    return 'C'
