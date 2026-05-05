# MES Signal Bot — User Manual

**Strategy:** 3/8/21 SMMA + Daily/Weekly/Monthly Pivot Points + Multi-Timeframe Alignment
**Chart:** TradingView — WolfeWinner layout (by J. Wolfe)
**Instrument:** MES (Micro E-mini S&P 500)
**Data:** Schwab API — real-time live data
**Execution:** Manual on Tradovate (bot signals, you place the trade)

---

## What This Bot Does

Scans MES across 6 timeframes every 30 seconds during market hours. It detects three types of setups and fires a signal with a specific entry, stop loss, and profit target(s). You take that signal to Tradovate and place the trade manually.

The bot reads the market regime in real time and adjusts what it looks for:
- **Trending market** → looks for price at pivot levels and pullbacks to SMMA21 with big targets
- **Ranging market** → scalps between the top and bottom of the range, both long and short

---

## First-Time Setup

### Install dependencies (one time only)
```
cd "C:\Users\emcca\Desktop\Trading Bot"
pip install -r requirements.txt
```

### Run the bot
```
cd "C:\Users\emcca\Desktop\Trading Bot"
python main.py
```

### Stop the bot
Press `Ctrl + C`

---

## The Three Signal Types

### 1. Standard Signal — Trending / Neutral Market
Fires when the SMMA stack is aligned on multiple timeframes AND price is at a pivot level. This is the base setup.

```
═══════════════════════════════════
  SIGNAL: LONG MES  [5m (scalp)]
═══════════════════════════════════
  Entry:      7,190.25
  Stop Loss:  7,187.75  (-$12.50 / 1 contract)
  Target 1:   7,198.03  (+$38.90)  [W_FR1]
  Target 2:   7,236.67  (+$232.10)  [D_R2]
  TF Align:   15m ✓  |  1H ✓  |  Daily ✓
  Action:     Click BUY on Tradovate
  Reason:     Price at D_FR1  |  5m bullish confluence
  R/R:        3.11:1
  Context:    NEUTRAL  |  ADX 21.4 (1H)  |  Range 44%
  Data:       🟢 Live (Schwab)
═══════════════════════════════════
```

### 2. Pullback Signal — Trend Continuation
Fires when the market is trending and price pulls back to the SMMA21 line then bounces off it. This is the high R/R intraday trade — like the 14:1 move seen April 27.

The key difference: the **Hold** line tells you when to EXIT. Stay in the trade as long as price doesn't close through SMMA21 on the entry timeframe. That's how you hold the big moves.

```
═══════════════════════════════════
  SIGNAL: LONG MES  [5m (scalp)] — PULLBACK
═══════════════════════════════════
  Entry:      7,248.50
  Stop Loss:  7,241.25  (-$36.25 / 1 contract)
  Target 1:   7,312.50  (+$320.00)  [D_R2]
  Target 2:   7,336.75  (+$441.25)  [W_R1]
  TF Align:   15m ✓  |  1H ✓  |  Daily ✓
  Action:     Click BUY on Tradovate
  Reason:     Pullback to SMMA21 held  |  5m bullish trend continuation
  R/R:        14.33:1
  Hold:       Hold while 5m closes above SMMA21 (7,241.00) — exit on close below
  Context:    TRENDING  |  ADX 31.2 (1H)  |  Range 52%
  Data:       🟢 Live (Schwab)
═══════════════════════════════════
```

**Hold rule:** The price on the 5m chart must CLOSE (not just wick) below SMMA21 to trigger your exit. Wicks don't count. A close below = trend is over, get out.

### 3. Range Scalp — Choppy / Ranging Market
Fires when the market is in a defined range (ADX below 18). Goes both LONG at support and SHORT at resistance regardless of higher timeframe direction — because in a range, the higher timeframes are flat anyway. Targets only the nearest pivot level (the other side of the range box). No second target.

```
═══════════════════════════════════
  SIGNAL: SHORT MES  [1m (scalp)] — RANGE SCALP
═══════════════════════════════════
  Entry:      7,207.75
  Stop Loss:  7,210.25  (-$12.50 / 1 contract)
  Target 1:   7,200.50  (+$36.25)  [W_PP]
  TF Align:   5m -  |  15m -  |  1H -
  Action:     Click SELL on Tradovate
  Reason:     Range scalp at D_FR1  |  smma mixed  |  vol 58% bearish
  R/R:        2.9:1
  Context:    SCALP  |  ADX 13.1 (15M)  |  Range 41%
  Data:       🟢 Live (Schwab)
═══════════════════════════════════
```

The `-` in TF Align is normal for range scalps — the higher timeframes are neutral in a range.

---

## Reading the Output

### Status Block (prints every 10 scans)
```
--------------------------------------------------
  MES  7,194.75  |  10:32:15 AM  |  🟢 Live (Schwab)
  Daily ^  1H ^  15m ^  5m ^  1m ^

  Resistance (targets for SELL trades):
    ^  W_FR1          7,198.03  (+3.28 pts)
    ^  D_FR2          7,197.80  (+3.05 pts)
  -- current price: 7,194.75 --
  Support (targets for BUY trades):
    v  D_R1           7,190.08  (-4.67 pts)
    v  D_FR1          7,173.79  (-20.96 pts)
--------------------------------------------------
```

| Symbol | Meaning |
|---|---|
| `^` next to timeframe | Bullish — SMMA 3 > 8 > 21 |
| `v` next to timeframe | Bearish — SMMA 3 < 8 < 21 |
| `-` next to timeframe | Neutral / no clear trend |
| `^` next to a level | Resistance above price |
| `v` next to a level | Support below price |

### Context Line
Every signal shows a Context line that tells you what kind of market you're in:

| Context | ADX | What it means |
|---|---|---|
| `TRENDING` | > 25 | Strong trend — T1 + T2 both shown, hold for the run |
| `NEUTRAL` | 18–25 | Developing trend — T1 only |
| `SCALP` | < 18 | Ranging market — range scalp mode, smallest targets |

`Range XX%` = how much of the typical daily range has already been used today. At 90%+ the second target is hidden. At 110%+ no signals fire (day is overdone).

`ADX XX (TF)` = the trend strength reading and which timeframe it's computed on.

### Reason Line — Range Scalp Quality Notes
For range scalps, the Reason line shows confluence indicators:
- `smma aligned` = the fast SMMA (3 vs 8) agrees with the trade direction — strongest quality
- `smma mixed` = SMAs neutral at the level — still valid, be aware
- `smma against` = SMAs leaning the other way — weakest signal, use extra caution
- `vol XX% bullish/bearish` = recent volume pressure — supporting info

### Pivot Level Names
| Prefix | Timeframe |
|---|---|
| `D_` | Daily (resets daily) |
| `W_` | Weekly (resets Monday) |
| `M_` | Monthly (resets 1st) |

| Suffix | Meaning |
|---|---|
| `PP` | Pivot Point — anchor level |
| `R1, R2, R3` | Standard resistance levels |
| `S1, S2, S3` | Standard support levels |
| `FR1, FR2, FR3` | Fibonacci resistance |
| `FS1, FS2, FS3` | Fibonacci support |

### No-Signal Line
```
  [10:45:22 AM]  No signal  |  Daily ✓  |  1H ✓  |  15m ✓  |  🟢 Live (Schwab)
```
Normal. Most scans show no signal. The bot fires only when conditions align.

---

## Signal Cooldowns

Once a signal fires at a level, the same signal won't re-fire at that same level and direction for:
- 1m signals: 5 minutes
- 5m signals: 15 minutes
- 15m signals: 30 minutes
- 1H signals: 60 minutes
- Range scalps: half the above (they can legitimately repeat each bounce)

This prevents the bot from sending the same setup 40 times in a row like it used to.

---

## How to Execute a Signal

Act within 1-2 minutes — setups can move quickly.

1. Open Tradovate → pull up MES on the timeframe shown in the signal
2. Verify price is still within 3 points of the entry price
3. Check your WolfeWinner chart — does it agree with the signal direction?
4. Place a **Limit Order** at Entry (or Market if price is moving fast)
5. **Immediately** set your **Stop Loss** at the Stop price shown
6. Set **Take Profit** at Target 1
7. Optional: set a second take profit at Target 2 (for standard / pullback signals only)

**For pullback signals:** use the Hold line as your exit rule instead of Target 1 alone. Watch for a 5m close through SMMA21 — that's when you exit.

### Pre-trade checklist
- [ ] Signal direction matches WolfeWinner chart
- [ ] Price still within 3 points of entry
- [ ] Stop loss entered before confirming order
- [ ] Dollar risk is within 2% of my account
- [ ] No major news in the next 30 minutes
- [ ] No open trade already

---

## Risk Rules

| Rule | Value |
|---|---|
| Max risk per trade | 2% of account |
| On $250 account | $5.00 max |
| MES point value | $5.00/point |
| MES tick value | $1.25/tick (0.25 pts) |
| Tradovate margin | $50/contract (returned when closed) |
| Max contracts | 1 MES |
| Max open trades | 1 at a time |

If the Stop Loss dollar amount exceeds your 2% limit — skip the signal. The next one will have a tighter setup.

---

## Account Growth Gates

| Balance | Timeframes Active | Trade Types |
|---|---|---|
| $250 – $3,499 | 1m, 5m, 15m, 1H | Scalp + Intraday |
| $3,500+ | All 6 TFs | Scalp + Intraday + Swing |

**To update your balance in the bot:**
1. Open `src/signals.py`
2. Find `ACCOUNT_BALANCE = 250.00`
3. Change to your current balance
4. Save — takes effect on next scan

---

## When to Skip a Signal

- Dollar risk shown exceeds 2% of your account
- Can't verify on WolfeWinner within 2 minutes
- Major news just dropped (FOMC, CPI, jobs report)
- Already in an open trade
- First 15 minutes of session (9:30–9:45 AM ET)
- Last 15 minutes of session (3:45–4:00 PM ET)
- Entry has moved more than 3 points from the signal price
- Context line shows `Range 90%+` or higher — day has little room left

---

## Market Hours

Bot scans regular session only:
- **Open:** 9:30 AM Eastern
- **Close:** 4:00 PM Eastern

Prints "Market closed" outside those hours and checks every 5 minutes.

---

## Data Source

**🟢 Live (Schwab)** — real-time data. Schwab API connected. All signal prices are live.

The Schwab token is self-maintaining. The Lambda writes a refreshed token back to S3 after every data fetch, so the connection stays alive indefinitely without manual intervention. If you ever see 🟡 delayed, run `python scripts/maintenance/auth_schwab.py` from the trading bot directory (not system32) and re-upload to S3.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Schwab error / no data | Token stale — run `python scripts/maintenance/auth_schwab.py` from the trading bot directory, then re-upload to S3 |
| No signals all day | Normal in choppy or low-ADX markets — the bot is filtering noise |
| Signal fired but looked wrong | Drop a screenshot in the `charts/` folder and ask Claude to analyze |
| "Market closed" during trading hours | Check PC clock timezone — should be Eastern or auto |
| Same signal repeating | Cooldowns should prevent this — if it's happening, note the (TF, level, direction) and report |

---

## Charts Folder

Drop TradingView screenshots into `Trading Bot/charts/` and mention them in the conversation. Claude reads images directly and can analyze the setups you're seeing to improve the bot's detection logic.

---

## Quick Reference

```
Run:   python main.py
Stop:  Ctrl + C

LONG  = Click BUY on Tradovate
SHORT = Click SELL on Tradovate

MES: $5.00/point  |  $1.25/tick  |  $50 margin/contract
$250 account: max $5 risk  |  1 contract

Signal types:
  Standard  → price at pivot, SMMA aligned, T1 + T2
  Pullback  → SMMA21 bounce in trend, use Hold line to exit
  Range Scalp → both long/short within range box, T1 only

Context: TRENDING = let it run | SCALP = take T1 and done

Skip if: news incoming, already in trade, entry moved 3+ pts,
         risk > 2%, first/last 15min of session, Range 90%+
```

---

## Upgrade Path

| Step | Trigger | What Changes |
|---|---|---|
| ✅ Done | — | Schwab real-time data live |
| ✅ Done | — | Signal dedup, ADX regime, volume filter, pullback + range scalp signals |
| Now | — | Paper trade 30+ signals on Tradovate demo |
| After 30 trades | Positive expectancy | Run backtest, review by signal type |
| $1,000 balance | — | Tradovate API — bot places orders automatically |
| $3,500 balance | — | 4H and Daily swing signals unlock |
| 60+ live trades | Confirmed edge | Scale to 2-3 contracts |
