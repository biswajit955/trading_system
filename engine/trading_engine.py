import config
from watchlist import WATCHLIST
from data.market_data import fetch_data, fetch_nifty_trend
from strategy.indicators import apply_indicators
from strategy.strategy_engine import generate_signal
from broker.paper_broker import PaperBroker
from risk.risk_manager import RiskManager
from logger import logger

COOLDOWN_CYCLES    = 2    # 10 min cooldown after a loss exit (was 6 = 30 min)
MAX_OPEN_POSITIONS = 4    # max simultaneous positions to focus capital


class TradingEngine:

    def __init__(self):
        self.broker          = PaperBroker()
        self.risk            = RiskManager()
        self.active          = True
        self.last_prices     = {}
        self.cooldown        = {}
        self._cycle_count    = 0

        # Opening Range Breakout tracking (per symbol)
        self._opening_ranges = {}     # {symbol: {"high": float, "low": float, "candles": int}}
        self._orb_locked     = set()  # symbols whose opening range is finalized

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
        self._opening_ranges = {}     # reset ORB data
        self._orb_locked     = set()
        self._allow_new_buys = True
        self._eod_exit_mode  = False
        logger.info("Engine reset for new trading day.")

    def _update_opening_range(self, symbol: str, high: float, low: float):
        """
        Track the first 3 candles (15 min) to build the Opening Range.
        Once 3 candles are collected, lock the range.
        """
        if symbol in self._orb_locked:
            return  # already finalized

        if symbol not in self._opening_ranges:
            self._opening_ranges[symbol] = {
                "high": high,
                "low": low,
                "candles": 1,
            }
        else:
            orb = self._opening_ranges[symbol]
            orb["high"] = max(orb["high"], high)
            orb["low"]  = min(orb["low"], low)
            orb["candles"] += 1

            if orb["candles"] >= 3:
                self._orb_locked.add(symbol)
                logger.info(
                    f"ORB locked: {symbol} | "
                    f"range=[₹{orb['low']:.2f} - ₹{orb['high']:.2f}]"
                )

    def _get_opening_range(self, symbol: str) -> dict | None:
        """Return the opening range dict if it's been finalized, else None."""
        if symbol in self._orb_locked:
            return self._opening_ranges.get(symbol)
        return None

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

        # Prefetch data for all watchlist tickers and NIFTY in bulk
        from data.market_data import prefetch_bulk_data
        tickers_to_fetch = list(WATCHLIST)
        if "^NSEI" not in tickers_to_fetch:
            tickers_to_fetch.append("^NSEI")
        prefetch_bulk_data(
            symbols=tickers_to_fetch,
            interval=config.TIMEFRAME,
            period=config.PERIOD,
        )

        # ── Market trend filter ───────────────────────────────────
        if self._allow_new_buys:
            market_trend = fetch_nifty_trend()
            allow_buy    = market_trend in ("BULL", "NEUTRAL")
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
                price  = round(float(df["Close"].iloc[-1]), 2)
                high   = round(float(df["High"].iloc[-1]), 2)
                low    = round(float(df["Low"].iloc[-1]), 2)

                self.last_prices[symbol] = price

                # ── Update Opening Range (first 3 candles) ────────
                self._update_opening_range(symbol, high, low)

                # Get ORB data for signal generation
                orb_data = self._get_opening_range(symbol)

                # Generate signal with VWAP + ORB
                signal = generate_signal(df, opening_range=orb_data)

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
                            f"vwap={df['vwap'].iloc[-1]:.2f} | "
                            f"rsi={df['rsi'].iloc[-1]:.1f} | "
                            f"supertrend={'UP' if df['supertrend_dir'].iloc[-1] > 0 else 'DOWN'}"
                        )
                        self.broker.sell(symbol, price, reason="SIGNAL")
                    else:
                        logger.info(
                            f"{symbol} -> SELL signal but no open position"
                        )
                    continue

                # ── BUY signal ────────────────────────────────────
                elif signal == "BUY":
                    logger.info(
                        f"{symbol} -> signal={signal} | price=₹{price} | "
                        f"vwap={df['vwap'].iloc[-1]:.2f} | "
                        f"rsi={df['rsi'].iloc[-1]:.1f} | "
                        f"supertrend={'UP' if df['supertrend_dir'].iloc[-1] > 0 else 'DOWN'}"
                    )
                    if not self._allow_new_buys:
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
                    # Check max open positions cap
                    if len(self.broker.positions) >= MAX_OPEN_POSITIONS:
                        logger.info(
                            f"{symbol} -> BUY blocked — "
                            f"max {MAX_OPEN_POSITIONS} open positions reached"
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
                        f"vwap={df['vwap'].iloc[-1]:.2f} | "
                        f"rsi={df['rsi'].iloc[-1]:.1f} | "
                        f"supertrend={'UP' if df['supertrend_dir'].iloc[-1] > 0 else 'DOWN'}"
                    )

            except Exception as e:
                logger.error(f"{symbol} error: {e}", exc_info=True)