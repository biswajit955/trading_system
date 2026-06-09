import config
from logger import logger

# ── Tunable constants ─────────────────────────────────────────────
CONFIRM_CANDLES     = 1    # EMA must hold cross for N candles before entry
VOLUME_SPIKE_FACTOR = 1.5  # Entry candle volume must be 1.5x average
RSI_FRESH_LOOKBACK  = 6    # RSI must have crossed BUY_MIN within last N candles
ADX_MIN             = 20   # Minimum ADX — skip trades on choppy/sideways days


def _ema_held_up(df, n: int) -> bool:
    for i in range(1, n + 1):
        if df.iloc[-i]["ema_fast"] <= df.iloc[-i]["ema_slow"]:
            return False
    return True


def _ema_held_down(df, n: int) -> bool:
    for i in range(1, n + 1):
        if df.iloc[-i]["ema_fast"] >= df.iloc[-i]["ema_slow"]:
            return False
    return True


def _rsi_just_crossed_up(df, threshold: float, lookback: int) -> bool:
    """
    True if RSI crossed ABOVE threshold within last `lookback` candles.
    lookback=6 (30 min) catches continuation moves on recovery days.
    """
    if df.iloc[-1]["rsi"] <= threshold:
        return False
    for i in range(2, lookback + 2):
        if len(df) < i + 1:
            break
        if df.iloc[-i]["rsi"] <= threshold:
            return True
    return False


def _volume_spike(df, factor: float) -> bool:
    last = df.iloc[-1]
    return last["Volume"] > (last["vol_ma"] * factor)


def generate_signal(df, nifty_open: float = None) -> str:
    """
    BUY  : EMA cross up + RSI fresh + not overbought + volume 1.5x + ADX>20
    SELL : EMA cross down + RSI < SELL_MAX
    Returns: 'BUY' | 'SELL' | 'HOLD'
    """
    if len(df) < CONFIRM_CANDLES + RSI_FRESH_LOOKBACK + 2:
        return "HOLD"

    last = df.iloc[-1]
    prev = df.iloc[-2]

    crossed_up   = (prev["ema_fast"] <= prev["ema_slow"]
                    and last["ema_fast"] >  last["ema_slow"])
    crossed_down = (prev["ema_fast"] >= prev["ema_slow"]
                    and last["ema_fast"] <  last["ema_slow"])

    ema_up_ok   = crossed_up   and _ema_held_up(df,   CONFIRM_CANDLES)
    ema_down_ok = crossed_down and _ema_held_down(df, CONFIRM_CANDLES)

    rsi_fresh  = _rsi_just_crossed_up(df, config.RSI_BUY_MIN, RSI_FRESH_LOOKBACK)
    rsi_not_ob = last["rsi"] < config.RSI_BUY_MAX
    vol_spike  = _volume_spike(df, VOLUME_SPIKE_FACTOR)
    adx_ok     = last.get("adx", 0) > ADX_MIN
    rsi_sell_ok = last["rsi"] < config.RSI_SELL_MAX

    buy_signal  = ema_up_ok and rsi_fresh and rsi_not_ob and vol_spike and adx_ok
    sell_signal = ema_down_ok and rsi_sell_ok

    if crossed_up and not buy_signal:
        reasons = []
        if not _ema_held_up(df, CONFIRM_CANDLES):
            reasons.append("EMA not confirmed")
        if not rsi_fresh:
            reasons.append(f"RSI={last['rsi']:.1f} stale (no fresh cross of {config.RSI_BUY_MIN} in {RSI_FRESH_LOOKBACK} candles)")
        if not rsi_not_ob:
            reasons.append(f"RSI={last['rsi']:.1f} overbought (cap={config.RSI_BUY_MAX})")
        if not vol_spike:
            reasons.append(f"Vol={last['Volume']:.0f} < {VOLUME_SPIKE_FACTOR}x vol_ma={last['vol_ma']*VOLUME_SPIKE_FACTOR:.0f}")
        if not adx_ok:
            reasons.append(f"ADX={last.get('adx',0):.1f} too weak (need >{ADX_MIN}) — choppy market")
        logger.debug(f"EMA crossed UP — BUY blocked: {' | '.join(reasons)}")

    if buy_signal:  return "BUY"
    if sell_signal: return "SELL"
    return "HOLD"