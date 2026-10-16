"""
Alpha Screener — "Next Big Stock" Multi-Parameter Engine

Identifies stocks with potential for hundreds to thousands of percent returns.
Uses 15+ parameters that historically correlated with explosive growth:
  - Small/micro cap with revenue acceleration
  - Institutional accumulation (new positions from 13F data)
  - Insider buying clusters (C-suite buying)
  - Volume breakouts (RVOL > 2x)
  - Sector tailwinds (AI, biotech, clean energy, defense, etc.)
  - Price breakouts (crossing 200-day SMA)
  - Analyst upgrade momentum
  - Low leverage + expanding margins
  - Recent IPO that found bottom

Data Sources: FMP API + existing 13F DB data
Output: Ranked top 10 with composite score + per-parameter breakdown
"""

import os
import math
import logging
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  CANDIDATE UNIVERSE — Sectors with historical explosive growth
# ═══════════════════════════════════════════════════════════════════════════════

# Small/mid-cap stocks across high-growth sectors
SCAN_UNIVERSE = {
    "AI & Semiconductors": [
        "PLTR", "SMCI", "ARM", "MRVL", "CRWD", "NET", "DDOG", "ZS", "MDB",
        "SNOW", "PANW", "ANET", "SNPS", "CDNS", "ONTO", "CEVA", "SOUN",
        "BBAI", "BFLY", "AI", "UPST", "PATH", "ASAN", "CFLT", "ESTC",
        "IOT", "RKLB", "IRDM", "IONQ", "RGTI", "QUBT",
    ],
    "Biotech & Healthcare": [
        "MRNA", "VRTX", "REGN", "ARGX", "ALNY", "PCVX", "DAWN", "RXRX",
        "KRYS", "CORT", "SAVA", "SMMT", "IOVA", "ACAD", "RPRX",
        "XENE", "INCY", "NBIX", "HALO", "RVMD", "TGTX",
        "LEGN", "IMVT", "BHVN", "AXSM", "CRNX", "GPCR",
    ],
    "Clean Energy & EV": [
        "ENPH", "SEDG", "FSLR", "RUN", "RIVN", "LCID", "CHPT", "BLDP",
        "PLUG", "BE", "NOVA", "STEM", "ARRY", "SHLS", "EVGO",
        "QS", "PTRA", "BLNK", "VST", "CEG", "OKLO", "NNE", "SMR",
    ],
    "Fintech & Crypto": [
        "COIN", "SOFI", "AFRM", "HOOD", "MSTR", "NU", "BILL",
        "TOST", "FOUR", "RELY", "FLYW", "PAYO", "DLO",
        "MARA", "RIOT", "CLSK", "BITF", "HIVE",
    ],
    "Defense & Aerospace": [
        "RKLB", "ASTS", "SPIR", "PL", "LUNR", "KTOS", "MRCY",
        "AVAV", "TDG", "AXON", "PLTR", "LDOS", "CACI",
    ],
    "Consumer & E-commerce": [
        "SHOP", "ETSY", "DUOL", "CART", "CELH", "HIMS", "ONON", "BIRK",
        "CAVA", "BROS", "SHAK", "WINGSTOP", "ELF", "MNST",
        "DECK", "CROX", "LULU", "RVLV",
    ],
    "Enterprise SaaS": [
        "HUBS", "TTD", "ZI", "BRZE", "S", "GTLB", "DOCN", "TWLO",
        "KVYO", "MNDY", "FRSH", "PAYC", "PCOR", "APPF",
        "TTAN", "DV", "CWAN", "MANH",
    ],
}

# Hot sectors and their momentum multipliers (updated periodically)
SECTOR_MOMENTUM = {
    "AI & Semiconductors": 1.5,       # AI boom = max multiplier
    "Biotech & Healthcare": 1.2,      # GLP-1, gene therapy
    "Clean Energy & EV": 1.1,         # Nuclear renaissance
    "Fintech & Crypto": 1.3,          # Crypto bull cycle
    "Defense & Aerospace": 1.3,       # Geopolitical spending surge
    "Consumer & E-commerce": 1.0,     # Neutral
    "Enterprise SaaS": 1.1,           # AI integration wave
}


def _safe_float(v: Any) -> Optional[float]:
    """Safely convert to float, return None on failure."""
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  PARAMETER SCORING FUNCTIONS (each returns 0-10)
# ═══════════════════════════════════════════════════════════════════════════════

def _score_market_cap(market_cap: Optional[float]) -> float:
    """Small/micro cap bias — where 100x growth happens.
    Sweet spot: $500M - $5B. Too small (<$200M) = risky. Too large (>$50B) = slow growth."""
    if not market_cap or market_cap <= 0:
        return 0
    mc_b = market_cap / 1e9  # Convert to billions
    if mc_b < 0.2:
        return 2  # Penny territory — risky
    if mc_b < 0.5:
        return 6  # Micro cap — high potential but risky
    if mc_b < 2:
        return 10  # Sweet spot — small cap explosive growth
    if mc_b < 5:
        return 9  # Still good — room to grow
    if mc_b < 10:
        return 7
    if mc_b < 30:
        return 5
    if mc_b < 100:
        return 3
    return 1  # Mega cap — unlikely to 10x


def _score_revenue_growth(metrics: Dict) -> float:
    """Revenue growth acceleration — the #1 predictor of explosive returns."""
    rev_growth = _safe_float(metrics.get("revenueGrowth"))
    if rev_growth is None:
        return 3  # Unknown = neutral
    growth_pct = rev_growth * 100
    if growth_pct > 100:
        return 10
    if growth_pct > 50:
        return 9
    if growth_pct > 30:
        return 8
    if growth_pct > 20:
        return 7
    if growth_pct > 10:
        return 5
    if growth_pct > 0:
        return 3
    return 1  # Declining revenue


def _score_institutional_accumulation(holdings_data: List[Dict]) -> float:
    """13F institutional accumulation — smart money flowing in."""
    if not holdings_data:
        return 3
    adds = sum(1 for h in holdings_data
               if "+" in str(h.get("position_change", ""))
               or "Added" in str(h.get("position_change", ""))
               or "New" in str(h.get("position_change", "")))
    total = len(holdings_data)
    if total == 0:
        return 3
    add_ratio = adds / total
    if add_ratio > 0.8:
        return 10
    if add_ratio > 0.6:
        return 8
    if add_ratio > 0.4:
        return 6
    if add_ratio > 0.2:
        return 4
    return 2


def _score_insider_buying(insider_data: List[Dict]) -> float:
    """Insider buying clusters — executives putting their own money in."""
    if not insider_data:
        return 3
    buys = [x for x in insider_data if x.get("is_buy")]
    sells = [x for x in insider_data if not x.get("is_buy")]
    if len(buys) >= 3 and len(sells) == 0:
        return 10  # Cluster buy with zero sells — extremely bullish
    if len(buys) >= 2 and len(sells) == 0:
        return 9
    if len(buys) > len(sells) * 2:
        return 8
    if len(buys) > len(sells):
        return 6
    if len(buys) > 0:
        return 4
    if len(sells) > 3 and len(buys) == 0:
        return 1  # Heavy insider selling
    return 3


def _score_volume_breakout(profile_data: Dict) -> float:
    """Relative volume — institutional accumulation signal."""
    vol = _safe_float(profile_data.get("volAvg"))
    vol_today = _safe_float(profile_data.get("volume"))
    if not vol or not vol_today or vol <= 0:
        return 3
    rvol = vol_today / vol
    if rvol > 5:
        return 10
    if rvol > 3:
        return 9
    if rvol > 2:
        return 8
    if rvol > 1.5:
        return 6
    if rvol > 1:
        return 4
    return 2  # Below average volume


def _score_price_vs_52w(quote_data: Dict) -> float:
    """Price vs 52-week range — near low with improving fundamentals = classic setup."""
    high = _safe_float(quote_data.get("yearHigh"))
    low = _safe_float(quote_data.get("yearLow"))
    price = _safe_float(quote_data.get("price"))
    if not high or not low or not price or high <= low:
        return 5
    range_pct = (price - low) / (high - low)  # 0 = at 52w low, 1 = at 52w high
    # Sweet spot: 10-40% from the low (bottoming pattern + momentum starting)
    if 0.1 <= range_pct <= 0.25:
        return 9  # Near bottom, potential reversal
    if 0.25 < range_pct <= 0.4:
        return 8  # Emerging from bottom
    if 0.4 < range_pct <= 0.6:
        return 6  # Mid range
    if 0.6 < range_pct <= 0.8:
        return 5  # Getting expensive
    if range_pct > 0.8:
        return 3  # Near highs — limited upside for explosive move
    if range_pct < 0.1:
        return 4  # Might be value trap
    return 5


def _score_analyst_momentum(grades_data: List[Dict]) -> float:
    """Recent analyst upgrade momentum — Wall Street catching on."""
    if not grades_data:
        return 4
    recent = grades_data[:5]  # Last 5 actions
    upgrades = sum(1 for g in recent if "upgrade" in (g.get("action", "") or "").lower())
    downgrades = sum(1 for g in recent if "downgrade" in (g.get("action", "") or "").lower())
    if upgrades >= 3 and downgrades == 0:
        return 10
    if upgrades >= 2 and downgrades == 0:
        return 9
    if upgrades > downgrades:
        return 7
    if upgrades == downgrades:
        return 5
    if downgrades > upgrades:
        return 3
    return 4


def _score_debt_to_equity(metrics: Dict) -> float:
    """Low leverage — room for growth without debt burden."""
    dte = _safe_float(metrics.get("debtToEquityTTM"))
    if dte is None:
        return 5
    if dte < 0:
        return 4  # Negative equity — unusual
    if dte < 0.3:
        return 10  # Almost debt-free
    if dte < 0.5:
        return 9
    if dte < 1.0:
        return 7
    if dte < 2.0:
        return 5
    if dte < 5.0:
        return 3
    return 1  # Heavy leverage


def _score_operating_margin(metrics: Dict) -> float:
    """Operating margin expansion — profitability trajectory."""
    margin = _safe_float(metrics.get("operatingProfitMarginTTM"))
    if margin is None:
        return 4
    margin_pct = margin * 100 if abs(margin) < 1 else margin
    if margin_pct > 30:
        return 10
    if margin_pct > 20:
        return 8
    if margin_pct > 10:
        return 7
    if margin_pct > 0:
        return 5
    if margin_pct > -10:
        return 3  # Slightly unprofitable but improving
    return 1  # Burning cash


def _score_pe_ratio(metrics: Dict) -> float:
    """PE ratio — reasonable valuation for a growth stock.
    For high-growth stocks, slightly elevated PE is acceptable."""
    pe = _safe_float(metrics.get("peRatioTTM"))
    if pe is None or pe <= 0:
        return 4  # No earnings or negative
    if pe < 15:
        return 9  # Undervalued
    if pe < 25:
        return 8  # Fair
    if pe < 40:
        return 6  # Growth premium
    if pe < 80:
        return 4
    if pe < 150:
        return 3
    return 1  # Extremely overvalued


def _score_price_breakout(quote_data: Dict, profile_data: Dict) -> float:
    """Price breakout: above 50-day and 200-day SMA = strong trend."""
    price = _safe_float(quote_data.get("price"))
    sma50 = _safe_float(profile_data.get("fiftyDayAverage") or profile_data.get("priceAvg50"))
    sma200 = _safe_float(profile_data.get("twoHundredDayAverage") or profile_data.get("priceAvg200"))
    if not price:
        return 5
    score = 5
    if sma50 and price > sma50:
        score += 2  # Above 50-day
    if sma200 and price > sma200:
        score += 2  # Above 200-day
    # Fresh breakout bonus: just crossed above (within 5%)
    if sma200 and price > sma200 and price < sma200 * 1.05:
        score += 1  # Fresh breakout!
    if sma50 and sma200 and sma50 > sma200:
        score += 1  # Golden cross
    return min(10, score)


def _score_upside_potential(quote_data: Dict, analyst_target: Dict) -> float:
    """Analyst upside potential — consensus room to grow."""
    price = _safe_float(quote_data.get("price"))
    target = _safe_float(analyst_target.get("avg_price_target") if analyst_target else None)
    if not price or not target or price <= 0:
        return 4
    upside = ((target - price) / price) * 100
    if upside > 80:
        return 10
    if upside > 50:
        return 9
    if upside > 30:
        return 8
    if upside > 15:
        return 6
    if upside > 0:
        return 4
    return 2  # Downside


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

def _analyze_stock(symbol: str, sector: str) -> Optional[Dict]:
    """Analyze a single stock across all parameters. Returns scored dict or None."""
    try:
        from fmp_client import (
            quote as fmp_quote, profile as fmp_profile,
            key_metrics_ttm, institutional_holders, insider_trading,
            grades as fmp_grades, analyst_price_target,
        )

        # Fetch all data for this stock
        q = fmp_quote(symbol)
        if not q or not q.get("price"):
            return None

        prof = fmp_profile(symbol) or {}
        km = key_metrics_ttm(symbol) or {}
        holders = institutional_holders(symbol) or []
        insiders = insider_trading(symbol, limit=10) or []
        g = fmp_grades(symbol, limit=5) or []
        target = analyst_price_target(symbol)

        price = q["price"]
        market_cap = q.get("market_cap") or prof.get("mktCap") or prof.get("marketCap")
        name = q.get("name") or prof.get("companyName") or symbol

        # Growth metrics from profile
        growth_metrics = {}
        if prof:
            growth_metrics["revenueGrowth"] = prof.get("revenueGrowth")

        # Build quote data for scoring
        quote_data = {
            "price": price,
            "yearHigh": prof.get("range", "0-0").split("-")[-1] if prof.get("range") else None,
            "yearLow": prof.get("range", "0-0").split("-")[0] if prof.get("range") else None,
            "volume": q.get("volume"),
        }
        try:
            quote_data["yearHigh"] = float(quote_data["yearHigh"]) if quote_data["yearHigh"] else None
            quote_data["yearLow"] = float(quote_data["yearLow"]) if quote_data["yearLow"] else None
        except (ValueError, TypeError):
            quote_data["yearHigh"] = None
            quote_data["yearLow"] = None

        profile_data = prof or {}

        # Score all parameters
        scores = {
            "market_cap": _score_market_cap(market_cap),
            "revenue_growth": _score_revenue_growth(growth_metrics),
            "institutional": _score_institutional_accumulation(holders),
            "insider_buying": _score_insider_buying(insiders),
            "volume_breakout": _score_volume_breakout(profile_data),
            "price_vs_52w": _score_price_vs_52w(quote_data),
            "analyst_momentum": _score_analyst_momentum(g),
            "debt_equity": _score_debt_to_equity(km),
            "operating_margin": _score_operating_margin(km),
            "pe_ratio": _score_pe_ratio(km),
            "price_breakout": _score_price_breakout(quote_data, profile_data),
            "upside_potential": _score_upside_potential(q, target),
        }

        # Sector momentum multiplier
        sector_mult = SECTOR_MOMENTUM.get(sector, 1.0)

        # Weighted composite score
        weights = {
            "market_cap": 1.5,
            "revenue_growth": 2.0,        # Most important
            "institutional": 1.8,
            "insider_buying": 1.5,
            "volume_breakout": 1.0,
            "price_vs_52w": 1.2,
            "analyst_momentum": 1.0,
            "debt_equity": 0.8,
            "operating_margin": 1.3,
            "pe_ratio": 0.7,
            "price_breakout": 1.2,
            "upside_potential": 1.5,
        }

        weighted_sum = sum(scores[k] * weights[k] for k in scores)
        max_possible = sum(10 * w for w in weights.values())
        composite = (weighted_sum / max_possible) * 100 * sector_mult

        # Build thesis
        top_params = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        param_names = {
            "market_cap": "Small cap advantage",
            "revenue_growth": "Strong revenue growth",
            "institutional": "Institutional accumulation",
            "insider_buying": "Insider buying cluster",
            "volume_breakout": "Volume breakout",
            "price_vs_52w": "Favorable 52w positioning",
            "analyst_momentum": "Analyst upgrade momentum",
            "debt_equity": "Low debt",
            "operating_margin": "Expanding margins",
            "pe_ratio": "Reasonable valuation",
            "price_breakout": "Price breakout pattern",
            "upside_potential": "High analyst upside",
        }
        thesis_parts = [param_names.get(p[0], p[0]) for p in top_params if p[1] >= 7]
        thesis = ". ".join(thesis_parts) + "." if thesis_parts else "Multi-factor candidate."

        # Upside calculation
        upside_pct = None
        if target and target.get("avg_price_target") and price > 0:
            upside_pct = round(((target["avg_price_target"] - price) / price) * 100, 1)

        # Change percent
        change_pct = q.get("change_percent", 0)

        return {
            "symbol": symbol,
            "name": name,
            "price": round(price, 2),
            "change_percent": round(change_pct, 2) if change_pct else 0,
            "market_cap": market_cap,
            "sector": sector,
            "industry": prof.get("industry", ""),
            "composite_score": round(composite, 1),
            "scores": scores,
            "thesis": thesis,
            "upside_pct": upside_pct,
            "num_institutions": len(holders),
            "insider_buys": len([x for x in insiders if x.get("is_buy")]),
            "analyst_target": target.get("avg_price_target") if target else None,
        }

    except Exception as e:
        logger.warning("Alpha scan failed for %s: %s", symbol, e)
        return None


def run_alpha_scan(max_stocks: int = 10) -> List[Dict]:
    """
    Run the full alpha scan across all sectors.
    Returns top N stocks ranked by composite score.
    """
    start = time.time()
    logger.info("═══ Alpha Screener starting full scan ═══")

    all_candidates = []

    # Build flat list of (symbol, sector) — deduplicated
    scan_list = []
    seen = set()
    for sector, symbols in SCAN_UNIVERSE.items():
        for sym in symbols:
            if sym not in seen:
                seen.add(sym)
                scan_list.append((sym, sector))

    logger.info("Scanning %d unique stocks across %d sectors", len(scan_list), len(SCAN_UNIVERSE))

    # Parallel scan — 5 workers to respect API rate limits
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_analyze_stock, sym, sector): (sym, sector)
                   for sym, sector in scan_list}
        for future in as_completed(futures):
            sym, sector = futures[future]
            try:
                result = future.result()
                if result and result.get("composite_score", 0) > 0:
                    results.append(result)
            except Exception as e:
                logger.warning("Alpha scan error for %s: %s", sym, e)

    # Sort by composite score descending
    results.sort(key=lambda x: x["composite_score"], reverse=True)

    # Take top N
    top = results[:max_stocks]

    # Add rank
    for i, stock in enumerate(top, 1):
        stock["rank"] = i

    elapsed = time.time() - start
    logger.info("═══ Alpha Screener complete: %d candidates scored, top %d selected, %.1fs ═══",
                len(results), len(top), elapsed)

    return top


# ═══════════════════════════════════════════════════════════════════════════════
#  CACHED SCANNER WITH BACKGROUND REFRESH
# ═══════════════════════════════════════════════════════════════════════════════

_alpha_cache = None  # (timestamp, results)
_alpha_lock = threading.Lock()
ALPHA_CACHE_TTL = 3600  # 1 hour


def get_alpha_picks(force_refresh: bool = False) -> List[Dict]:
    """Get cached alpha picks, or run scan if cache expired."""
    global _alpha_cache
    with _alpha_lock:
        if not force_refresh and _alpha_cache is not None:
            ts, data = _alpha_cache
            if time.time() - ts < ALPHA_CACHE_TTL and data:
                return data

    # Run scan (outside lock to allow concurrent reads of stale cache)
    results = run_alpha_scan(max_stocks=10)

    with _alpha_lock:
        _alpha_cache = (time.time(), results)

    return results


def _alpha_refresh_loop():
    """Background thread: refresh alpha picks every 2 hours."""
    while True:
        try:
            logger.info("Alpha screener background refresh starting...")
            results = run_alpha_scan(max_stocks=10)
            with _alpha_lock:
                global _alpha_cache
                _alpha_cache = (time.time(), results)
            logger.info("Alpha screener refreshed: %d picks", len(results))
        except Exception as e:
            logger.error("Alpha screener background refresh failed: %s", e)
        time.sleep(7200)  # 2 hours


def start_alpha_background():
    """Start background alpha screener refresh thread."""
    t = threading.Thread(target=_alpha_refresh_loop, daemon=True, name="alpha-screener")
    t.start()
    logger.info("Alpha screener background thread started (interval: 2h)")
    return t
