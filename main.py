import time
import pytz
import config
from datetime import datetime
from engine.trading_engine import TradingEngine
from logger import logger


def get_ist_time() -> datetime:
    return datetime.now(pytz.timezone("Asia/Kolkata"))


def is_market_open() -> bool:
    now = get_ist_time()
    if now.weekday() >= 5:
        return False
    open_time  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_time <= now <= close_time


def is_no_new_trade_window() -> bool:
    """After 3:00 PM — stop all new BUY entries."""
    now = get_ist_time()
    cutoff = now.replace(hour=15, minute=0, second=0, microsecond=0)
    return now >= cutoff


def is_eod_exit_window() -> bool:
    """Between 3:00 PM and 3:30 PM — force-exit all open positions."""
    now = get_ist_time()
    start = now.replace(hour=15, minute=0,  second=0, microsecond=0)
    end   = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return start <= now <= end


def print_eod_summary(engine: TradingEngine):
    broker = engine.broker
    sep = "=" * 65

    logger.info(sep)
    logger.info("           END OF DAY SUMMARY — TRADING REPORT")
    logger.info(sep)

    if broker.trade_history:
        logger.info(
            f"  {'#':<4} {'Symbol':<15} {'Side':<5} "
            f"{'Entry':>8} {'Exit':>8} {'Qty':>5} {'PnL':>10} {'Reason'}"
        )
        logger.info("  " + "-" * 65)
        for i, t in enumerate(broker.trade_history, 1):
            result = "✓" if t["pnl"] > 0 else "✗"
            logger.info(
                f"  {i:<4} {t['symbol']:<15} {t['side']:<5} "
                f"{t['entry']:>8.2f} {t['exit']:>8.2f} "
                f"{t['qty']:>5} {t['pnl']:>+10.2f}  {result}  [{t.get('reason','')}]"
            )
    else:
        logger.info("  No trades executed today.")

    logger.info("  " + "-" * 65)

    total    = len(broker.trade_history)
    winning  = [t for t in broker.trade_history if t["pnl"] > 0]
    losing   = [t for t in broker.trade_history if t["pnl"] <= 0]
    g_profit = sum(t["pnl"] for t in winning)
    g_loss   = sum(t["pnl"] for t in losing)
    win_rate = (len(winning) / total * 100) if total else 0

    logger.info(f"  Total Trades   : {total}")
    logger.info(f"  Winning Trades : {len(winning)}")
    logger.info(f"  Losing Trades  : {len(losing)}")
    logger.info(f"  Win Rate       : {win_rate:.1f}%")
    logger.info(f"  Gross Profit   : ₹{g_profit:+.2f}")
    logger.info(f"  Gross Loss     : ₹{g_loss:+.2f}")
    logger.info(f"  Net PnL        : ₹{broker.pnl:+.2f}")
    logger.info(f"  Capital Start  : ₹{config.CAPITAL:,.2f}")
    logger.info(f"  Capital End    : ₹{config.CAPITAL + broker.pnl:,.2f}")
    logger.info(sep)


# ── Main Loop ─────────────────────────────────────────────────────
engine   = TradingEngine()
eod_done = False

logger.info("Bot started. Waiting for market open (9:15 AM IST)...")

while True:
    now = get_ist_time()

    if is_market_open():
        eod_done = False

        no_new_trades = is_no_new_trade_window()
        eod_exit      = is_eod_exit_window()

        if no_new_trades and not eod_exit:
            # Exactly 3:00 PM — log once
            pass

        # Pass the window flags into engine
        engine.set_session_flags(
            allow_new_buys = not no_new_trades,
            eod_exit_mode  = eod_exit,
        )

        if not engine.active and not eod_exit:
            logger.info("Daily limit reached. Waiting for market close...")
            time.sleep(60)
            continue

        engine.run()
        time.sleep(config.INTERVAL)

    else:
        # Market closed — print summary once, then reset
        if not eod_done:
            if engine.broker.positions:
                logger.info(
                    f"Market closed. Squaring off "
                    f"{len(engine.broker.positions)} remaining position(s)..."
                )
                engine.broker.square_off_all(engine.last_prices)

            print_eod_summary(engine)
            eod_done = True
            engine.reset_for_new_day()

        if now.hour < 9:
            logger.info("Pre-market. Sleeping 10 min...")
            time.sleep(600)
        else:
            time.sleep(60)