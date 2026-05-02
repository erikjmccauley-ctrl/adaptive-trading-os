import sys
from colorama import Fore, Style, init
from datetime import datetime
init(autoreset=True)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

TF_LABEL    = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1H', '4h': '4H', '1d': 'Daily'}
ALIGN_ICON  = {'bullish': '^', 'bearish': 'v', 'neutral': '-'}
ALIGN_COLOR = {'bullish': Fore.GREEN, 'bearish': Fore.RED, 'neutral': Fore.YELLOW}
SEP         = chr(9552) * 35
SEP2        = '-' * 50

TRADOVATE_MARGIN = 50.00


def _data_tag():
    return "🟢 Live (Schwab)"


def _fmt(price):
    return f"{price:,.2f}"


def _check(align_val):
    return chr(10003) if align_val != 'neutral' else 'x'


def print_signal(signal):
    d   = signal['direction']
    col = Fore.GREEN if d == 'LONG' else Fore.RED

    action = 'Click BUY on Tradovate' if d == 'LONG' else 'Click SELL on Tradovate'

    # TF align line — only show the relevant higher TFs for this entry timeframe
    display_tfs = signal.get('display_tfs', ['1h', '1d'])
    tf_align_line = '  |  '.join(
        f"{TF_LABEL.get(tf, tf)} {_check(signal['tf_align'].get(tf, 'neutral'))}"
        for tf in display_tfs
    )

    quality   = signal.get('quality', '?')
    qual_col  = {
        'A': Fore.GREEN if d == 'LONG' else Fore.RED,
        'B': Fore.GREEN if d == 'LONG' else Fore.RED,
        'C': Fore.YELLOW,
    }.get(quality, col)

    score     = signal.get('quality_score')
    score_str = f' · {score}' if score is not None else ''
    score_col = (Fore.GREEN if score is not None and score >= 70
                 else Fore.YELLOW if score is not None and score >= 50
                 else Fore.RED if score is not None
                 else col)

    print(f"\n{col}{SEP}")
    sig_type = {
        'pullback':    ' — PULLBACK',
        'range_scalp': ' — RANGE SCALP',
    }.get(signal.get('signal_type'), '')
    print(f"{col}  SIGNAL: {d} MES  [{signal['tf_label']}]  [{quality}{score_col}{score_str}{col}]{sig_type}")
    print(f"{col}{SEP}")
    print(f"{col}  Entry:      {_fmt(signal['entry'])}")
    print(f"{col}  Stop Loss:  {_fmt(signal['stop'])}  (-${signal['risk_per_contract']:.2f} / 1 contract)")
    print(f"{col}  Target 1:   {_fmt(signal['target1'])}  (+${signal['reward_per_contract']:.2f})  [{signal['target1_name']}]")
    if signal['target2']:
        print(f"{col}  Target 2:   {_fmt(signal['target2'])}  (+${signal['reward2_per_contract']:.2f})  [{signal['target2_name']}]")
    print(f"{col}  TF Align:   {tf_align_line}")
    print(f"{col}  Action:     {action}")
    print(f"{col}  Reason:     {signal['reason']}")
    q_detail  = signal.get('quality_detail', '')
    score_tag = f'  |  Score {score}/100' if score is not None else ''
    print(f"{qual_col}  Quality:    {quality}  ({q_detail}){score_col}{score_tag}{col}")
    print(f"{col}  R/R:        {signal['rr']}:1")
    hold = signal.get('hold_condition')
    if hold:
        print(f"{col}  Hold:       {hold}")

    # Market context line — regime, ADX, daily range consumed
    regime_label = {'trending': 'TRENDING', 'neutral': 'NEUTRAL', 'ranging': 'SCALP'}.get(
        signal.get('regime', 'neutral'), 'NEUTRAL'
    )
    ctx_parts = [regime_label]
    adx = signal.get('adx')
    if adx is not None:
        adx_tf = signal.get('adx_tf', '').upper()
        ctx_parts.append(f"ADX {adx} ({adx_tf})")
    consumed = signal.get('daily_consumed_pct')
    if consumed is not None:
        t2_note = ' — T2 off' if signal.get('t2_suppressed') else ''
        ctx_parts.append(f"Range {consumed}%{t2_note}")
    print(f"{col}  Context:    {'  |  '.join(ctx_parts)}")

    print(f"{col}  Data:       {_data_tag()}")
    print(f"{col}{SEP}")
    print(f"  {Fore.WHITE}Signal at {datetime.now().strftime('%I:%M:%S %p')}\n")


def print_signals(signals):
    if not signals:
        return
    print(f"\n{Fore.WHITE}  {len(signals)} signal(s) found — ranked by R/R:")
    for s in signals:
        print_signal(s)


def print_status(price, pivots, align):
    ts = datetime.now().strftime('%I:%M:%S %p')
    print(f"\n{Fore.CYAN}{SEP2}")
    print(f"{Fore.CYAN}  MES  {_fmt(price)}  |  {ts}  |  {_data_tag()}")

    tf_row = "  "
    for tf in ['1d', '1h', '15m', '5m', '1m']:
        if tf in align:
            a = align.get(tf, 'neutral')
            c = ALIGN_COLOR[a]
            tf_row += f"{c}{TF_LABEL[tf]} {ALIGN_ICON[a]}  "
    print(tf_row)

    above = sorted([(k, v) for k, v in pivots.items() if v > price], key=lambda x: x[1])[:4]
    below = sorted([(k, v) for k, v in pivots.items() if v < price], key=lambda x: x[1], reverse=True)[:4]

    print(f"\n{Fore.WHITE}  Resistance (targets for SELL trades):")
    for name, level in reversed(above):
        print(f"{Fore.RED}    ^  {name:12s} {_fmt(level):>10s}  (+{level-price:.2f} pts)")

    print(f"{Fore.CYAN}  -- current price: {_fmt(price)} --")

    print(f"{Fore.WHITE}  Support (targets for BUY trades):")
    for name, level in below:
        print(f"{Fore.GREEN}    v  {name:12s} {_fmt(level):>10s}  (-{price-level:.2f} pts)")

    print(f"{Fore.CYAN}{SEP2}")


def print_no_signal(align):
    ts = datetime.now().strftime('%I:%M:%S %p')
    tf_summary = '  |  '.join(
        f"{TF_LABEL.get(tf, tf)} {_check(align.get(tf, 'neutral'))}"
        for tf in ['1d', '1h', '15m', '5m', '1m'] if tf in align
    )
    print(f"{Fore.YELLOW}  [{ts}]  No signal  |  {tf_summary}  |  {_data_tag()}")


def print_header():
    print(f"{Fore.CYAN}")
    print("  +------------------------------------------------+")
    print("  |   MES Signal Bot  --  3/8/21 SMMA + Pivots    |")
    print("  |   Scanning: 1m / 5m / 15m / 1H / 4H / Daily  |")
    print("  +------------------------------------------------+")
    print(f"{Style.RESET_ALL}")
