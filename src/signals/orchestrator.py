from datetime import datetime

from src.features.indicators import add_smmAs, ema_alignment, smma_pullback_touch, smma_micro_alignment, calc_atr
from src.features.regimes import RegimeClassifier
from src.features.support_resistance import LevelCatalog
from src.signals.constants import (
    ACCOUNT_BALANCE, SWING_UNLOCK_BALANCE, INTRADAY_ONLY, CONFIRMATION_MAP,
    ATR_OVEREXTENDED, ADX_TRENDING, ADX_RANGING, LEVEL_BLACKLIST,
)
from src.signals.candidate_generators.pivot_signal import check_pivot_setup
from src.signals.candidate_generators.pullback_signal import check_pullback_setup
from src.signals.candidate_generators.range_scalp import check_range_scalp
from src.signals.filters.volume import volume_direction_note
from src.rules import load_rule_engine as _load_rule_engine

_classifier  = RegimeClassifier(adx_trending=ADX_TRENDING, adx_ranging=ADX_RANGING)
_rule_engine = _load_rule_engine()


def _calc_market_context(tf_data: dict) -> dict:
    """Derive daily ATR and today's consumed range % from available data."""
    from src.features.indicators import calc_atr as _calc_atr
    ctx = {'daily_atr': None, 'daily_consumed_pct': None}

    daily_df = tf_data.get('1d')
    if daily_df is not None and not daily_df.empty and len(daily_df) >= 14:
        ctx['daily_atr'] = _calc_atr(daily_df)

    if ctx['daily_atr']:
        today = datetime.now().date()
        for tf in ['1m', '5m', '15m']:
            df = tf_data.get(tf)
            if df is None or df.empty:
                continue
            today_bars = df[df.index.date == today]
            if today_bars.empty:
                continue
            today_range = float(today_bars['high'].max() - today_bars['low'].min())
            ctx['daily_consumed_pct'] = today_range / ctx['daily_atr']
            break

    return ctx


def generate_signals(tf_data: dict, pivots: dict, market_context: dict | None = None) -> list[dict]:
    """
    Scan all entry timeframes and return valid signals sorted by R/R descending.

    pivots: raw dict[str, float] from get_all_pivots() — e.g. {'D_PP': 5200.0, 'D_R1': 5220.0, ...}
    """
    enriched = {}
    for tf, df in tf_data.items():
        if not df.empty and len(df) > 21:
            enriched[tf] = add_smmAs(df)

    align = {tf: ema_alignment(df) for tf, df in enriched.items()}

    if market_context is None:
        market_context = _calc_market_context(tf_data)

    consumed = market_context.get('daily_consumed_pct')
    if consumed is not None and consumed >= ATR_OVEREXTENDED:
        return []

    catalog    = LevelCatalog(pivots)
    signals    = []
    active_tfs = list(CONFIRMATION_MAP.keys()) if ACCOUNT_BALANCE >= SWING_UNLOCK_BALANCE else INTRADAY_ONLY

    # ── Pivot + pullback loop (requires HTF alignment) ────────────────────────
    for entry_tf in active_tfs:
        confirm_tfs = CONFIRMATION_MAP[entry_tf]
        if entry_tf not in enriched:
            continue

        if confirm_tfs:
            if not all(tf in align for tf in confirm_tfs):
                continue
            confirm_directions = [align[tf] for tf in confirm_tfs]
            if len(set(confirm_directions)) != 1:
                continue
            htf_direction = confirm_directions[0]
        else:
            htf_direction = align.get(entry_tf)

        if htf_direction == 'neutral' or htf_direction is None:
            continue

        entry_direction = align.get(entry_tf, 'neutral')
        if entry_direction != htf_direction and entry_direction != 'neutral':
            continue

        result  = _classifier.classify(enriched, entry_tf)
        adx_val = result.adx
        adx_tf  = result.adx_tf
        regime  = result.regime

        entry_df      = enriched[entry_tf]
        price         = float(entry_df['close'].iloc[-1])
        atr_val       = calc_atr(entry_df)
        nearby_levels = [l for l in catalog.levels_near(price, atr_val)
                         if l.name not in LEVEL_BLACKLIST]

        if not nearby_levels:
            continue

        signal = check_pivot_setup(
            entry_tf, htf_direction, price, entry_df,
            nearby_levels, catalog, align,
            market_context, adx_val, adx_tf, regime,
        )
        if signal:
            signals.append(signal)

        pullback_dir = smma_pullback_touch(entry_df)
        if pullback_dir and pullback_dir == htf_direction:
            pb_signal = check_pullback_setup(
                entry_tf, pullback_dir, price, entry_df,
                catalog, align,
                market_context, adx_val, adx_tf, regime,
            )
            if pb_signal:
                signals.append(pb_signal)

    # ── Ranging scalp loop (no HTF confirmation required) ─────────────────────
    seen_scalp_keys: set = set()
    for entry_tf in active_tfs:
        if entry_tf not in enriched:
            continue

        result = _classifier.classify(enriched, entry_tf)
        if result.regime != 'ranging':
            continue

        entry_df      = enriched[entry_tf]
        price         = float(entry_df['close'].iloc[-1])
        atr_val       = calc_atr(entry_df)
        nearby_levels = [l for l in catalog.levels_near(price, atr_val)
                         if l.name not in LEVEL_BLACKLIST]
        if not nearby_levels:
            continue

        micro_dir = smma_micro_alignment(entry_df)

        for try_dir in ['bullish', 'bearish']:
            scalp_key = (entry_tf, try_dir)
            if scalp_key in seen_scalp_keys:
                continue

            vol_note = volume_direction_note(entry_df, try_dir)
            signal   = check_range_scalp(
                entry_tf, try_dir, price, entry_df,
                nearby_levels, catalog, align,
                market_context, result.adx, result.adx_tf,
                vol_note, micro_dir,
            )
            if signal:
                seen_scalp_keys.add(scalp_key)
                signals.append(signal)

    # Rule engine — block failing candidates, score passing ones
    filtered = []
    for sig in signals:
        passed, reason = _rule_engine.evaluate(sig)
        if passed:
            sig['quality_score'] = _rule_engine.score(sig)
            sig['blocked_by']    = None
            filtered.append(sig)
    signals = filtered

    signals.sort(key=lambda x: x['rr'], reverse=True)
    return signals
