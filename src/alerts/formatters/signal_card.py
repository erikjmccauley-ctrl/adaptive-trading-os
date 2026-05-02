from datetime import datetime

_TF_LABEL = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1H', '4h': '4H', '1d': 'Daily'}
_MAX_TRADES = 3  # mirrors src/risk/limits


def _fmt(price: float) -> str:
    return f"{price:,.2f}"


def _check(align_val: str) -> str:
    return '✓' if align_val != 'neutral' else '-'


def format_signal_card(signal: dict, risk_state=None, bucket_stats=None) -> str:
    """
    Build a Telegram HTML signal card.
    risk_state: DailyRiskState | None
    bucket_stats: BucketResult | None  (from BucketEngine.bucket('near_level', 'regime'))
    """
    d = signal['direction']
    emoji = '🟢' if d == 'LONG' else '🔴'

    sig_type_label = {
        'pullback':    ' — PULLBACK',
        'range_scalp': ' — RANGE SCALP',
    }.get(signal.get('signal_type'), '')

    quality = signal.get('quality', '?')
    score = signal.get('quality_score')
    score_str = f' · {score}' if score is not None else ''

    header = f"{emoji} <b>{d} MES  [{signal['tf_label']}]  [{quality}{score_str}]{sig_type_label}</b>"

    # ── price block ──────────────────────────────────────────────────────────
    price_lines = [
        f"Entry:    {_fmt(signal['entry'])}",
        f"Stop:     {_fmt(signal['stop'])}  (-${signal['risk_per_contract']:.2f} / 1 ct)",
        f"T1:       {_fmt(signal['target1'])}  (+${signal['reward_per_contract']:.2f})  [{signal['target1_name']}]",
    ]
    if signal.get('target2'):
        price_lines.append(
            f"T2:       {_fmt(signal['target2'])}  (+${signal['reward2_per_contract']:.2f})  [{signal['target2_name']}]"
        )
    price_block = '<code>' + '\n'.join(price_lines) + '</code>'

    # ── TF alignment ─────────────────────────────────────────────────────────
    display_tfs = signal.get('display_tfs', ['1h', '1d'])
    tf_parts = [
        f"{_TF_LABEL.get(tf, tf)} {_check(signal['tf_align'].get(tf, 'neutral'))}"
        for tf in display_tfs
    ]
    tf_line = 'TF Align:  ' + '  |  '.join(tf_parts)

    # ── context ───────────────────────────────────────────────────────────────
    regime_label = {'trending': 'TRENDING', 'neutral': 'NEUTRAL', 'ranging': 'SCALP'}.get(
        signal.get('regime', 'neutral'), 'NEUTRAL'
    )
    adx = signal.get('adx')
    adx_str = f"  |  ADX {adx} ({signal.get('adx_tf', '').upper()})" if adx else ''
    consumed = signal.get('daily_consumed_pct')
    range_str = f"  |  Range {consumed}%" if consumed is not None else ''
    context_line = f"R/R: {signal['rr']}:1  |  {regime_label}{adx_str}{range_str}"

    # ── assemble ──────────────────────────────────────────────────────────────
    parts = [header, '', price_block, '', tf_line, context_line,
             f"Reason: {signal['reason']}"]

    hold = signal.get('hold_condition')
    if hold:
        parts.append(f"Hold: {hold}")

    # ── bucket stats ──────────────────────────────────────────────────────────
    if bucket_stats is not None:
        n = bucket_stats.n
        if n < 10:
            parts.append(f"\n📊 {signal.get('near_level', '')} · {regime_label.lower()}: insufficient data (n={n})")
        else:
            wr_pct = round(bucket_stats.win_rate * 100)
            pf = f"{bucket_stats.profit_factor:.1f}" if bucket_stats.profit_factor is not None else '—'
            conf = bucket_stats.confidence
            parts.append(
                f"\n📊 {signal.get('near_level', '')} · {regime_label.lower()}: "
                f"{wr_pct}% WR ({bucket_stats.wins}/{n})  PF {pf}  [{conf}]"
            )

    # ── risk state ────────────────────────────────────────────────────────────
    if risk_state is not None:
        trades_left = max(0, _MAX_TRADES - risk_state.trades_taken)
        pnl = risk_state.daily_pnl
        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        ks = '  ⛔ KILL SWITCH' if risk_state.kill_switch_active else ''
        parts.append(f"⏱ Trades left: {trades_left}/{_MAX_TRADES}  |  P&amp;L: {pnl_str}{ks}")
    else:
        ts = datetime.now().strftime('%I:%M %p')
        parts.append(f"⏱ {ts}")

    return '\n'.join(parts)
