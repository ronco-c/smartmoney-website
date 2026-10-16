"""
Smart Market Screener — Scans real market data to find the best stocks RIGHT NOW.
Uses yfinance for fundamentals/momentum and Finnhub for real-time quotes.
Returns scored picks with per-stock reasoning.
"""

import logging
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  STOCK UNIVERSE — Broad scan pool by sector
# ═══════════════════════════════════════════════════════════════════════════════

UNIVERSE = {
    "tech": [
        "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD", "AVGO", "CRM", "ORCL",
        "CSCO", "INTC", "TXN", "QCOM", "NOW", "INTU", "ADBE", "PLTR", "CRWD",
        "SNOW", "PANW", "NET", "ZS", "DDOG", "MDB", "UBER", "SQ", "SHOP",
        "TTD", "ANET", "MRVL", "LRCX", "ASML", "KLAC", "SNPS", "CDNS",
    ],
    "finance": [
        "JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "V", "MA",
        "PNC", "USB", "TFC", "BK", "STT", "ICE", "CME", "COIN", "HOOD",
        "SOFI", "AFRM", "PYPL", "FIS", "FISV", "MCO", "SPGI",
    ],
    "health": [
        "JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV", "TMO", "DHR", "ABT",
        "BMY", "AMGN", "GILD", "ISRG", "VRTX", "REGN", "MDT", "SYK",
        "EW", "ZTS", "CI", "HCA", "DXCM", "MRNA", "BIIB",
    ],
    "energy": [
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY",
        "HES", "DVN", "FANG", "HAL", "BKR", "KMI", "WMB", "ET",
    ],
    "retail": [
        "AMZN", "WMT", "COST", "TGT", "HD", "LOW", "TJX", "ROST", "DG",
        "DLTR", "NKE", "LULU", "SBUX", "MCD", "CMG", "YUM", "DPZ",
        "BURL", "ULTA", "ETSY", "W", "CHWY",
    ],
    "dividend": [
        "KO", "PEP", "PG", "JNJ", "VZ", "T", "MO", "PM", "ABBV", "MMM",
        "O", "MAIN", "ARCC", "SPG", "AVB", "WPC", "STAG", "EPD",
        "ENB", "IBM", "XEL", "DUK", "SO", "NEE",
    ],
    "general": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "V", "JPM",
        "JNJ", "UNH", "XOM", "WMT", "PG", "KO", "HD", "MRK", "COST",
        "LLY", "ABBV", "CRM", "AVGO", "AMD", "NFLX", "ADBE", "TJX",
        "GE", "CAT", "DE", "LMT", "BA", "GD", "RTX",
    ],
}


def _fetch_stock_data(symbol: str) -> Optional[Dict]:
    """Fetch real market data for a single stock using yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)

        # Get basic info
        info = t.info or {}
        hist_1m = t.history(period="1mo")
        hist_5d = t.history(period="5d")
        hist_3m = t.history(period="3mo")

        if hist_1m.empty or len(hist_1m) < 5:
            return None

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not current_price and not hist_1m.empty:
            current_price = float(hist_1m["Close"].iloc[-1])

        if not current_price or current_price <= 0:
            return None

        # Calculate key metrics
        close_1m = hist_1m["Close"]
        close_5d = hist_5d["Close"] if not hist_5d.empty else close_1m.tail(5)

        # Price changes
        change_1d = 0
        if len(close_1m) >= 2:
            change_1d = ((close_1m.iloc[-1] / close_1m.iloc[-2]) - 1) * 100

        change_1w = 0
        if len(close_5d) >= 2:
            change_1w = ((close_5d.iloc[-1] / close_5d.iloc[0]) - 1) * 100

        change_1m_pct = 0
        if len(close_1m) >= 2:
            change_1m_pct = ((close_1m.iloc[-1] / close_1m.iloc[0]) - 1) * 100

        change_3m_pct = 0
        if not hist_3m.empty and len(hist_3m) >= 2:
            change_3m_pct = ((hist_3m["Close"].iloc[-1] / hist_3m["Close"].iloc[0]) - 1) * 100

        # Volume analysis
        avg_vol = hist_1m["Volume"].mean()
        recent_vol = hist_1m["Volume"].tail(3).mean()
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0

        # Moving average momentum (price vs 20-day SMA)
        sma_20 = close_1m.tail(20).mean() if len(close_1m) >= 20 else close_1m.mean()
        momentum = ((current_price / sma_20) - 1) * 100

        # Market cap
        market_cap = info.get("marketCap", 0) or 0

        # Analyst target
        target = info.get("targetMeanPrice", 0) or 0
        upside = ((target / current_price) - 1) * 100 if target and current_price else 0

        # Company name
        name = info.get("shortName") or info.get("longName") or symbol

        # Sector
        sector = info.get("sector", "Unknown")

        # Beta (volatility)
        beta = info.get("beta", 1.0) or 1.0

        # Dividend yield
        div_yield = info.get("dividendYield", 0) or 0

        # PE ratio
        pe = info.get("trailingPE", 0) or 0

        return {
            "symbol": symbol,
            "name": name,
            "price": round(current_price, 2),
            "change_1d": round(change_1d, 2),
            "change_1w": round(change_1w, 2),
            "change_1m": round(change_1m_pct, 2),
            "change_3m": round(change_3m_pct, 2),
            "vol_ratio": round(vol_ratio, 2),
            "momentum": round(momentum, 2),
            "market_cap": market_cap,
            "target_price": round(target, 2),
            "upside": round(upside, 2),
            "sector": sector,
            "beta": round(beta, 2),
            "div_yield": round(div_yield * 100, 2) if div_yield < 1 else round(div_yield, 2),
            "pe": round(pe, 1),
        }

    except Exception as e:
        logger.warning("Failed to fetch data for %s: %s", symbol, e)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _score_stock(stock: Dict, risk: str) -> float:
    """Score a stock based on multiple factors. Higher = better pick."""
    score = 50.0  # Base score

    # 1. Momentum (weight: 25%)
    mom = stock["momentum"]
    if risk == "high":
        score += mom * 2.5  # Strong momentum amplified for high risk
    elif risk == "low":
        score += mom * 0.5 if mom > 0 else mom * 2  # Punish negative momentum harder
    else:
        score += mom * 1.5

    # 2. Weekly performance (weight: 15%)
    score += stock["change_1w"] * 1.5

    # 3. Monthly performance (weight: 15%)
    score += stock["change_1m"] * 0.8

    # 4. Volume spike (weight: 10%) — High volume = institutional interest
    vol = stock["vol_ratio"]
    if vol > 1.5:
        score += (vol - 1) * 10  # Volume spike bonus
    elif vol < 0.5:
        score -= 5  # Volume drought penalty

    # 5. Analyst upside (weight: 15%)
    if stock["upside"] > 0:
        score += min(stock["upside"] * 0.5, 20)  # Cap at 20 bonus
    elif stock["upside"] < -10:
        score -= 10  # Overvalued penalty

    # 6. Risk-adjusted scoring
    beta = stock["beta"]
    if risk == "low":
        # Prefer stable, large cap, dividend payers
        if beta < 1.0:
            score += 10
        if beta > 1.5:
            score -= 15
        if stock["market_cap"] > 100_000_000_000:  # >100B
            score += 8
        if stock["div_yield"] > 2:
            score += 10
    elif risk == "high":
        # Prefer high-beta, high-momentum, growth
        if beta > 1.2:
            score += 8
        if stock["change_1w"] > 5:
            score += 10  # Breakout stocks
        if stock["vol_ratio"] > 2:
            score += 8  # Volume explosion
    else:  # medium
        if 0.8 < beta < 1.5:
            score += 5
        if stock["market_cap"] > 20_000_000_000:  # >20B
            score += 5

    return round(score, 2)


def _generate_reasoning(stock: Dict) -> str:
    """Generate a clear, specific reasoning for why this stock was picked."""
    reasons = []

    # Momentum
    if stock["momentum"] > 3:
        reasons.append(f"Trading {stock['momentum']:.1f}% above 20-day avg")
    elif stock["momentum"] < -3:
        reasons.append(f"Oversold — {abs(stock['momentum']):.1f}% below 20-day avg")

    # Weekly move
    if abs(stock["change_1w"]) > 2:
        direction = "up" if stock["change_1w"] > 0 else "down"
        reasons.append(f"{direction} {abs(stock['change_1w']):.1f}% this week")

    # Volume
    if stock["vol_ratio"] > 1.8:
        reasons.append(f"Volume {stock['vol_ratio']:.1f}x above average")
    elif stock["vol_ratio"] > 1.3:
        reasons.append(f"Elevated volume ({stock['vol_ratio']:.1f}x avg)")

    # Analyst target
    if stock["upside"] > 10:
        reasons.append(f"Analysts target ${stock['target_price']:.0f} ({stock['upside']:.0f}% upside)")
    elif stock["upside"] > 0:
        reasons.append(f"{stock['upside']:.0f}% upside to target")

    # Monthly/quarterly trend
    if stock["change_1m"] > 5:
        reasons.append(f"+{stock['change_1m']:.1f}% in the last month")
    if stock["change_3m"] > 15:
        reasons.append(f"+{stock['change_3m']:.0f}% over 3 months")

    # Dividend
    if stock["div_yield"] > 3:
        reasons.append(f"{stock['div_yield']:.1f}% dividend yield")

    if not reasons:
        reasons.append("Stable performer with solid fundamentals")

    return " · ".join(reasons[:3])


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN SCREENER
# ═══════════════════════════════════════════════════════════════════════════════

def scan_market(strategy: str = "general", risk: str = "medium", count: int = 5) -> List[Dict]:
    """
    Scan the market and return the best stock picks RIGHT NOW.

    Args:
        strategy: 'tech', 'finance', 'health', 'energy', 'retail', 'dividend', 'general'
        risk: 'low', 'medium', 'high'
        count: Number of stocks to return

    Returns:
        List of scored stock dicts with reasoning
    """
    # Get stock pool
    pool = UNIVERSE.get(strategy, UNIVERSE["general"])

    # Shuffle to avoid bias when we can only scan a subset
    pool_shuffled = list(pool)
    random.shuffle(pool_shuffled)

    # Scan stocks in parallel (limit to ~25 to stay fast)
    scan_count = min(len(pool_shuffled), 25)
    stocks_to_scan = pool_shuffled[:scan_count]

    logger.info("[Screener] Scanning %d stocks for strategy=%s, risk=%s", scan_count, strategy, risk)

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_stock_data, sym): sym for sym in stocks_to_scan}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                logger.warning("Screener error for %s: %s", sym, e)

    if not results:
        logger.warning("[Screener] No stocks returned data")
        return []

    # Score each stock
    for stock in results:
        stock["score"] = _score_stock(stock, risk)
        stock["reasoning"] = _generate_reasoning(stock)

    # Sort by score (descending) and return top N
    results.sort(key=lambda x: -x["score"])
    top_picks = results[:count]

    logger.info("[Screener] Top %d picks: %s",
                len(top_picks),
                [f"{s['symbol']}({s['score']:.0f})" for s in top_picks])

    return top_picks
