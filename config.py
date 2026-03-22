# ═══════════════════════════════════════════════════════
# TRADING BOT CONFIG — updated for 30-stock watchlist
# ═══════════════════════════════════════════════════════

CAPITAL            = 100000
POSITION_SIZE      = 10000
MAX_TRADES_PER_DAY = 8       # increased from 5 → more stocks = more signals
INTERVAL           = 300     # 5 min between scans

TIMEFRAME = "5m"
PERIOD    = "5d"             # never hits the 75-candle cap

DAILY_PROFIT_TARGET = CAPITAL * 0.01   # ₹1000 = 1%
DAILY_MAX_LOSS      = 300              # stop if down ₹300

# ── Strategy thresholds ────────────────────────────────
# Relaxed for 30 stocks to generate more signals
RSI_BUY_MIN    = 52    # was 55 — catch momentum building
RSI_BUY_MAX    = 72    # was 70 — allow slightly strong entries
RSI_SELL_MAX   = 45
VOLUME_FACTOR  = 1.0   # was 1.5 — normal above-average volume


