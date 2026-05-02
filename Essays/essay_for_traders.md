# MES Signal Bot — For Traders

## What This Is

This is a rules-based signal system for trading MES futures (Micro E-mini S&P 500). It runs in the cloud, scans the market every minute during regular session, and sends a complete trade plan to your phone via Telegram when a setup forms.

It doesn't predict the market. It doesn't use machine learning or proprietary data. It applies a specific technical strategy consistently, without emotion and without missing a setup because you stepped away from the screen.

---

## The Strategy

The strategy comes from a trader named J. Wolfe. The core is simple: three Smoothed Moving Averages (3, 8, 21 period) stacked in alignment tell you the trend direction on any timeframe. Daily, Weekly, and Monthly Pivot Points tell you where price is likely to react. When those two things align — price at a significant level while the moving averages are stacked and pointing the same direction across multiple timeframes — that's the trade.

### Why SMMA, Not EMA

The Smoothed Moving Average uses the formula `alpha = 1/period` in an exponential weighted calculation. It's smoother than an EMA and slower to react to noise. On short timeframes, this matters. The 3-period SMMA doesn't whipsaw on every tick the way an EMA would. It gives you a cleaner read of momentum direction.

The stack alignment rule is strict: all three must be in order (3 above 8 above 21 for longs, reversed for shorts). Partial alignment — the 3 above the 8 but the 8 below the 21 — is not a signal. This filters out a significant amount of noise and choppy mid-trend conditions.

### Why Pivot Points

Pivot Points are calculated from the prior period's high, low, and close. Daily pivots reset every morning. Weekly reset Monday. Monthly reset on the first. They are forward-looking levels: calculated before the session opens and fixed for the entire period.

Traders across institutions use the same pivot formulas. That shared reference makes pivots self-fulfilling in a way that arbitrary horizontal lines aren't. When price approaches a Daily R1 or a Weekly Pivot Point, the market notices. You're not drawing lines on a chart — you're reading the same map everyone else has.

The bot calculates 39 total levels: standard pivots and Fibonacci pivots across daily, weekly, and monthly timeframes. The Fibonacci levels add refinement — they fill in price zones between the standard levels where reactions commonly occur.

---

## Multi-Timeframe Confirmation

A setup on a single timeframe is noise. The same setup confirmed by higher timeframes is a trade.

The confirmation hierarchy is:
- A 1m signal requires agreement on 5m and 15m
- A 5m signal requires agreement on 15m and 1H
- A 15m signal requires agreement on 1H and 4H
- A 1H signal requires agreement on 4H and Daily

Agreement means the SMMA stack on the confirmation timeframe is pointing the same direction as the entry signal. You're not taking a 5m long if the 1H is bearish. The higher timeframe is the governing context.

This multi-timeframe gate is the single most important filter in the system. It eliminates the majority of losing setups — the ones that look good in isolation on a fast chart but are fighting the trend above them.

---

## Market Regime — Why the Bot Adjusts

Not every market condition calls for the same approach. A trending market and a ranging market require completely different tactics. Trading a ranging strategy in a trend means leaving money on the table. Trading a trending strategy in a range means getting chopped up.

The bot uses ADX (Average Directional Index, 14-period) computed on the highest confirmation timeframe to classify the current regime:

**Trending (ADX > 25):** The market is in a defined trend. Momentum is real. In this regime, the bot shows two targets — a near term Target 1 and an extended Target 2. Pullback signals are valid. The goal is to stay in the trade and let it run.

**Neutral (ADX 18–25):** The trend exists but isn't strong. The bot shows only Target 1. Extended targets are unreliable in developing trends. Take the near-term move and reassess.

**Ranging (ADX < 18):** No trend. The higher timeframes are flat. In this regime, the bot ignores higher timeframe SMMA alignment entirely — it's meaningless when the market is in a box. Instead it scalps between pivot levels: long at support, short at resistance, targeting the nearest opposing pivot. These are quick trades with smaller targets and tighter stops.

This regime switching is not optional. A system that applies trending logic in a ranging market is a losing system. ADX is the filter that keeps those two modes separate.

---

## The Three Signal Types

### 1. Pivot Signal
Price is at a significant pivot level. The SMMA stack is aligned on the entry timeframe and all confirmation timeframes agree. This is the core setup — the highest-conviction version of the strategy.

The stop is placed just below the 10-bar swing low (for longs) or above the 10-bar swing high (for shorts). The stop is tight by design. The edge in this strategy comes from high risk/reward, not from wide stops that survive longer.

### 2. Pullback Signal
The market is in a trend. Price has pulled back to the 21 SMMA on the entry timeframe and closed back above it (for longs). The SMMA stack remains aligned. This is trend continuation — re-entering after a retracement rather than chasing a breakout.

The pullback signal includes a Hold line: "Hold while 5m closes above SMMA21." This is the exit rule. Not Target 1. Not Target 2. You stay in the trade as long as price doesn't close through the 21 SMMA. Wicks don't count — only closes. This is how you stay in the big intraday moves instead of taking $40 and watching a 200-point run happen without you.

### 3. Range Scalp
ADX is below 18. The market is in a box. The bot identifies the pivot levels bounding the range and fires signals at the edges — long at support, short at resistance, regardless of what the higher timeframes say.

The range scalp has one target: the nearest opposing pivot on the other side of the range. No extended target. Get in at the boundary, exit at the middle, move on. The signals are valid even when the short-term SMA alignment is mixed — the level is what matters in a ranging market.

---

## Signal Quality Scoring

Every signal receives a quality grade — A, B, or C — based on three price action factors evaluated at the moment the signal fires:

**Bar close quality:** Did the entry bar close in the right part of its range? A long signal where the bar closes at the top of its range is stronger than one where the bar closed near the low.

**Momentum consistency:** How many of the last three completed bars closed in the trade direction? Three out of three is full momentum. Zero out of three is going against recent price action.

**Confirmation bar:** For pivot signals, is there a rejection wick at the level — a bar that tested the pivot and closed on the trade side? For pullback signals, does the current bar engulf the prior bar?

A score of 3 is an A. Score of 2 is a B. Score of 1 or 0 is a C. The grade appears in the Telegram signal card. A-grade signals at historically strong levels are the highest-conviction entries. C-grade signals at unfavorable levels should be skipped or sized down.

---

## Risk Management Built In

Every signal comes with a pre-calculated stop loss, dollar risk per contract, and risk/reward ratio. The bot enforces minimum R/R before sending a signal:

- 2.0:1 minimum for pivot and pullback signals
- 1.5:1 minimum for range scalps

If the natural stop (swing low/high) produces a risk/reward below those thresholds, the signal doesn't fire. It doesn't show up at 1.3:1 with a note saying "marginal setup." It simply doesn't come through. The filter is hard.

Beyond R/R filtering, the bot has a built-in risk management layer that tracks daily state:

- **Maximum 3 trades per day:** After three signals are acted on, no more entries that session.
- **Maximum 5% daily loss:** If paper or live losses exceed 5% of account in a day, a kill switch activates and blocks all further entries.
- **Consecutive loss protection:** Three losses in a row triggers the kill switch automatically. Reset it manually once you've reviewed what happened.
- **Kill switch:** Can be activated manually at any time. Persists across days until explicitly reset.

The 2% account rule per trade is on the trader — the bot shows you the dollar risk per contract, and you make the call. On a $250 account, max risk is $5.00. If the signal shows $12.50 risk, that's a skip.

---

## The Rule Engine

The bot accumulates data on which pivot levels and signal types perform well and which don't. This analysis runs after each backtest and produces ranked performance buckets — win rate, profit factor, and expectancy by level, regime, signal type, and quality tier.

When a bucket has enough data and shows a clear pattern (consistent loser or consistent winner), it can be promoted to an active rule that the bot enforces on every signal. Current active rules: D_FR1 and D_S2 are blacklisted — historical data shows these levels produce net losing results, so the bot blocks signals at those levels regardless of other conditions.

New rules start as candidates. Candidates are suggestions from the data that haven't yet met the threshold to be enforced automatically. They're visible in the dashboard for review and can be promoted or retired manually.

The rule engine doesn't override your judgment. If a D_FR1 signal fires and you see something exceptional on the chart, you can still take the trade. The bot just won't hand it to you automatically.

---

## What the Bot Doesn't Do

It doesn't trade automatically. It doesn't know your account size, your risk tolerance, your open positions, or whether you're watching the screen when it fires. It sends a signal. You decide whether to take it.

It doesn't account for news events. FOMC days, CPI prints, NFP — the bot doesn't know those are coming. The user manual lists a pre-trade checklist that includes checking for upcoming news before entering any position. That check is on you.

It doesn't guarantee any outcome. A 3:1 R/R signal that fires at a historically reliable pivot level is still a trade with real risk. The edge is statistical — over many trades, the math works. On any individual trade, the market can do whatever it wants.

---

## The Execution Discipline

The signal has a short shelf life. Price at a pivot level with SMA alignment is a moment-in-time condition. The bot detects it; your job is to verify it on the WolfeWinner chart and execute within 1–2 minutes.

Verification isn't optional. The bot computes against Schwab API data. The WolfeWinner chart on TradingView is your visual confirmation. If they agree — take the trade. If something looks off on the chart that the bot didn't catch — skip it. The chart is the final authority.

The checklist before every entry:
- Signal direction matches the WolfeWinner chart
- Price is still within 3 points of the entry
- Stop loss is entered before the order is confirmed
- Dollar risk is within 2% of account
- No major news in the next 30 minutes
- No open position already

One trade at a time. Never average down. Never hold through a close below SMMA21 hoping it comes back.

---

## Paper Trading and the Path to Live

The upgrade path is gated by sample size. Thirty paper trades minimum before going live. Not 30 winning trades — 30 trades, wins and losses both, with accurate tracking of entry, stop, and target hit or miss.

The local bot includes a paper broker that tracks this automatically. When a signal fires and you execute it on Tradovate's demo platform, the bot's paper broker follows the position — monitoring each scan for stop hits, target hits, or timeouts and logging the outcome to a CSV. The dashboard shows today's signals, outcomes, P&L, and running metrics without any manual spreadsheet work.

After 30 paper trades, the performance bucket analysis tells you which setups are working and which aren't — by level, regime, signal type, and quality tier. That data feeds the rule engine. Rules get refined. The system learns from its own track record.

The backtest shows this strategy has an edge over two years of historical MES data. The paper trade period is how you verify it behaves the way you expect in real market conditions — with real spreads, real timing pressure, and real decisions — before betting capital on it.

After 30 paper trades with positive expectancy, go live with 1 MES contract, intraday only. After 60 live trades confirming the edge holds, scale to 2–3 contracts. After $3,500 account balance, unlock 4H and Daily swing setups.

The sequence exists for a reason. Don't skip steps.
