# Bot Logic Reference

Exact description of what the code does, in execution order.

---

## 1. Data Pipeline (`src/data.py`)

### What gets fetched

| Bot TF | Schwab interval | Days back |
|--------|----------------|-----------|
| 1m     | 1m             | 5         |
| 5m     | 5m             | 10        |
| 15m    | 15m            | 20        |
| 1h     | 30m → resample | 30        |
| 4h     | derived from 1h | —        |
| 1d     | 1d             | 730       |

- **1H bars:** Schwab doesn't have a 1H endpoint. Fetches 30m bars, resamples to 1H with `resample('1h').agg(OHLCV)`.
- **4H bars:** Resampled from the 1H DataFrame with `resample('4h').agg(OHLCV)`. Not fetched separately.
- **Extended hours:** excluded (`need_extended_hours_data=False`).

### Pivot source

Fetches 730 days of daily bars. Resamples to weekly (`resample('W')`) and monthly (`resample('ME')`). These three DataFrames go to `get_all_pivots()`.

---

## 2. Indicators (`src/indicators.py`)

### SMMA

```
series.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
```

Three periods applied to close: **3, 8, 21**. Stored as `smma3`, `smma8`, `smma21` on the DataFrame.

### Full stack alignment

```
bullish: smma3 > smma8 > smma21
bearish: smma3 < smma8 < smma21
neutral: anything else
```

Used for HTF confirmation and entry TF direction check.

### Micro alignment

```
bullish: smma3 > smma8
bearish: smma3 < smma8
neutral: equal
```

Used only as a confluence note in range scalp signals. Never a hard gate.

### Pullback touch detection (`smma_pullback_touch`)

Checks the last 4 completed bars before the current bar.

**Bullish pullback (returns 'bullish'):**
1. Current bar: full stack is bullish (`smma3 > smma8 > smma21`)
2. Any of the last 4 bars had `low <= smma21` (price touched or undercut the line)
3. Current bar closes above `smma21`

**Bearish pullback (returns 'bearish'):** mirror image — stack bearish, recent bar touched above smma21, current bar closes below.

Returns `None` if neither condition is met.

### Pivot calculations

**Standard pivots** (from prior period OHLC):
```
PP = (H + L + C) / 3
R1 = 2×PP − L
R2 = PP + (H − L)
R3 = H + 2×(PP − L)
S1 = 2×PP − H
S2 = PP − (H − L)
S3 = L − 2×(H − PP)
```

**Fibonacci pivots:**
```
PP  = (H + L + C) / 3
rng = H − L
R1  = PP + 0.382×rng
R2  = PP + 0.618×rng
R3  = PP + 1.000×rng
S1  = PP − 0.382×rng
S2  = PP − 0.618×rng
S3  = PP − 1.000×rng
```

Both sets are computed for Daily, Weekly, Monthly. Result: **39 named levels** (`D_PP`, `D_R1`, `D_FR2`, `W_S1`, `M_FR3`, etc.). Fib PP is not duplicated (skipped when key == 'PP').

### ATR(14)

True range = max(H−L, |H−prev_C|, |L−prev_C|) per bar. Smoothed with EWM span=14.

### ADX(14)

Standard Wilder ADX using EWM alpha=1/14 for smoothing (not Wilder's RMA, but effectively the same). Returns a single float. Used only for regime classification — not as a filter.

### Swing high / low

```
swing_high = df['high'].iloc[-10:].max()
swing_low  = df['low'].iloc[-10:].min()
```

Lookback is 10 bars on the entry TF.

### Price action helpers

**Rejection at level** (`rejection_at_level`): checks the last 2 bars for evidence the pivot level was tested and held. Long: any bar had `low <= level` AND `close > level`. Short: any bar had `high >= level` AND `close < level`. Captures both pin bars and engulfing bars that touched the level.

**Bar close quality** (`bar_close_quality`): `(close - low) / (high - low)` on the last bar. Returns 0.0 (closed at low) to 1.0 (closed at high). 0.5 for doji/zero range.

**Engulfing** (`is_engulfing`): current bar's open-to-close body completely contains the prior bar's body in the opposite direction. Bullish: current bullish body covers prior bearish body (`c_o <= p_c` and `c_c >= p_o`). Bearish: mirror.

**Momentum consistency** (`momentum_consistency`): counts of the last 3 completed bars that closed in the trade direction (close > open for bullish, close < open for bearish). Returns an integer 0–3.

---

## 3. Signal Generation (`src/signals.py`)

### Entry before any loop

**Market context:** Computes `daily_atr` (ATR(14) on daily bars, needs ≥14 bars) and `daily_consumed_pct` (today's intraday high−low ÷ daily ATR, pulled from 1m → 5m → 15m bars in that priority order).

**Over-extended check:** If `daily_consumed_pct ≥ 1.10` → return empty list immediately. No signals fire.

**Active TFs:** If `ACCOUNT_BALANCE < 3500`, only `['1m', '5m', '15m', '1h']` are scanned. At $3,500+ the `4h` and `1d` TFs are added.

---

### Signal Path A: Pivot and Pullback (trending / neutral markets)

Runs for each active entry TF:

**Step 1 — HTF confirmation**

All confirmation TFs (from `CONFIRMATION_MAP`) must:
- Be present in the data
- All return the same non-neutral direction from `ema_alignment()`

If any confirm TF is missing, returns neutral, or they disagree → skip this entry TF.

| Entry TF | Confirmation TFs | ADX measured on |
|----------|-----------------|-----------------|
| 1m       | 5m, 15m         | 15m             |
| 5m       | 15m, 1H         | 1H              |
| 15m      | 1H, 4H          | 4H              |
| 1H       | 4H, Daily       | Daily           |
| 4H       | Daily           | Daily           |
| Daily    | (none)          | Daily           |

**Step 2 — Entry TF direction check**

Entry TF alignment must equal HTF direction OR be neutral. If entry TF is actively opposed to HTF direction → skip.

**Step 3 — ADX regime**

Computed on the highest confirmation TF.

| ADX value | Regime    | Effect |
|-----------|-----------|--------|
| ≥ 25      | trending  | T1 + T2 shown, R/R min = 2.0 |
| 18–25     | neutral   | T1 only, R/R min = 2.0 |
| < 18      | ranging   | (handled by Path B, not Path A) |

Note: a ranging ADX here doesn't block Path A — it just sets `regime = 'ranging'` which lowers the R/R bar to 1.5 and suppresses T2. Path B (the dedicated range scalp loop) runs separately.

**Step 4 — Pivot proximity**

`nearby = {level_name: level_price for all pivots where |price − pivot| ≤ 0.6 × ATR}`

If no levels are within that band → skip.

**Step 5 — Pivot signal check (`_check_setup`)**

1. **Volume gate:** recent 3-bar avg volume must be ≥ 50% of 20-bar avg. If not → `None`.
2. **Volume direction:** using last 5 completed bars — if bullish trade and up-volume is < 45% of total → `None`. If bearish and down-volume < 45% → `None`.
3. **Support/resistance at level:** for LONG, at least one nearby level must be at or below price (acting as support). For SHORT, at least one must be at or above price (resistance). If not → `None`.
4. **Near level selection:** picks the *nearest* qualifying level — highest support (for LONG) or lowest resistance (for SHORT). This is the level that gets labeled in the signal output.
5. **Rejection gate (price action):** the selected level must have been tested and held within the last 2 bars (`rejection_at_level`). If the level was never touched, the signal is rejected. This filters entries where price is only *approaching* a level vs. one that has been proven to hold.
6. **Stop:** `swing_low − 0.25` (LONG) or `swing_high + 0.25` (SHORT). Swing is 10-bar max/min on entry TF.
7. **Targets:** scan all 39 pivots for the nearest level beyond price (T1), then the next one after that (T2).
8. **T2 suppression:** T2 is removed if `regime == 'ranging'` OR `daily_consumed_pct ≥ 0.90`.
9. **R/R check:** `reward / risk`. Must be ≥ 2.0 (trending/neutral) or ≥ 1.5 (ranging). If not → `None`.
10. **Quality scoring:** assigns a tier (A/B/C) based on three price action checks — see Quality Tier section below.
11. **Dollar amounts:** `risk_pts × 5` and `reward_pts × 5` (MES = $5/point).

**Step 6 — Pullback signal check (`_check_pullback_setup`)**

Runs only when `smma_pullback_touch(entry_df)` returns the same direction as the HTF.

Same volume gate and volume direction check as pivot signal. Same stop and target logic. Key differences:
- No pivot proximity required for entry (entry is at SMMA21, not at a pivot)
- Adds `hold_condition` field: `"Hold while 5m closes above SMMA21 (X.XX) — exit on close below"`
- `near_level` is set to `'SMMA21'` instead of a pivot name

---

---

### Signal Quality Tier (`_signal_quality`)

Computed for every signal that passes all gates. Three components, each worth 1 point:

| Component | Bullish pass | Bearish pass |
|-----------|-------------|-------------|
| Bar close quality | close ≥ 65% of bar range | close ≤ 35% of bar range |
| Momentum consistency | ≥ 2 of last 3 completed bars closed bullish | ≥ 2 closed bearish |
| Engulfing (pivot/pullback) | current bar engulfs prior bearish body | current bar engulfs prior bullish body |
| Rejection wick (range scalp) | `rejection_at_level` passes | `rejection_at_level` passes |

**Tiers:** A = 3 pts, B = 2 pts, C = 0–1 pts.

For **pivot signals**: rejection gate already guarantees the level held, so the 3rd component is engulfing.
For **range scalp signals**: rejection_at_level used as 3rd component (not a gate here, only quality).
For **pullback signals**: engulfing used as 3rd component (bounce off SMMA21 is ideally an engulf).

Output in signal box:
```
  Quality:    B  (close 71%  |  mom 2/3  |  no engulf)
```
C-quality signals print in yellow as a visual caution flag.

---

### Signal Path B: Range Scalp (ranging markets only)

Runs as a separate loop over all active TFs after Path A completes.

**Condition to enter loop:** ADX on the highest confirm TF must be < 18. If ADX ≥ 18 → skip this TF entirely.

For each qualifying TF, the bot tries **both** directions (bullish and bearish).

**Direction logic:**
- **LONG:** needs at least one nearby pivot at or below price (support)
- **SHORT:** needs at least one nearby pivot at or above price (resistance)

**No HTF confirmation required.** The full SMMA stack won't be aligned in a ranging market — that's expected.

**SMMA micro-alignment** (smma3 vs smma8 only) → added to the `reason` string:
- Matches trade direction → `smma aligned`
- Neutral → `smma mixed`
- Opposed to trade direction → `smma against`

**Volume direction** → added to `reason` string. Not a gate.

**Stop / target / R/R:** same mechanics as pivot signal. R/R minimum = 1.5. T2 is always `None`.

**Dedup within loop:** each `(entry_tf, direction)` pair can only produce one range scalp signal per scan.

---

### Final sort

All signals from both paths are sorted by R/R descending before being returned.

---

## 4. Main Loop (`main.py`)

**Market hours gate:** `09:30 ≤ now ≤ 16:00`. Outside that window → sleep 5 minutes, check again.

**Scan cycle (every 30 seconds):**
1. Fetch all TF data from Schwab
2. Compute pivots from daily/weekly/monthly OHLC
3. Compute SMMA alignment for status display
4. Every 10 scans: print full status block (price, pivot levels, alignment)
5. Call `generate_signals()`
6. Run `_dedup_signals()` — drops any signal whose `(entry_tf, near_level, direction)` key fired within its cooldown window

**Cooldown windows:**

| TF  | Standard cooldown | Range scalp cooldown |
|-----|------------------|----------------------|
| 1m  | 5 min            | 2.5 min              |
| 5m  | 15 min           | 7.5 min              |
| 15m | 30 min           | 15 min               |
| 1H  | 60 min           | 30 min               |
| 4H  | 4 hr             | 2 hr                 |
| 1D  | 8 hr             | 4 hr                 |

7. If signals remain after dedup → record fire times, print signal boxes
8. If no signals → print `No signal` line with current alignment

---

## 5. Key Thresholds Summary

| Constant            | Value | Effect |
|--------------------|-------|--------|
| `PROXIMITY_ATR`    | 0.6   | Max distance to a pivot (× ATR) to qualify |
| `MIN_VOLUME_RATIO` | 0.5   | Recent vol must be ≥ 50% of 20-bar avg |
| `ADX_TRENDING`     | 25    | Above → T1+T2 shown |
| `ADX_RANGING`      | 18    | Below → range scalp path |
| `MIN_RR`           | 2.0   | Pivot + pullback signals |
| `MIN_RR_SCALP`     | 1.5   | Range scalp signals |
| `ATR_CONSUMED_LIMIT` | 0.90 | Suppress T2 |
| `ATR_OVEREXTENDED` | 1.10  | Block all signals |
| `VOLUME_DIRECTION_BARS` | 5 | Bars used for volume direction note |
| `SWING_UNLOCK_BALANCE` | 3500 | Account balance to enable 4H/Daily TFs |
| `SCAN_INTERVAL`    | 30s   | Loop frequency |
| `STATUS_EVERY`     | 10    | Scans between status prints |
