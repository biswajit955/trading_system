import config
from watchlist import WATCHLIST
from data.market_data import fetch_data, fetch_nifty_trend
from strategy.indicators import apply_indicators
from strategy.strategy_engine import generate_signal
from broker.paper_broker import PaperBroker
from risk.risk_manager import RiskManager
from logger import logger

COOLDOWN_CYCLES = 6   # 30 min cooldown after a loss exit


class TradingEngine:

    def __init__(self):
        self.broker          = PaperBroker()
        self.risk            = RiskManager()
        self.active          = True
        self.last_prices     = {}
        self.cooldown        = {}
        self._cycle_count    = 0
        self._nifty_open     = None   # NIFTY price at 9:15 AM, set on first cycle

        # Session flags set by main.py each cycle
        self._allow_new_buys = True
        self._eod_exit_mode  = False

    def set_session_flags(self, allow_new_buys: bool, eod_exit_mode: bool):
        """Called by main.py every cycle to pass time-based rules."""
        prev_buy  = self._allow_new_buys
        prev_exit = self._eod_exit_mode

        self._allow_new_buys = allow_new_buys
        self._eod_exit_mode  = eod_exit_mode

        # Log transitions once
        if prev_buy and not allow_new_buys:
            logger.info(
                "── 3:00 PM ── No new BUY entries. "
                "Monitoring open positions for best exit..."
            )
        if not prev_exit and eod_exit_mode and self.broker.positions:
            logger.info(
                f"── EOD exit window open ── "
                f"{len(self.broker.positions)} position(s) will be sold "
                f"at best price before 3:30 PM"
            )

    def reset_for_new_day(self):
        self.broker          = PaperBroker()
        self.risk            = RiskManager()
        self.active          = True
        self.last_prices     = {}
        self.cooldown        = {}
        self._cycle_count    = 0
        self._nifty_open     = None   # reset for new day
        self._allow_new_buys = True
        self._eod_exit_mode  = False
        logger.info("Engine reset for new trading day.")

    def _eod_smart_exit(self, symbol: str, price: float):
        """
        EOD exit logic (3:00–3:30 PM):
        Sell immediately if price is ABOVE entry (lock profit).
        Otherwise hold until the best price seen in the window,
        or force-exit at 3:25 PM to avoid last-minute slippage.
        """
        from datetime import datetime
        import pytz

        pos = self.broker.positions.get(symbol)
        if pos is None:
            return

        now = datetime.now(pytz.timezone("Asia/Kolkata"))
        force_exit_time = now.replace(hour=15, minute=25, second=0, microsecond=0)

        # Track highest price seen during EOD window
        if "eod_high" not in pos:
            pos["eod_high"] = price
        else:
            pos["eod_high"] = max(pos["eod_high"], price)

        entry      = pos["entry"]
        eod_high   = pos["eod_high"]
        unrealized = (price - entry) * pos["qty"]

        # Rule 1: If in profit — sell immediately, lock it in
        if price > entry:
            logger.info(
                f"EOD smart exit: {symbol} @ ₹{price} | "
                f"Above entry ₹{entry} | unrealized=₹{unrealized:+.2f} — LOCKING PROFIT"
            )
            self.broker.sell(symbol, price, reason="EOD-PROFIT-LOCK")

        # Rule 2: Force exit at 3:25 PM regardless — no exceptions
        elif now >= force_exit_time:
            logger.info(
                f"EOD force exit: {symbol} @ ₹{price} | "
                f"3:25 PM deadline hit | PnL=₹{unrealized:+.2f}"
            )
            self.broker.sell(symbol, price, reason="EOD-FORCE-3:25PM")

        # Rule 3: Still in loss window — wait for recovery, log best seen
        else:
            mins_left = (force_exit_time - now).seconds // 60
            logger.info(
                f"EOD holding: {symbol} @ ₹{price} | "
                f"entry=₹{entry} | best_seen=₹{eod_high} | "
                f"unrealized=₹{unrealized:+.2f} | "
                f"{mins_left}min until force exit"
            )

    def run(self):
        self._cycle_count += 1

        # ── Daily PnL limits (skip in EOD exit mode) ──────────────
        if not self._eod_exit_mode:
            if self.broker.pnl >= config.DAILY_PROFIT_TARGET:
                logger.info(f"Daily profit target ₹{config.DAILY_PROFIT_TARGET} reached.")
                self.active = False
                return
            if self.broker.pnl <= -config.DAILY_MAX_LOSS:
                logger.info(f"Daily max loss ₹{config.DAILY_MAX_LOSS} hit.")
                self.active = False
                return

        # ── Market trend filter ───────────────────────────────────
        if self._allow_new_buys:
            market_trend = fetch_nifty_trend()
            allow_buy    = market_trend in ("BULL", "NEUTRAL")

            # Capture NIFTY open price on first cycle of the day
            if self._nifty_open is None:
                try:
                    from data.market_data import fetch_data as _fd
                    _ndf = _fd("^NSEI", interval="5m", period="1d")
                    if _ndf is not None and len(_ndf) > 0:
                        self._nifty_open = float(_ndf["Close"].iloc[0])
                        logger.info(f"NIFTY day open captured: {self._nifty_open:.0f}")
                except Exception:
                    pass
        else:
            market_trend = "N/A"
            allow_buy    = False   # 3PM+ — no new buys regardless

        # ── Decrement cooldowns ───────────────────────────────────
        for sym in list(self.cooldown.keys()):
            self.cooldown[sym] -= 1
            if self.cooldown[sym] <= 0:
                del self.cooldown[sym]
                logger.info(f"{sym} -> cooldown expired")

        # ── Scan all symbols ──────────────────────────────────────
        for symbol in WATCHLIST:
            try:
                df = fetch_data(
                    symbol,
                    interval=config.TIMEFRAME,
                    period=config.PERIOD,
                )
                if df is None or len(df) < 25:
                    continue

                df     = apply_indicators(df)
                signal = generate_signal(df, nifty_open=self._nifty_open)
                price  = round(float(df["Close"].iloc[-1]), 2)

                self.last_prices[symbol] = price

                # ── EOD exit mode: smart sell open positions ───────
                if self._eod_exit_mode:
                    if symbol in self.broker.positions:
                        self._eod_smart_exit(symbol, price)
                    # No new signals in EOD mode
                    continue

                # ── Normal mode: stop-loss / take-profit / trailing ─
                if symbol in self.broker.positions:
                    prev_pos = set(self.broker.positions.keys())
                    self.broker.check_stops(symbol, price)
                    if symbol not in self.broker.positions and symbol in prev_pos:
                        last_trade = self.broker.trade_history[-1]
                        if last_trade["pnl"] < 0:
                            self.cooldown[symbol] = COOLDOWN_CYCLES
                            logger.info(
                                f"{symbol} -> loss exit, "
                                f"cooldown {COOLDOWN_CYCLES} cycles"
                            )
                        continue

                # ── SELL signal ───────────────────────────────────
                # Only process SELL if we have an open position
                if signal == "SELL":
                    if symbol in self.broker.positions:
                        logger.info(
                            f"{symbol} -> signal={signal} | price=₹{price} | "
                            f"ema_fast={df['ema_fast'].iloc[-1]:.2f} | "
                            f"ema_slow={df['ema_slow'].iloc[-1]:.2f} | "
                            f"rsi={df['rsi'].iloc[-1]:.1f}"
                        )
                        self.broker.sell(symbol, price, reason="SIGNAL")
                    # Skip logging if no position (not wasting logs for non-owned stocks)
                    continue

                # ── BUY signal ────────────────────────────────────
                elif signal == "BUY":
                    logger.info(
                        f"{symbol} -> signal={signal} | price=₹{price} | "
                        f"ema_fast={df['ema_fast'].iloc[-1]:.2f} | "
                        f"ema_slow={df['ema_slow'].iloc[-1]:.2f} | "
                        f"rsi={df['rsi'].iloc[-1]:.1f}"
                    )
                    if not self._allow_new_buys:
                        # Should not reach here but safety guard
                        logger.info(f"{symbol} -> BUY blocked (after 3PM)")
                        continue
                    if not allow_buy:
                        logger.info(
                            f"{symbol} -> BUY blocked by NIFTY trend ({market_trend})"
                        )
                        continue
                    if symbol in self.cooldown:
                        logger.info(
                            f"{symbol} -> BUY blocked, cooldown "
                            f"{self.cooldown[symbol]} cycles left"
                        )
                        continue
                    if symbol not in self.broker.positions:
                        if self.risk.allow_trade():
                            self.broker.buy(symbol, price)
                        else:
                            logger.info(
                                f"{symbol} -> BUY blocked — "
                                f"daily limit {config.MAX_TRADES_PER_DAY} reached"
                            )
                    else:
                        logger.info(
                            f"{symbol} -> BUY signal but already in position"
                        )

                # ── HOLD signal ──────────────────────────────────
                else:
                    logger.info(
                        f"{symbol} -> signal={signal} | price=₹{price} | "
                        f"ema_fast={df['ema_fast'].iloc[-1]:.2f} | "
                        f"ema_slow={df['ema_slow'].iloc[-1]:.2f} | "
                        f"rsi={df['rsi'].iloc[-1]:.1f}"
                    )

            except Exception as e:
                logger.error(f"{symbol} error: {e}", exc_info=True)