"""
Support/resistance level catalog.

Wraps the raw pivot dict (str → float) from get_all_pivots() with typed metadata
so downstream code works with structured objects instead of raw key strings.

Level name convention (from indicators.py):
  D_PP, D_R1, D_R2, D_R3, D_S1, D_S2, D_S3   — daily standard
  D_FR1, D_FR2, D_FR3, D_FS1, D_FS2, D_FS3   — daily fibonacci
  W_*   — weekly,  M_*  — monthly (same suffixes)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PivotLevel:
    name:       str     # e.g. 'D_R1', 'W_PP', 'M_FR2'
    price:      float
    period:     str     # 'daily' | 'weekly' | 'monthly'
    level_type: str     # 'standard' | 'fibonacci'
    role:       str     # 'resistance' | 'support' | 'pivot'

    def __str__(self):
        return f"{self.name} @ {self.price:.2f}  [{self.period} {self.level_type} {self.role}]"


def _parse_level(name: str, price: float) -> PivotLevel:
    """Derive PivotLevel metadata from the naming convention."""
    prefix = name[0]
    period = {'D': 'daily', 'W': 'weekly', 'M': 'monthly'}.get(prefix, 'unknown')

    suffix = name[2:]   # strip 'D_', 'W_', 'M_'
    is_fib = suffix.startswith('F')
    level_type = 'fibonacci' if is_fib else 'standard'

    code = suffix[1:] if is_fib else suffix   # strip leading 'F' from fibonacci
    if code == 'PP':
        role = 'pivot'
    elif code.startswith('R'):
        role = 'resistance'
    else:
        role = 'support'

    return PivotLevel(name=name, price=price, period=period,
                      level_type=level_type, role=role)


class LevelCatalog:
    """
    Typed catalog of all 39 pivot levels for the current session.

    Usage:
        from src.features.indicators import get_all_pivots
        from src.features.support_resistance import LevelCatalog

        pivots  = get_all_pivots(pivot_source)
        catalog = LevelCatalog(pivots)

        nearby = catalog.levels_near(price=7250.0, atr=35.0)
        t1     = catalog.nearest_target(price=7250.0, direction='long')
    """

    def __init__(self, pivot_dict: dict[str, float]):
        self._levels: list[PivotLevel] = [
            _parse_level(name, price)
            for name, price in pivot_dict.items()
        ]

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_levels(self) -> list[PivotLevel]:
        return sorted(self._levels, key=lambda l: l.price)

    def levels_near(self, price: float, atr: float,
                    proximity: float = 0.6) -> list[PivotLevel]:
        """Levels within proximity × ATR of price, sorted by distance."""
        threshold = proximity * atr
        nearby = [l for l in self._levels if abs(l.price - price) <= threshold]
        return sorted(nearby, key=lambda l: abs(l.price - price))

    def levels_above(self, price: float) -> list[PivotLevel]:
        """All levels above price, sorted ascending (nearest first)."""
        return sorted(
            [l for l in self._levels if l.price > price],
            key=lambda l: l.price
        )

    def levels_below(self, price: float) -> list[PivotLevel]:
        """All levels below price, sorted descending (nearest first)."""
        return sorted(
            [l for l in self._levels if l.price < price],
            key=lambda l: l.price,
            reverse=True
        )

    def nearest_target(self, price: float, direction: str) -> Optional[PivotLevel]:
        """
        Return the nearest pivot level in the trade direction.
        direction: 'long' → first level above price
                   'short' → first level below price
        """
        if direction == 'long':
            candidates = self.levels_above(price)
        else:
            candidates = self.levels_below(price)
        return candidates[0] if candidates else None

    def two_targets(self, price: float, direction: str) -> tuple[Optional[PivotLevel], Optional[PivotLevel]]:
        """Return T1 and T2 (the nearest two levels in the trade direction)."""
        if direction == 'long':
            candidates = self.levels_above(price)
        else:
            candidates = self.levels_below(price)
        t1 = candidates[0] if len(candidates) > 0 else None
        t2 = candidates[1] if len(candidates) > 1 else None
        return t1, t2

    def as_dict(self) -> dict[str, float]:
        """Return the raw pivot dict (for compatibility with existing callers)."""
        return {l.name: l.price for l in self._levels}

    def __len__(self) -> int:
        return len(self._levels)

    def __repr__(self) -> str:
        return f"LevelCatalog({len(self._levels)} levels)"
