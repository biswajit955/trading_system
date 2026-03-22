import config
from logger import logger

# All thresholds now live in config.py — change them there only.
# RSI_BUY_MIN, RSI_BUY_MAX, RSI_SELL_MAX, VOLUME_FACTOR

CONFIRM_CANDLES = 1  # EMA must hold crossover for 1 candle before entry


def _ema_confirmed(df, lookback: int) -> bool:
    """True if ema_fast > ema_slow for every one of the last `lookback` candles."""
    for i in range(1, lookback + 1):
        if df.iloc[-i]["ema_fast"] <= df.iloc[-i]["ema_slow"]:
            return False
    return True


def _ema_confirmed_down(df, lookback: int) -> bool:
    """True if ema_fast < ema_slow for every one of the last `lookback` candles."""
    for i in range(1, lookback + 1):
        if df.iloc[-i]["ema_fast"] >= df.iloc[-i]["ema_slow"]:
            return False
    return True


def generate_signal(df) -> str:
    """
    BUY  : EMA-9 crosses above EMA-21, holds for CONFIRM_CANDLES
           + RSI in band (config.RSI_BUY_MIN – config.RSI_BUY_MAX)
           + Volume > vol_ma × config.VOLUME_FACTOR

    SELL : EMA-9 crosses below EMA-21, holds for CONFIRM_CANDLES
           + RSI < config.RSI_SELL_MAX

    Returns: 'BUY' | 'SELL' | 'HOLD'
    """
    if len(df) < CONFIRM_CANDLES + 2:
        return "HOLD"

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # ── Crossover detection ───────────────────────────────────────
    crossed_up   = (prev["ema_fast"] <= prev["ema_slow"]
                    and last["ema_fast"] >  last["ema_slow"])
    crossed_down = (prev["ema_fast"] >= prev["ema_slow"]
                    and last["ema_fast"] <  last["ema_slow"])

    # ── Candle confirmation ───────────────────────────────────────
    ema_up_confirmed   = crossed_up   and _ema_confirmed(df,      CONFIRM_CANDLES)
    ema_down_confirmed = crossed_down and _ema_confirmed_down(df, CONFIRM_CANDLES)

    # ── Conditions (read from config — single source of truth) ───
    volume_ok   = last["Volume"] > (last["vol_ma"] * config.VOLUME_FACTOR)
    rsi_buy_ok  = config.RSI_BUY_MIN < last["rsi"] < config.RSI_BUY_MAX
    rsi_sell_ok = last["rsi"] < config.RSI_SELL_MAX

    buy_signal  = ema_up_confirmed   and rsi_buy_ok  and volume_ok
    sell_signal = ema_down_confirmed and rsi_sell_ok

    # ── Debug: log exactly why BUY was blocked on a crossover ─────
    if crossed_up and not buy_signal:
        reasons = []
        if not _ema_confirmed(df, CONFIRM_CANDLES):
            reasons.append(f"EMA not confirmed ({CONFIRM_CANDLES} candle)")
        if last["rsi"] <= config.RSI_BUY_MIN:
            reasons.append(
                f"RSI={last['rsi']:.1f} too low "
                f"(need >{config.RSI_BUY_MIN})"
            )
        if last["rsi"] >= config.RSI_BUY_MAX:
            reasons.append(
                f"RSI={last['rsi']:.1f} overbought "
                f"(need <{config.RSI_BUY_MAX})"
            )
        if not volume_ok:
            reasons.append(
                f"Vol={last['Volume']:.0f} < "
                f"vol_ma×{config.VOLUME_FACTOR}="
                f"{last['vol_ma'] * config.VOLUME_FACTOR:.0f}"
            )
        logger.debug(f"EMA crossed UP — BUY blocked: {' | '.join(reasons)}")

    if buy_signal:  return "BUY"
    if sell_signal: return "SELL"
    return "HOLD"