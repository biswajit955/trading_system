import logging
import os
import pytz
from datetime import datetime


def _get_trading_date() -> str:
    """
    Returns the trading date as YYYY-MM-DD.

    Rule: if current IST time is before 9:15 AM, the log belongs to
    TODAY (file will be created now, market opens soon).
    If the bot is running overnight or pre-market, it still uses
    today's date so the file is ready before 9:15 AM.

    The log file is always named for the day the market trades,
    not the exact minute the bot started.
    """
    tz  = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d")


def _rotate_file_handler(logger_instance):
    """
    Called at midnight / new day to swap the file handler to
    the new date's log file without restarting the bot.
    """
    tz      = pytz.timezone("Asia/Kolkata")
    today   = datetime.now(tz).strftime("%Y-%m-%d")
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    new_file = os.path.join(log_dir, f"trading_{today}.log")

    # Find and replace the existing FileHandler
    for handler in logger_instance.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            if handler.baseFilename.endswith(f"trading_{today}.log"):
                return  # already on today's file — nothing to do
            handler.close()
            logger_instance.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    new_handler = logging.FileHandler(new_file, encoding="utf-8")
    new_handler.setFormatter(formatter)
    logger_instance.addHandler(new_handler)
    logger_instance.info(f"Log rotated — now writing to {new_file}")


def get_logger():
    # ── Create logs/ folder ───────────────────────────────────────
    os.makedirs("logs", exist_ok=True)

    # ── Log file named for today's trading date ───────────────────
    today    = _get_trading_date()
    log_file = os.path.join("logs", f"trading_{today}.log")

    logger = logging.getLogger("trading_system")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on re-import
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # ── Handler 1: terminal ───────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ── Handler 2: daily log file (created immediately) ───────────
    # File is created NOW, even if market hasn't opened yet.
    # This means logs/trading_YYYY-MM-DD.log exists from the moment
    # the bot starts, ready to capture the 9:15 AM open.
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False

    # Silence noisy third-party loggers
    for noisy in ("yfinance", "peewee", "urllib3", "curl_cffi"):
        logging.getLogger(noisy).setLevel(logging.CRITICAL)

    logger.info(f"Logger started — writing to {log_file}")
    return logger


# ── Module-level logger instance ─────────────────────────────────
logger = get_logger()


def rotate_daily(logger_instance=None):
    """
    Call this once per day at midnight (or bot reset) to switch
    the log file to the new date. Called automatically from main.py
    inside reset_for_new_day().
    """
    if logger_instance is None:
        logger_instance = logging.getLogger("trading_system")
    _rotate_file_handler(logger_instance)