import logging

# ── Trading system logger ─────────────────────────────────────────
logger = logging.getLogger("trading_system")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False

# ── Silence noisy third-party loggers ────────────────────────────
# yfinance prints its own 404/error messages directly — suppress them
for noisy in ("yfinance", "peewee", "urllib3", "curl_cffi"):
    logging.getLogger(noisy).setLevel(logging.CRITICAL)