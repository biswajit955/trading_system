import logging
import os
from datetime import datetime

def get_logger():
    # ── Create logs/ folder if it doesn't exist ───────────────────
    os.makedirs("logs", exist_ok=True)

    # ── Daily log filename: logs/trading_2026-03-26.log ───────────
    today     = datetime.now().strftime("%Y-%m-%d")
    log_file  = os.path.join("logs", f"trading_{today}.log")

    logger = logging.getLogger("trading_system")
    logger.setLevel(logging.INFO)

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # ── Handler 1: terminal (stdout) ──────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ── Handler 2: daily log file ─────────────────────────────────
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False

    # Silence noisy third-party loggers
    for noisy in ("yfinance", "peewee", "urllib3", "curl_cffi"):
        logging.getLogger(noisy).setLevel(logging.CRITICAL)

    logger.info(f"Logger started — writing to {log_file}")
    return logger


logger = get_logger()