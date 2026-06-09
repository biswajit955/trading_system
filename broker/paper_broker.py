import config
from logger import logger
from storage.tradebook import log_trade

STOP_LOSS_PCT   = 0.003     # 0.3% — cut losers fast
TAKE_PROFIT_PCT = 0.005     # 0.5% — take small profits quickly
TRAIL_ACTIVATE  = 0.003     # trailing kicks in after +0.3% gain
TRAIL_DISTANCE  = 0.0015    # trail 0.15% below highest seen


class PaperBroker:

    def __init__(self):
        self.positions     = {}
        self.pnl           = 0.0
        self.trade_history = []

    def buy(self, symbol: str, price: float):
        qty = int(config.POSITION_SIZE // price)
        if qty == 0:
            logger.warning(
                f"BUY {symbol} skipped — price ₹{price} > "
                f"POSITION_SIZE ₹{config.POSITION_SIZE}"
            )
            return

        stop   = round(price * (1 - STOP_LOSS_PCT),   2)
        target = round(price * (1 + TAKE_PROFIT_PCT),  2)

        self.positions[symbol] = {
            "entry":    price,
            "qty":      qty,
            "stop":     stop,
            "target":   target,
            "highest":  price,
            "trailing": False,
            "eod_best": price,   # tracks best price seen in EOD window
        }
        log_trade(symbol, "BUY", price, qty)
        logger.info(
            f"BUY  {symbol} @ ₹{price:.2f} | qty={qty} | "
            f"invested=₹{price*qty:,.0f} | "
            f"stop=₹{stop} | target=₹{target}"
        )

    def sell(self, symbol: str, price: float, reason: str = "SIGNAL"):
        pos = self.positions.get(symbol)
        if pos is None:
            return

        trade_pnl = (price - pos["entry"]) * pos["qty"]
        self.pnl  += trade_pnl

        self.trade_history.append({
            "symbol": symbol,
            "side":   "SELL",
            "entry":  pos["entry"],
            "exit":   price,
            "qty":    pos["qty"],
            "pnl":    trade_pnl,
            "reason": reason,
        })

        log_trade(symbol, "SELL", price, pos["qty"])
        result = "PROFIT ✓" if trade_pnl >= 0 else "LOSS ✗"
        logger.info(
            f"SELL {symbol} @ ₹{price:.2f} | qty={pos['qty']} | "
            f"entry=₹{pos['entry']:.2f} | "
            f"PnL=₹{trade_pnl:+.2f} [{result}] [{reason}] | "
            f"Total=₹{self.pnl:+.2f}"
        )
        del self.positions[symbol]

    def check_stops(self, symbol: str, price: float):
        pos = self.positions.get(symbol)
        if pos is None:
            return

        # Update highest price for trailing
        if price > pos["highest"]:
            pos["highest"] = price

        gain_pct = (pos["highest"] - pos["entry"]) / pos["entry"]

        # Activate trailing stop
        if gain_pct >= TRAIL_ACTIVATE and not pos["trailing"]:
            pos["trailing"] = True
            logger.info(
                f"TRAILING STOP activated: {symbol} | "
                f"gain={gain_pct*100:.2f}% | highest=₹{pos['highest']}"
            )

        # Trailing stop exit
        if pos["trailing"]:
            trail_stop = round(pos["highest"] * (1 - TRAIL_DISTANCE), 2)
            if price <= trail_stop:
                logger.info(
                    f"TRAILING STOP hit: {symbol} @ ₹{price} "
                    f"(trail=₹{trail_stop}, peak=₹{pos['highest']})"
                )
                self.sell(symbol, price, reason="TRAIL-STOP")
                return

        # Hard stop-loss
        if price <= pos["stop"]:
            logger.warning(
                f"STOP-LOSS hit: {symbol} @ ₹{price} (stop=₹{pos['stop']})"
            )
            self.sell(symbol, price, reason="STOP-LOSS")
            return

        # Take-profit
        if price >= pos["target"]:
            logger.info(
                f"TAKE-PROFIT hit: {symbol} @ ₹{price} (target=₹{pos['target']})"
            )
            self.sell(symbol, price, reason="TAKE-PROFIT")

    def square_off_all(self, prices: dict):
        """Force-close everything at 15:30 — last resort."""
        for symbol in list(self.positions.keys()):
            price = prices.get(symbol, self.positions[symbol]["entry"])
            self.sell(symbol, price, reason="EOD-SQUAREOFF")