import pandas as pd


def apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds all technical indicators needed by strategy_engine:
      ema_fast : EMA-9
      ema_slow : EMA-21
      rsi      : RSI-14
      vol_ma   : rolling 20-period volume average
      adx      : ADX-14  (trend strength — used to skip choppy days)
    """
    df = df.copy()

    # ── EMA 9 / 21 ────────────────────────────────────────────────
    df["ema_fast"] = df["Close"].ewm(span=9,  adjust=False).mean()
    df["ema_slow"] = df["Close"].ewm(span=21, adjust=False).mean()

    # ── RSI 14 ────────────────────────────────────────────────────
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=14, adjust=False).mean()
    avg_loss = loss.ewm(span=14, adjust=False).mean()
    rs        = avg_gain / avg_loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)

    # ── Volume MA 20 ──────────────────────────────────────────────
    df["vol_ma"] = df["Volume"].rolling(window=20, min_periods=1).mean()

    # ── ADX 14 ───────────────────────────────────────────────────
    # ADX measures trend STRENGTH (not direction).
    # ADX > 20  = trending market   → allow trades
    # ADX < 20  = choppy/sideways   → skip trades (reduces false signals)
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    plus_dm  = high.diff()
    minus_dm = low.diff().mul(-1)
    plus_dm  = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr       = tr.ewm(span=14, adjust=False).mean()
    plus_di   = 100 * plus_dm.ewm(span=14, adjust=False).mean() / atr
    minus_di  = 100 * minus_dm.ewm(span=14, adjust=False).mean() / atr
    dx_denom  = (plus_di + minus_di).replace(0, float("nan"))
    dx        = 100 * (plus_di - minus_di).abs() / dx_denom
    df["adx"] = dx.ewm(span=14, adjust=False).mean().fillna(0)

    return df