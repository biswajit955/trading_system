# strategy/indicators.py
import pandas as pd
import numpy as np
import ta
from logger import logger

def _to_1d_series(col, index=None):
    if isinstance(col, np.ndarray):
        arr = col.ravel()
        # use the provided index, not default 0,1,2...
        series = pd.Series(arr, index=index[:len(arr)] if index is not None else None)
    elif isinstance(col, pd.DataFrame) and col.shape[1] == 1:
        series = col.iloc[:, 0]
    else:
        try:
            series = pd.Series(col).squeeze()
        except Exception:
            series = pd.Series(col)

    if index is not None and not isinstance(col, (pd.Series, pd.DataFrame)):
        series.index = index[:len(series)]

    series = pd.to_numeric(series, errors="coerce")
    return series


def _compute_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Compute intraday VWAP that resets each trading day.
    VWAP = cumulative(TypicalPrice * Volume) / cumulative(Volume)
    Resets at the start of each new date in the index.
    """
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    tp_vol = typical_price * df["Volume"]

    # Detect day boundaries for reset
    if hasattr(df.index, 'date'):
        dates = pd.Series(df.index.date, index=df.index)
    else:
        dates = pd.Series(range(len(df)), index=df.index)

    day_changed = dates != dates.shift(1)
    day_changed.iloc[0] = True  # first row always starts a new day

    # Build day group IDs for cumulative grouping
    day_group = day_changed.cumsum()

    cum_tp_vol = tp_vol.groupby(day_group).cumsum()
    cum_vol = df["Volume"].groupby(day_group).cumsum()

    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    return vwap.astype("float64")


def _compute_supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
                        period: int = 10, multiplier: float = 2.0) -> pd.Series:
    """
    Compute Supertrend indicator.
    Returns a Series of 1 (UP/bullish) or -1 (DOWN/bearish).
    """
    atr = ta.volatility.AverageTrueRange(
        high=high, low=low, close=close, window=period, fillna=False
    ).average_true_range()

    hl2 = (high + low) / 2.0
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    n = len(close)
    supertrend = pd.Series(np.zeros(n), index=close.index, dtype="float64")
    direction = pd.Series(np.ones(n), index=close.index, dtype="float64")  # 1=UP, -1=DOWN

    final_upper = upper_band.copy()
    final_lower = lower_band.copy()

    for i in range(1, n):
        # Final upper band
        if upper_band.iloc[i] < final_upper.iloc[i - 1] or close.iloc[i - 1] > final_upper.iloc[i - 1]:
            final_upper.iloc[i] = upper_band.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        # Final lower band
        if lower_band.iloc[i] > final_lower.iloc[i - 1] or close.iloc[i - 1] < final_lower.iloc[i - 1]:
            final_lower.iloc[i] = lower_band.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        # Direction
        if direction.iloc[i - 1] == 1:  # was UP
            if close.iloc[i] < final_lower.iloc[i]:
                direction.iloc[i] = -1
                supertrend.iloc[i] = final_upper.iloc[i]
            else:
                direction.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]
        else:  # was DOWN
            if close.iloc[i] > final_upper.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = final_upper.iloc[i]

    return direction  # 1 = UP (bullish), -1 = DOWN (bearish)


def apply_indicators(df):
    """
    Accepts a DataFrame from fetch_data and returns a DataFrame with:
    - ema_fast, ema_slow, rsi, vol_ma (original)
    - vwap, supertrend_dir (new for scalping strategy)
    Defensive: handles 2D columns, NaNs, and preserves index.
    """

    if df is None or df.empty:
        logger.warning("apply_indicators called with empty df")
        return df

    # preserve original index
    idx = df.index

    # defensive conversion
    close = _to_1d_series(df.get("Close"), index=idx)
    volume = _to_1d_series(df.get("Volume"), index=idx)
    high = _to_1d_series(df.get("High"), index=idx)
    low = _to_1d_series(df.get("Low"), index=idx)

    # if we have too many NaNs after conversion, abort
    if close.isna().all():
        logger.error("apply_indicators -> close series is all NaN after conversion")
        return df

    # create new df copy so we don't accidentally modify incoming object
    out = df.copy()

    # ── Original indicators (kept for trend context) ──────────────
    out["ema_fast"] = ta.trend.EMAIndicator(close=close, window=9, fillna=False).ema_indicator()
    out["ema_slow"] = ta.trend.EMAIndicator(close=close, window=21, fillna=False).ema_indicator()
    out["rsi"] = ta.momentum.RSIIndicator(close=close, window=14, fillna=False).rsi()
    out["vol_ma"] = volume.rolling(20, min_periods=1).mean()

    # ── New scalping indicators ───────────────────────────────────
    # VWAP: Volume Weighted Average Price (resets daily)
    try:
        out["vwap"] = _compute_vwap(out)
    except Exception as e:
        logger.warning(f"VWAP calculation failed: {e} — filling with close")
        out["vwap"] = close

    # Supertrend: trend direction filter (1=UP, -1=DOWN)
    try:
        out["supertrend_dir"] = _compute_supertrend(
            high=high, low=low, close=close,
            period=10, multiplier=2.0,
        )
    except Exception as e:
        logger.warning(f"Supertrend calculation failed: {e} — defaulting to UP")
        out["supertrend_dir"] = 1.0

    return out