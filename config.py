# ═══════════════════════════════════════════════════════
# TRADING BOT CONFIG — VWAP Scalping Strategy
# ═══════════════════════════════════════════════════════

CAPITAL            = 1000031
POSITION_SIZE      = 8000               # ₹8k per trade — more ₹ from small % moves
MAX_TRADES_PER_DAY = 20                 # scalping needs more trade capacity
INTERVAL           = 300                # 5 min between scans

TIMEFRAME = "5m"
PERIOD    = "5d"                        # never hits the 75-candle cap

DAILY_PROFIT_TARGET = 500               # ₹500/day — realistic for scalping
DAILY_MAX_LOSS      = 400               # stop if down ₹400

# ── Strategy thresholds ────────────────────────────────
RSI_BUY_MIN    = 40          # catch VWAP bounces earlier
RSI_BUY_MAX    = 68          # avoid buying overbought
RSI_SELL_MAX   = 45          # sell when momentum fades