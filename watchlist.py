# ══════════════════════════════════════════════════════════════════
#  NSE ALGO TRADING WATCHLIST — 30 stocks
#  Ranked by: Liquidity + Volatility + Trend Quality + yfinance reliability
#  Strategy: EMA 9/21 crossover + RSI + Volume confirmation
#  Scan time estimate: ~36 seconds per cycle (within 5-min interval)
#  Last updated: March 2026
# ══════════════════════════════════════════════════════════════════

WATCHLIST = [

    # ── BANKING & FINANCE (8 stocks) ─────────────────────────────
    # Best sector for EMA crossovers — high volume, clear trends
    "BAJFINANCE.NS",    # #1  Score 9.20 — most volatile large-cap, sharpest crossovers
    "SBIN.NS",          # #4  Score 8.75 — highest PSU bank volume
    "ICICIBANK.NS",     # #6  Score 8.75 — strong consistent trends
    "HDFCBANK.NS",      # #8  Score 8.50 — largest private bank, ultra-liquid
    "INDUSINDBK.NS",    # #12 Score 8.40 — high beta, amplifies market moves
    "IDFCFIRSTB.NS",    # #13 Score 8.40 — NEW volatile midcap bank, great crossovers
    "AXISBANK.NS",      # #18 Score 8.20 — reliable trends
    "BANKBARODA.NS",    # #29 Score 7.90 — NEW high volume PSU bank

    # ── IT & TECHNOLOGY (5 stocks) ───────────────────────────────
    # Strong sector trends, high liquidity, RSI moves cleanly
    "INFY.NS",          # #5  Score 8.75 — clean EMA trends
    "TCS.NS",           # #7  Score 8.50 — most liquid IT stock
    "HCLTECH.NS",       # #9  Score 8.45 — NEW consistent trends, less choppy than TCS
    "TECHM.NS",         # #10 Score 8.40 — highest volatility in IT sector
    "WIPRO.NS",         # #17 Score 8.20 — NEW steady volume, good crossovers

    # ── METALS (5 stocks) ────────────────────────────────────────
    # Commodity-linked = strong momentum moves, algo favourite sector
    "TATASTEEL.NS",     # #2  Score 9.00 — highest metal volume, commodity-driven moves
    "VEDL.NS",          # #3  Score 8.95 — most volatile metal stock
    "JSWSTEEL.NS",      # #11 Score 8.40 — NEW strong trend follower
    "HINDALCO.NS",      # #14 Score 8.40 — NEW aluminium plays, good intraday swings
    "SAIL.NS",          # #20 Score 8.15 — NEW very high volume, cheap price = big qty

    # ── ENERGY (3 stocks) ────────────────────────────────────────
    "RELIANCE.NS",      # #16 Score 8.25 — mega-cap, consistent intraday movement
    "ONGC.NS",          # #25 Score 7.95 — NEW high volume, cheap = large position size
    "BPCL.NS",          # #27 Score 7.90 — NEW oil price sensitivity = volatility

    # ── INFRASTRUCTURE (3 stocks) ────────────────────────────────
    "ADANIPORTS.NS",    # #15 Score 8.40 — NEW high volume, strong trends
    "LT.NS",            # #22 Score 8.15 — large-cap infra, clean EMA trends
    "BHEL.NS",          # #28 Score 7.90 — NEW high volume infra, good momentum

    # ── PHARMA (2 stocks) ────────────────────────────────────────
    "SUNPHARMA.NS",     # #19 Score 8.15 — NEW largest pharma volume, strong trends
    "M&M.NS",           # #21 Score 8.15 — NEW auto + farm equipment, strong mover

    # ── TELECOM (1 stock) ────────────────────────────────────────
    "BHARTIARTL.NS",    # #23 Score 8.15 — NEW Airtel, strong uptrend, good volume

    # ── REAL ESTATE (1 stock) ────────────────────────────────────
    "DLF.NS",           # #24 Score 8.10 — NEW highest RE volume, volatile, trending

    # ── CONSUMER (1 stock) ───────────────────────────────────────
    "TITAN.NS",         # #30 Score 7.85 — NEW Tata brand, clean uptrends, good RSI moves

    # ── FMCG (1 stock) ───────────────────────────────────────────
    "ITC.NS",           # #38 Score 7.50 — defensive, steady signals, kept for balance

]

# ── REMOVED FROM PREVIOUS WATCHLIST ──────────────────────────────
# KOTAKBANK.NS  — ranked #41, replaced by higher-scoring stocks
# TATAMOTORS.NS — yfinance unreliable (404 errors), excluded

# ── SCAN TIME ESTIMATE ───────────────────────────────────────────
# 30 stocks × ~1.2s = ~36 seconds per 5-min cycle
# Stays well within 300s interval — safe to run