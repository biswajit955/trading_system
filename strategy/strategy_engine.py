import config
from logger import logger

# ── Tunable constants ─────────────────────────────────────────────
# VWAP Bounce parameters
VWAP_PROXIMITY_PCT  = 0.003   # Price within 0.3% of VWAP counts as "near VWAP"
RSI_BUY_LOW         = 40      # RSI power zone lower bound
RSI_BUY_HIGH        = 68      # RSI power zone upper bound (avoid overbought)
VOLUME_SPIKE_FACTOR = 1.0     # Normal above-average volume is fine for scalping

# Opening Range Breakout parameters
ORB_CANDLES         = 3       # First 3 candles (15 min) define the opening range
ORB_BREAKOUT_BUFFER = 0.001   # 0.1% buffer above/below range for breakout confirmation


def generate_signal(df, opening_range: dict = None) -> str:
    """
    Dual-mode scalping signal generator.

    Mode A — VWAP Bounce (primary, runs all day):
      BUY:  Price bounced off VWAP from near/below → now above VWAP
            + RSI in power zone (40-68)
            + Price > EMA-21 (trend up)
            + Supertrend = UP
            + Volume >= average
      SELL: Price dropped below VWAP + RSI < 45
            OR Supertrend flipped to DOWN

    Mode B — Opening Range Breakout (first hour only):
      BUY:  Price breaks above Opening Range High
            + Volume spike + Supertrend UP
      (Handled via opening_range dict passed from engine)

    Returns: 'BUY' | 'SELL' | 'HOLD'
    """
    if len(df) < 25:
        return "HOLD"

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price     = last["Close"]
    rsi       = last.get("rsi", 50)
    vwap      = last.get("vwap", price)
    ema_slow  = last.get("ema_slow", price)
    ema_fast  = last.get("ema_fast", price)
    st_dir    = last.get("supertrend_dir", 1)
    volume    = last.get("Volume", 0)
    vol_ma    = last.get("vol_ma", 1)


    prev_price = prev["Close"]
    prev_vwap  = prev.get("vwap", prev_price)

    # ── Derived conditions ────────────────────────────────────────
    # VWAP bounce: was near/below VWAP, now above it
    was_near_or_below_vwap = prev_price <= prev_vwap * (1 + VWAP_PROXIMITY_PCT)
    now_above_vwap         = price > vwap

    # RSI in the "power zone" — not too cold, not too hot
    rsi_in_zone  = RSI_BUY_LOW <= rsi <= RSI_BUY_HIGH
    rsi_sell_ok  = rsi < config.RSI_SELL_MAX

    # Trend filters
    trend_up     = price > ema_slow         # price above slow EMA = uptrend
    supertrend_up = st_dir > 0              # Supertrend says bullish
    supertrend_down = st_dir < 0            # Supertrend says bearish

    # Volume check — just above average is fine for scalping
    vol_ok = volume >= (vol_ma * VOLUME_SPIKE_FACTOR) if vol_ma > 0 else True

    # Price dropped below VWAP
    below_vwap = price < vwap

    # ── Mode A: VWAP Bounce Signal ────────────────────────────────
    vwap_buy = (
        was_near_or_below_vwap
        and now_above_vwap
        and rsi_in_zone
        and trend_up
        and supertrend_up
        and vol_ok
    )

    vwap_sell = (
        (below_vwap and rsi_sell_ok)
        or supertrend_down
    )

    # ── Mode B: Opening Range Breakout ────────────────────────────
    orb_buy = False
    if opening_range is not None:
        orb_high = opening_range.get("high")
        orb_low  = opening_range.get("low")
        if orb_high is not None and orb_low is not None:
            breakout_level = orb_high * (1 + ORB_BREAKOUT_BUFFER)
            if price > breakout_level and supertrend_up and vol_ok and rsi < RSI_BUY_HIGH:
                orb_buy = True
                logger.info(
                    f"ORB breakout detected | price=₹{price:.2f} > "
                    f"range_high=₹{orb_high:.2f} | RSI={rsi:.1f}"
                )

    # ── Decision ──────────────────────────────────────────────────
    buy_signal  = vwap_buy or orb_buy
    sell_signal = vwap_sell and not buy_signal  # sell only if not also buying

    # Debug logging for rejected VWAP bounces
    if was_near_or_below_vwap and now_above_vwap and not vwap_buy:
        reasons = []
        if not rsi_in_zone:
            reasons.append(f"RSI={rsi:.1f} outside [{RSI_BUY_LOW}-{RSI_BUY_HIGH}]")
        if not trend_up:
            reasons.append(f"price={price:.2f} < EMA21={ema_slow:.2f}")
        if not supertrend_up:
            reasons.append("Supertrend=DOWN")
        if not vol_ok:
            reasons.append(f"Vol={volume:.0f} < avg={vol_ma:.0f}")
        logger.debug(f"VWAP bounce rejected: {' | '.join(reasons)}")

    if buy_signal:
        return "BUY"
    if sell_signal:
        return "SELL"
    return "HOLD"