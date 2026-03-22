import pytz
import yfinance as yf
import pandas as pd
from datetime import datetime
from logger import logger

REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _normalize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    for col in REQUIRED_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    return df


def _validate(df: pd.DataFrame, symbol: str) -> bool:
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            logger.error(f"{symbol} -> missing '{col}' | have: {df.columns.tolist()}")
            return False
        if df[col].isna().all():
            logger.error(f"{symbol} -> '{col}' is all NaN")
            return False
    return True


def _check_stale(df: pd.DataFrame, symbol: str):
    try:
        tz  = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz)
        ts  = df.index[-1]
        if hasattr(ts, "tzinfo") and ts.tzinfo:
            ts = ts.astimezone(tz)
        else:
            ts = tz.localize(ts)
        age = (now - ts).total_seconds() / 60
        if age > 10:
            logger.warning(f"{symbol} -> last candle {age:.0f}min old — may be stale")
    except Exception:
        pass


def _extract_close_series(df: pd.DataFrame) -> pd.Series:
    """
    Safely extract Close as a clean 1-D float64 Series.
    Handles flat columns, MultiIndex columns, and 2-D array values.
    Fixes TypeError: 'NoneType' object is not subscriptable in yfinance 1.2.0
    """
    # Step 1: get the Close column regardless of MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        close_cols = [c for c in df.columns if str(c[0]).strip() == "Close"]
        series = df[close_cols[0]] if close_cols else df.iloc[:, 0]
    else:
        if "Close" in df.columns:
            series = df["Close"]
        else:
            close_cols = [c for c in df.columns if "Close" in str(c)]
            series = df[close_cols[0]] if close_cols else df.iloc[:, 0]

    # Step 2: flatten DataFrame to Series
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]

    # Step 3: squeeze + force numeric
    series = pd.to_numeric(series.squeeze(), errors="coerce")

    # Step 4: ensure proper 1-D Series
    if not isinstance(series, pd.Series):
        series = pd.Series(series.values.ravel(), index=df.index[:len(series)])

    return series.astype("float64")


def _fetch_raw(symbol: str, interval: str, period: str) -> pd.DataFrame | None:
    """Fetch raw OHLCV df. No aliases needed — TATAMOTORS removed from watchlist."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval=interval, period=period)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return None


def fetch_nifty_trend() -> str:
    """
    Returns 'BULL', 'BEAR', or 'NEUTRAL' based on NIFTY50 vs its 20-EMA.
    Robust against MultiIndex columns and 2-D array values.
    Always falls back to NEUTRAL on any error — never crashes the bot.
    """
    try:
        ticker = yf.Ticker("^NSEI")
        df = ticker.history(interval="5m", period="5d")

        if df is None or df.empty or len(df) < 20:
            logger.warning("NIFTY data unavailable — defaulting to NEUTRAL")
            return "NEUTRAL"

        close = _extract_close_series(df)

        if close.isna().all() or len(close) < 20:
            logger.warning("NIFTY Close invalid — defaulting to NEUTRAL")
            return "NEUTRAL"

        ema20  = close.ewm(span=20, adjust=False).mean()
        last_c = float(close.iloc[-1])
        last_e = float(ema20.iloc[-1])

        if last_c > last_e * 1.001:
            trend = "BULL"
        elif last_c < last_e * 0.999:
            trend = "BEAR"
        else:
            trend = "NEUTRAL"

        # Single clean log line — trading_engine must NOT log trend again
        logger.info(f"NIFTY trend: {trend} | price={last_c:.0f} | ema20={last_e:.0f}")
        return trend

    except Exception as e:
        logger.warning(
            f"NIFTY trend fetch failed ({e.__class__.__name__}: {e}) "
            f"— defaulting to NEUTRAL"
        )
        return "NEUTRAL"


def fetch_data(
    symbol: str,
    interval: str = "5m",
    period: str   = "5d",
) -> pd.DataFrame | None:
    try:
        df = _fetch_raw(symbol, interval, period)

        if df is None or df.empty:
            logger.warning(f"{symbol} -> empty data")
            return None

        existing = [c for c in REQUIRED_COLUMNS if c in df.columns]
        if not existing:
            logger.error(f"{symbol} -> no OHLCV cols. Got: {df.columns.tolist()}")
            return None

        df = df[existing].copy()
        df = _normalize_dtypes(df)

        # Drop rows where Close OR Volume is NaN
        # Volume NaN on last candle corrupts vol_ma calculation
        before = len(df)
        df.dropna(subset=["Close", "Volume"], inplace=True)
        if (dropped := before - len(df)):
            logger.warning(f"{symbol} -> dropped {dropped} NaN rows")

        if not _validate(df, symbol):
            return None
        if len(df) < 2:
            return None

        _check_stale(df, symbol)

        logger.info(
            f"{symbol} -> {len(df)} candles | "
            f"last close ₹{df['Close'].iloc[-1]:.2f}"
        )
        return df

    except Exception as e:
        logger.error(f"{symbol} -> fetch failed: {e}", exc_info=True)
        return None