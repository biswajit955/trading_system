import logging
import os
import pytz
from datetime import datetime

_current_log_date = None   # tracks which date the file handler is on


def _today_ist() -> str:
    return datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")


def _log_path(date_str: str) -> str:
    os.makedirs("logs", exist_ok=True)
    return os.path.join("logs", f"trading_{date_str}.log")


def _ensure_todays_file():
    """
    Checks if the date changed since last write.
    If yes — closes old FileHandler and opens a new one for today.
    Called every loop iteration in main.py so rotation happens
    within 60 seconds of midnight automatically.
    """
    global _current_log_date
    today    = _today_ist()
    log_inst = logging.getLogger("trading_system")

    if _current_log_date == today:
        return  # already on correct file — nothing to do

    # Date changed — swap the FileHandler
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    for handler in log_inst.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            log_inst.removeHandler(handler)

    new_path    = _log_path(today)
    new_handler = logging.FileHandler(new_path, encoding="utf-8")
    new_handler.setFormatter(formatter)
    log_inst.addHandler(new_handler)

    _current_log_date = today
    log_inst.info(f"Log file ready — writing to {new_path}")


def get_logger():
    global _current_log_date
    os.makedirs("logs", exist_ok=True)

    log_inst = logging.getLogger("trading_system")
    log_inst.setLevel(logging.INFO)

    if log_inst.handlers:
        _ensure_todays_file()
        return log_inst

    today     = _today_ist()
    log_path  = _log_path(today)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # Handler 1 — terminal
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    log_inst.addHandler(console)

    # Handler 2 — today's log file
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(formatter)
    log_inst.addHandler(fh)

    log_inst.propagate = False
    _current_log_date  = today

    for noisy in ("yfinance", "peewee", "urllib3", "curl_cffi"):
        logging.getLogger(noisy).setLevel(logging.CRITICAL)

    log_inst.info(f"Logger started — writing to {log_path}")
    return log_inst


logger = get_logger()


def rotate_daily():
    """
    Call at top of every main loop iteration.
    Automatically creates the next day's log file at midnight.
    """
    _ensure_todays_file()