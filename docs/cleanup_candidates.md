---
name: cleanup_candidates
description: Tracks known cleanup items deferred to future phases — unused imports, dead code, future refactors.
---

# Cleanup Candidates

_Created: Phase 17 (2026-04-30). Review before each major release._

---

## Unused Imports (Phase 17 scan — AST-based)

**Note:** `__init__.py` re-export files show all names as "unused" — these are false positives
because the AST scanner cannot see that callers import from them. Do NOT remove exports from
`__init__.py` files without auditing all callers first.

### Real candidates to review

| File | Import | Status |
|---|---|---|
| `src/alerts/telegram/provider.py` | `os` | Possibly unused — audit before removing |
| `src/data_sources/schwab/validator.py` | `datetime` | Possibly unused — audit before removing |
| `src/features/regimes/volatility.py` | `calc_atr` | Possibly unused — audit before removing |
| `src/data_sources/schwab/provider.py` | `ValidationResult` | Possibly unused — audit before removing |

### Confirmed false positives (do not remove)

All `__init__.py` files — they re-export names for callers and will always appear "unused"
to static analyzers.

`from __future__ import annotations` in dashboard and inference files — this is a real
directive (deferred annotation evaluation), not an unused import.

`field` in `walk_forward.py` and `config.py` — used by dataclass field definitions which
the AST scanner misses.

---

## Deferred Phase Items

| Item | Phase | Status |
|---|---|---|
| Integration tests (data → features → signals → risk → alert) | Phase 16 | Deferred — needs proper fixture infrastructure |
| Backtest fixture data (`tests/fixtures/`) | Phase 16 | Deferred |
| Backtest correctness tests (no-lookahead) | Phase 16 | Deferred |
| Regression tests for known signals | Phase 16 | Deferred |
| `from __future__ import annotations` audit | — | Minor — no functional impact |
| S3Storage / DynamoDBStateStore implementations | Phase 14 | Blocked on AWS infra |
| Lambda handler migration | Phase 14 | Blocked on infra repo |
| ATR-based stop test variants (Phase 7 item) | Phase 7 | Still open |
| CLAUDE.md file structure diagram update (D-09) | Review | Low priority |
| Rule versioning | Phase 9 | Deferred post Phase 10 |
| Auto-promotion rules after N trades | Phase 9 | Deferred |

---

## Future Organizational Items

- `Essays/` folder at root — essays are informational; keep as-is unless a docs/ migration makes sense
- `inference_results.csv` at root — output of `inference.py`; could move to `data/` but depends on backtest workflow
