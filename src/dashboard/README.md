# src/dashboard

Visualization and reporting UI.

## What belongs here
- `streamlit/` — main Streamlit dashboard app
- `api/` — optional FastAPI layer if dashboard needs a backend API
- `components/` — reusable UI components (charts, tables, signal cards)

## What does NOT belong here
- Trading logic
- Data fetching (dashboard reads from storage layer)

## Status
- All subfolders empty.

## Panels to build (Phase 13)
- Today's signals (with quality tier and regime)
- Active rules (current rule set)
- Candidate rules (rules in testing)
- Paper P/L (today + rolling)
- Best / worst buckets (inference engine output)
- Risk state (daily limits consumed, kill switch status)
- Rejected signals log (what fired but was blocked and why)
- Execution readiness checklist

## Framework decision needed
Streamlit is the default choice — fast to build, no frontend skills required.
Confirm before implementing.
