import csv
import os
from datetime import datetime


TRADEBOOK_FILE = "tradebook.csv"
HEADERS = ["datetime", "symbol", "side", "price", "qty", "value"]


def log_trade(symbol: str, side: str, price: float, qty: int = 0):
    """Append a trade record to tradebook.csv with timestamp."""

    file_exists = os.path.isfile(TRADEBOOK_FILE)

    with open(TRADEBOOK_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        # Write header only on first ever write
        if not file_exists:
            writer.writerow(HEADERS)

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            side,
            round(price, 2),
            qty,
            round(price * qty, 2),
        ])