# ══════════════════════════════════════════════════════════════════
#  NSE ALGO TRADING WATCHLIST — 15 stocks (Scalping-optimized)
#  Ranked by: Intraday volatility + Liquidity + VWAP bounce quality
#  Strategy: VWAP Bounce + RSI Momentum + Supertrend filter
#  Scan time estimate: ~4 seconds per cycle (with bulk prefetch)
#  Last updated: June 2026
# ══════════════════════════════════════════════════════════════════

WATCHLIST = [

    # ── BANKING & FINANCE (5 stocks) ─────────────────────────────
    # Best sector for intraday scalping — massive volume, clear VWAP bounces
    "BAJFINANCE.NS",    # Highest intraday volatility, sharpest moves
    "SBIN.NS",          # Highest PSU bank volume, proven winner
    "ICICIBANK.NS",     # Consistent trends, proven winner in tradebook
    "HDFCBANK.NS",      # Ultra-liquid, tight spreads, excellent VWAP respect
    "AXISBANK.NS",      # Reliable momentum, proven in tradebook

    # ── METALS (3 stocks) ────────────────────────────────────────
    # Commodity-linked = strong momentum moves, great for scalping
    "TATASTEEL.NS",     # Highest metal volume, commodity-driven swings
    "VEDL.NS",          # Most volatile metal stock, strong intraday range
    "HINDALCO.NS",      # Proven winner, good intraday swings

    # ── IT (2 stocks) ────────────────────────────────────────────
    "INFY.NS",          # Clean trends, proven in tradebook
    "JSWSTEEL.NS",      # Strong trend follower, high momentum

    # ── ENERGY & INFRA (3 stocks) ────────────────────────────────
    "RELIANCE.NS",      # Mega-cap, consistent intraday movement
    "ADANIPORTS.NS",    # High volume, strong trends
    "M&M.NS",           # Strong mover, good intraday range

    # ── OTHERS (2 stocks) ────────────────────────────────────────
    "BHARTIARTL.NS",    # Good volume, strong uptrend, nice VWAP bounces
    "DLF.NS",           # Most volatile real estate, trending, great for scalping

]

# ── REMOVED (moved to bench — can restore if needed) ─────────────
# INDUSINDBK.NS   — too correlated with AXISBANK
# IDFCFIRSTB.NS   — low price = tiny absolute moves, bad for scalping
# BANKBARODA.NS   — slow mover, low volatility
# TCS.NS           — too stable, rarely gives intraday signals
# HCLTECH.NS       — low intraday range
# TECHM.NS         — choppy, false signals
# WIPRO.NS         — very low volatility
# SAIL.NS          — low price, small absolute ₹ moves
# ONGC.NS          — low volatility
# BPCL.NS          — low intraday range
# LT.NS            — slow mover for scalping
# BHEL.NS          — too choppy
# SUNPHARMA.NS     — slow mover
# TITAN.NS         — too expensive, low qty per trade
# ITC.NS           — defensive, barely moves intraday

# ── SCAN TIME ESTIMATE ───────────────────────────────────────────
# 15 stocks — bulk prefetched in ~3-4 seconds per cycle
# Well within the 300s (5-min) interval