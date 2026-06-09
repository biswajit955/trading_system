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

def apply_indicators(df):
    """
    Accepts a DataFrame from fetch_data and returns a DataFrame with:
    - ema_fast, ema_slow, rsi, vol_ma
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

    # if we have too many NaNs after conversion, abort
    if close.isna().all():
        logger.error("apply_indicators -> close series is all NaN after conversion")
        return df

    # create new df copy so we don't accidentally modify incoming object
    out = df.copy()

    # Compute indicators (ta expects 1-D Series)
    out["ema_fast"] = ta.trend.EMAIndicator(close=close, window=9, fillna=False).ema_indicator()
    out["ema_slow"] = ta.trend.EMAIndicator(close=close, window=21, fillna=False).ema_indicator()
    out["rsi"] = ta.momentum.RSIIndicator(close=close, window=14, fillna=False).rsi()
    out["vol_ma"] = volume.rolling(20, min_periods=1).mean()
    
    # ADX: Measures trend strength (0-100)
    # Required by strategy to avoid false signals in choppy markets
    high = _to_1d_series(df.get("High"), index=idx)
    low = _to_1d_series(df.get("Low"), index=idx)
    out["adx"] = ta.trend.ADXIndicator(
        high=high,
        low=low,
        close=close,
        window=14,
        fillna=False
    ).adx()

    return out