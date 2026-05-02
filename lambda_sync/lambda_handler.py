import json
import boto3
import urllib.request
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from src.data import get_multi_tf_data, get_pivot_source_ohlc
from src.indicators import get_all_pivots
from src.signals import generate_signals

MARKET_OPEN  = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)
_ET = ZoneInfo("America/New_York")

# Cache credentials across warm invocations — avoids Secrets Manager call every minute
_creds = None


def _get_creds():
    global _creds
    if _creds is None:
        client = boto3.client('secretsmanager')
        secret = client.get_secret_value(SecretId='trading-bot/telegram')
        data   = json.loads(secret['SecretString'])
        _creds = data['bot_token'], data['chat_id']
    return _creds


def send_telegram(token, chat_id, message):
    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({
        "chat_id":    chat_id,
        "text":       message,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)


_TF_LABEL = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1H', '4h': '4H', '1d': 'Daily'}


def _fmt(price):
    return f"{price:,.2f}"


def _check(align_val):
    return '✓' if align_val != 'neutral' else '-'


def format_signal(signal, now_et):
    d     = signal['direction']
    emoji = '🟢' if d == 'LONG' else '🔴'

    sig_type_label = {
        'pullback':    ' — PULLBACK',
        'range_scalp': ' — RANGE SCALP',
    }.get(signal.get('signal_type'), '')

    quality   = signal.get('quality', '?')
    score     = signal.get('quality_score')
    score_str = f' · {score}' if score is not None else ''
    header    = f"{emoji} <b>{d} MES  [{signal['tf_label']}]  [{quality}{score_str}]{sig_type_label}</b>"

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

    display_tfs = signal.get('display_tfs', ['1h', '1d'])
    tf_parts    = [
        f"{_TF_LABEL.get(tf, tf)} {_check(signal['tf_align'].get(tf, 'neutral'))}"
        for tf in display_tfs
    ]
    tf_line = 'TF Align:  ' + '  |  '.join(tf_parts)

    regime_label = {'trending': 'TRENDING', 'neutral': 'NEUTRAL', 'ranging': 'SCALP'}.get(
        signal.get('regime', 'neutral'), 'NEUTRAL'
    )
    adx       = signal.get('adx')
    adx_str   = f"  |  ADX {adx} ({signal.get('adx_tf', '').upper()})" if adx else ''
    consumed  = signal.get('daily_consumed_pct')
    range_str = f"  |  Range {consumed}%" if consumed is not None else ''
    context_line = f"R/R: {signal['rr']}:1  |  {regime_label}{adx_str}{range_str}"

    parts = [header, '', price_block, '', tf_line, context_line,
             f"Reason: {signal['reason']}"]

    hold = signal.get('hold_condition')
    if hold:
        parts.append(f"Hold: {hold}")

    parts.append(f"⏱ {now_et.strftime('%I:%M %p ET')}")

    return '\n'.join(parts)


def lambda_handler(event, context):
    now_et   = datetime.now(tz=_ET)
    now_time = now_et.time()

    if not (MARKET_OPEN <= now_time <= MARKET_CLOSE):
        print(f"Outside market hours  |  {now_et.strftime('%H:%M ET')}")
        return {"statusCode": 200, "body": "Outside market hours"}

    tf_data      = get_multi_tf_data()
    pivot_source = get_pivot_source_ohlc()
    pivots       = get_all_pivots(pivot_source)
    signals      = generate_signals(tf_data, pivots)

    if not signals:
        print(f"No signal  |  {now_et.strftime('%H:%M ET')}")
        return {"statusCode": 200, "body": "No signal"}

    token, chat_id = _get_creds()
    for signal in signals:
        send_telegram(token, chat_id, format_signal(signal, now_et))
        print(
            f"Signal sent: {signal.get('direction')} {signal.get('entry_tf')} "
            f"@ {signal.get('near_level')}  [{signal.get('quality')} · {signal.get('quality_score')}]"
        )

    return {"statusCode": 200, "body": f"{len(signals)} signal(s) sent"}
