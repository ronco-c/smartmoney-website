"""
Financial Modeling Prep (FMP) API client.
Real-time quote, profile, institutional holders (13F-style), analyst price target, news, search.
Set FMP_API_KEY in env for live data. Falls back to None when key missing or request fails.
No caching for quote/holdings — always fetch latest. Full tradable list cached briefly for search.

NOTE: FMP deprecated /api/v3/ endpoints in Aug 2025. New keys must use /stable/ endpoints.
This client tries /stable/ first, falls back to /api/v3/ for legacy keys.
"""
import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)
BASE = "https://financialmodelingprep.com"
STABLE_PATH = "/stable"
V3_PATH = "/api/v3"

def _api_key():
    """Lazy read so dotenv has time to load before first call."""
    return os.environ.get("FMP_API_KEY", "").strip()

# Full tradable list cache: (timestamp, list). TTL 5 min so search has global symbols without hammering API.
_tradable_list_cache: Optional[tuple] = None
TRADABLE_LIST_TTL_SEC = 300

_last_call_time = 0.0

def _get(path: str, params: Optional[Dict] = None) -> Optional[Any]:
    """Make GET request to FMP /stable/ API.
    Since the user's key is post-Aug-2025, /api/v3/ always returns 403.
    We only call /stable/ to avoid wasting API quota on double calls."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < 0.25:
        time.sleep(0.25 - elapsed)
    _last_call_time = time.time()

    key = _api_key()
    if not key:
        return None
    p = dict(params or {})
    p["apikey"] = key
    url = BASE + STABLE_PATH + "/" + path.lstrip("/")
    try:
        r = requests.get(url, params=p, timeout=12)
        if not r.ok:
            logger.error("FMP error %s %s: %s", r.status_code, url, r.text[:200])
            return None
        data = r.json()
        return data
    except Exception as e:
        logger.warning("FMP request failed %s: %s", path, e)
        return None


def _get_stable(path: str, params: Optional[Dict] = None) -> Optional[Any]:
    """Alias for _get — both use /stable/ now."""
    return _get(path, params)


def quote(symbol: str) -> Optional[Dict]:
    """Real-time quote: price, change, changePercent, volume, marketCap.
    Uses /stable/quote?symbol=X."""
    data = _get("quote", {"symbol": symbol.upper()})
    if not data:
        return None
    q = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
    if not q:
        return None
    price = q.get("price")
    if price is None:
        return None
    change_pct = float(q.get("changesPercentage") or q.get("changePercentage") or 0)
    change_abs = float(q.get("change", 0) or 0)
    return {
        "symbol": (q.get("symbol") or symbol).upper(),
        "name": q.get("name") or symbol,
        "price": round(float(price), 2),
        "change": round(change_abs, 2),
        "change_percent": round(change_pct, 2),
        "volume": int(q.get("volume") or 0),
        "market_cap": q.get("marketCap"),
    }


def batch_quote(symbols: List[str]) -> List[Dict]:
    """Batch real-time quotes using FMP /stable/quote/AAPL,MSFT,NVDA."""
    if not symbols:
        return []
    joined = ",".join(s.upper() for s in symbols)
    data = _get(f"quote/{joined}")
    if not data or not isinstance(data, list):
        return []
    
    results = []
    for q in data:
        price = q.get("price")
        if price is None:
            continue
        change_pct = float(q.get("changesPercentage") or q.get("changePercentage") or 0)
        change_abs = float(q.get("change", 0) or 0)
        sym = q.get("symbol")
        results.append({
            "symbol": sym.upper(),
            "name": q.get("name") or sym,
            "price": round(float(price), 2),
            "change": round(change_abs, 2),
            "change_percent": round(change_pct, 2),
            "volume": int(q.get("volume") or 0),
            "market_cap": q.get("marketCap"),
        })
    return results


def profile(symbol: str) -> Optional[Dict]:
    """Company profile: name, mktCap, sector, description, etc."""
    data = _get("profile", {"symbol": symbol.upper()})
    if not data:
        return None
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def institutional_holders(symbol: str) -> List[Dict]:
    """
    Institutional holders (13F-style). Latest quarterly filing.
    SEC 13F reports value in THOUSANDS — we convert to full dollars for value and avg_price.
    Position change: reportHoldingChange (%) or positionChange (Added/Reduced/New/Sold Out).
    """
    data = _get("institutional-holder", {"symbol": symbol.upper()})
    if not data or not isinstance(data, list):
        return []
    out = []
    for h in data:
        holder = (h.get("holder") or h.get("organization") or "").strip()
        if not holder:
            continue
        shares = h.get("shares") or h.get("numberOfShares")
        if shares is not None:
            try:
                shares = int(shares)
            except (TypeError, ValueError):
                shares = None
        value_report = h.get("valueReported") or h.get("value")
        if value_report is not None:
            try:
                value_report = float(value_report)
            except (TypeError, ValueError):
                value_report = None
        # SEC 13F: valueReported is in THOUSANDS of dollars. Convert to full dollars.
        value_dollars = None
        if value_report is not None:
            value_dollars = value_report * 1000
        # Estimated avg cost per share = total value / shares (must be in same order as stock price)
        avg_price = None
        if shares and value_dollars is not None and shares > 0:
            avg_price = round(value_dollars / shares, 2)
        # Position change: prefer numeric % (reportHoldingChange), then changeInShares, then Added/Reduced
        report_date = h.get("dateReported") or h.get("reportDate") or ""
        pc_pct = h.get("reportHoldingChange") or h.get("holdingChangePercent") or h.get("changePercent")
        pc_shares = h.get("changeInShares")
        position_change = h.get("positionChange") or h.get("change") or ""
        if pc_pct is not None:
            try:
                pct = float(pc_pct)
                position_change = f"{pct:+.1f}%" if pct != 0 else "Unchanged"
            except (TypeError, ValueError):
                pass
        elif pc_shares is not None and isinstance(pc_shares, (int, float)):
            try:
                position_change = f"{int(pc_shares):+,}" + " shares" if position_change == "" else position_change
            except (TypeError, ValueError):
                pass
        if position_change == "" and (h.get("positionChange") or h.get("change")):
            position_change = str(h.get("positionChange") or h.get("change"))
        out.append({
            "institution": holder,
            "shares": shares,
            "value": value_dollars,
            "date_reported": report_date,
            "position_change": position_change,
            "avg_price": avg_price,
        })
    return out


def institutional_net_direction(symbol: str) -> str:
    """
    From 13F institutional-holder data: "buy" (net inflow), "sell" (net outflow), or "neutral".
    Used to filter out companies where institutional ownership is declining (net sell).
    """
    holders = institutional_holders(symbol)
    if not holders:
        return "neutral"
    add_count = 0
    reduce_count = 0
    total_pct = 0.0
    n_pct = 0
    for h in holders:
        pc = h.get("position_change") or ""
        pc_str = str(pc).strip()
        if "Added" in pc_str or "New" in pc_str or (pc_str.startswith("+") and "%" in pc_str):
            add_count += 1
        elif "Reduced" in pc_str or "Sold" in pc_str or (pc_str.startswith("-") and "%" in pc_str):
            reduce_count += 1
        try:
            if "%" in pc_str:
                pct_val = float(pc_str.replace("%", "").replace("+", "").strip())
                total_pct += pct_val
                n_pct += 1
        except (ValueError, TypeError):
            pass
    if n_pct > 0:
        avg_pct = total_pct / n_pct
        if avg_pct > 2:
            return "buy"
        if avg_pct < -2:
            return "sell"
    if add_count > reduce_count + 1:
        return "buy"
    if reduce_count > add_count + 1:
        return "sell"
    return "neutral"


def grades(symbol: str, limit: int = 10) -> List[Dict]:
    """Analyst grades: upgrades, downgrades, maintained ratings from Wall Street firms.
    Uses /stable/grades?symbol=X — real analyst actions with firm names."""
    data = _get("grades", {"symbol": symbol.upper()})
    if not data or not isinstance(data, list):
        return []
    out = []
    for item in data[:limit]:
        out.append({
            "symbol": (item.get("symbol") or symbol).upper(),
            "date": item.get("date") or "",
            "grading_company": item.get("gradingCompany") or "",
            "previous_grade": item.get("previousGrade") or "",
            "new_grade": item.get("newGrade") or "",
            "action": item.get("action") or "",  # "upgrade", "downgrade", "maintain"
        })
    return out


def analyst_price_target(symbol: str) -> Optional[Dict]:
    """Analyst consensus: avg price target, upside/downside %."""
    data = _get("price-target", {"symbol": symbol.upper()})
    if not data or not isinstance(data, list) or len(data) == 0:
        return None
    # Use latest entry; aggregate if multiple
    targets = [float(x.get("adjPriceTarget") or x.get("priceTarget") or x.get("priceWhenPosted") or 0) for x in data if x.get("adjPriceTarget") or x.get("priceTarget") or x.get("priceWhenPosted")]
    if not targets:
        return None
    avg_target = sum(targets) / len(targets)
    return {
        "symbol": symbol.upper(),
        "avg_price_target": round(avg_target, 2),
        "targets": targets,
        "num_analysts": len(data),
    }


def stock_news(limit: int = 50, tickers: Optional[str] = None) -> List[Dict]:
    """Real-time stock/market news. tickers optional comma-separated."""
    params = {"limit": limit}
    if tickers:
        params["tickers"] = tickers
    data = _get("stock_news", params)
    if not data or not isinstance(data, list):
        return []
    out = []
    for n in data:
        out.append({
            "title": n.get("title") or "",
            "text": (n.get("text") or "")[:500],
            "url": n.get("url") or "#",
            "source": n.get("site") or "FMP",
            "time": n.get("publishedDate") or "",
            "tickers": (n.get("tickers") or "").split(",") if n.get("tickers") else [],
        })
    return out


def search(query: str, limit: int = 30) -> List[Dict]:
    """Search symbols by name or ticker. Returns [{ symbol, name, type }]."""
    data = _get("search", {"query": query, "limit": limit})
    if not data or not isinstance(data, list):
        return []
    out = []
    seen = set()
    for item in data[:limit]:
        sym = (item.get("symbol") or "").strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        name = (item.get("name") or item.get("description") or sym).strip()
        out.append({
            "symbol": sym,
            "name": name,
            "type": item.get("type") or "stock",
        })
    return out


def search_ticker(query: str, limit: int = 30) -> List[Dict]:
    """Alternative: search-ticker endpoint if available."""
    data = _get("search-ticker", {"query": query, "limit": limit})
    if not data or not isinstance(data, list):
        return []
    out = []
    seen = set()
    for item in data[:limit]:
        sym = (item.get("symbol") or "").strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        name = (item.get("name") or item.get("description") or sym).strip()
        out.append({"symbol": sym, "name": name, "type": "stock"})
    return out


def _fetch_tradable_list() -> List[Dict]:
    """Fetch full list of tradable symbols (Nasdaq/NYSE/etc). No cache inside this function."""
    # FMP: stock/list = all stocks; available-traded/list = all tradable (stocks + ETFs)
    for path in ("stock/list", "available-traded/list"):
        data = _get(path)
        if data and isinstance(data, list) and len(data) > 0:
            out = []
            for item in data:
                sym = (item.get("symbol") or "").strip()
                if not sym:
                    continue
                name = (item.get("name") or item.get("description") or sym).strip()
                out.append({"symbol": sym, "name": name, "type": item.get("type") or "stock"})
            if out:
                logger.info("FMP tradable list: %s returned %d symbols", path, len(out))
                return out
    return []


def get_tradable_list(force_refresh: bool = False) -> List[Dict]:
    """Full list of tradable symbols. Cached for TRADABLE_LIST_TTL_SEC so search is fast and global."""
    global _tradable_list_cache
    now = time.time()
    if not force_refresh and _tradable_list_cache is not None:
        ts, lst = _tradable_list_cache
        if now - ts < TRADABLE_LIST_TTL_SEC and lst:
            return lst
    lst = _fetch_tradable_list()
    _tradable_list_cache = (now, lst)
    return lst


def search_tradable(query: str, limit: int = 50) -> List[Dict]:
    """
    Search over full tradable symbol list (global market). No hardcoded list.
    Uses cached API list; filters by symbol (exact/prefix) and name (substring).
    """
    q = (query or "").strip().upper()
    if not q or len(q) < 1:
        return []
    all_syms = get_tradable_list()
    if not all_syms:
        return []
    ql = query.strip().lower()
    exact = []
    prefix = []
    name_match = []
    for item in all_syms:
        sym = (item.get("symbol") or "").upper()
        name = (item.get("name") or "").lower()
        if sym == q:
            exact.append(item)
        elif sym.startswith(q):
            prefix.append(item)
        elif ql in name or q in sym:
            name_match.append(item)
    seen = set()
    out = []
    for item in exact + prefix + name_match:
        sym = item.get("symbol") or ""
        if sym in seen:
            continue
        seen.add(sym)
        out.append({"symbol": sym, "name": item.get("name") or sym, "type": item.get("type") or "stock"})
        if len(out) >= limit:
            break
    return out


def stock_screener(filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict]:
    """
    Screen stocks using FMP Stock Screener endpoint.
    filters: dict of criteria (e.g. {'dividendMoreThan': 1.5, 'marketCapMoreThan': 1000000000, 'isEtf': false})
    """
    data = _get("stock-screener", {**(filters or {}), "limit": limit})
    if not data or not isinstance(data, list):
        return []
    out = []
    # FMP screener returns slightly different keys than quote
    for item in data:
        sym = item.get("symbol")
        if not sym:
            continue
        out.append({
            "symbol": sym,
            "name": item.get("companyName") or sym,
            "price": _float(item.get("price")),
            "market_cap": item.get("marketCap"),
            "sector": item.get("sector"),
            "industry": item.get("industry"),
            "beta": _float(item.get("beta")),
            "dividend_yield": _float(item.get("lastAnnualDividend") / item.get("price") * 100 if item.get("price") else 0) if item.get("lastAnnualDividend") is not None else _float(item.get("dividendYield"))
        })
    return out


# --- Hot Stocks (gainers / most active) ---
def stock_market_gainers(limit: int = 50) -> List[Dict]:
    """Biggest gainers by % — high momentum, significant % change."""
    data = _get("stock_market_gainers")
    if not data or not isinstance(data, list):
        return []
    out = []
    for item in data[:limit]:
        sym = (item.get("symbol") or "").strip()
        if not sym:
            continue
        change_pct = item.get("changesPercentage") or 0
        try:
            change_pct = float(change_pct)
        except (TypeError, ValueError):
            change_pct = 0
        out.append({
            "symbol": sym,
            "name": item.get("name") or sym,
            "price": _float(item.get("price")),
            "change": _float(item.get("change")),
            "change_percent": round(change_pct, 2),
            "volume": int(item.get("volume") or 0),
        })
    return out


def stock_market_most_active(limit: int = 50) -> List[Dict]:
    """Most active by volume — high RVOL / breakout candidates."""
    data = _get("stock_market_most_active")
    if not data or not isinstance(data, list):
        return []
    out = []
    for item in data[:limit]:
        sym = (item.get("symbol") or "").strip()
        if not sym:
            continue
        change_pct = item.get("changesPercentage") or 0
        try:
            change_pct = float(change_pct)
        except (TypeError, ValueError):
            change_pct = 0
        out.append({
            "symbol": sym,
            "name": item.get("name") or sym,
            "price": _float(item.get("price")),
            "change": _float(item.get("change")),
            "change_percent": round(change_pct, 2),
            "volume": int(item.get("volume") or 0),
        })
    return out


def _float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return None


# --- Insider trading (Form 4) ---
def insider_trading(symbol: str, limit: int = 30) -> List[Dict]:
    """Insider transactions (Form 4): CEO, CFO, Directors — buy/sell. Cluster buys = multiple insiders buying."""
    data = _get("insider-trading", {"symbol": symbol.upper(), "limit": limit})
    if not data or not isinstance(data, list):
        return []
    out = []
    for item in data:
        reporting = (item.get("reportingName") or item.get("filerName") or "").strip()
        if not reporting:
            reporting = "—"
        txn = (item.get("transactionType") or item.get("type") or "").strip()
        is_buy = "P" in txn.upper() or "BUY" in txn.upper() or "A" in txn.upper()
        shares = item.get("secShares") or item.get("numberOfSharesTransacted") or item.get("sharesTransacted")
        out.append({
            "reporting_name": reporting,
            "title": (item.get("typeOfOwner") or item.get("officerTitle") or "").strip() or "—",
            "transaction_type": txn or "—",
            "is_buy": is_buy,
            "shares": int(shares) if shares is not None else None,
            "filing_date": item.get("filingDate") or item.get("reportDate") or "",
        })
    return out


# --- Key Metrics TTM (PE, Dividend Yield, etc.) ---
def key_metrics_ttm(symbol: str) -> Optional[Dict]:
    """Trailing twelve months key metrics: PE ratio, dividend yield, book value, etc."""
    data = _get("key-metrics-ttm", {"symbol": symbol.upper()})
    if not data:
        return None
    row = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
    if not row:
        return None
    return {
        "pe_ratio": _float(row.get("peRatioTTM")),
        "dividend_yield": _float(row.get("dividendYieldTTM")),
        "peg_ratio": _float(row.get("pegRatioTTM")),
        "earnings_yield": _float(row.get("earningsYieldTTM")),
        "book_value_per_share": _float(row.get("bookValuePerShareTTM")),
        "debt_to_equity": _float(row.get("debtToEquityTTM")),
        "current_ratio": _float(row.get("currentRatioTTM")),
        "roe": _float(row.get("roeTTM")),
    }


# --- Price Target Consensus (Low / Avg / High) ---
def price_target_consensus(symbol: str) -> Optional[Dict]:
    """Analyst price target consensus: low, avg, high, median.
    Uses /stable/price-target-consensus (real Wall Street consensus data)."""
    data = _get("price-target-consensus", {"symbol": symbol.upper()})
    if not data:
        return None
    row = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
    if not row:
        return None
    return {
        "symbol": symbol.upper(),
        "target_high": _float(row.get("targetHigh")),
        "target_low": _float(row.get("targetLow")),
        "target_consensus": _float(row.get("targetConsensus")),
        "target_median": _float(row.get("targetMedian")),
    }


# --- Analyst Estimates (forward revenue / EPS) ---
def analyst_estimates(symbol: str, period: str = "annual") -> List[Dict]:
    """Analyst forward estimates: revenue, EPS, EBITDA per quarter/year.
    Uses /stable/analyst-estimates (requires period param)."""
    data = _get("analyst-estimates", {"symbol": symbol.upper(), "period": period})
    if not data or not isinstance(data, list):
        return []
    out = []
    for item in data:
        out.append({
            "date": item.get("date") or "",
            "revenue_avg": _float(item.get("estimatedRevenueAvg")),
            "revenue_low": _float(item.get("estimatedRevenueLow")),
            "revenue_high": _float(item.get("estimatedRevenueHigh")),
            "eps_avg": _float(item.get("estimatedEpsAvg")),
            "eps_low": _float(item.get("estimatedEpsLow")),
            "eps_high": _float(item.get("estimatedEpsHigh")),
            "ebitda_avg": _float(item.get("estimatedEbitdaAvg")),
            "num_analysts_eps": item.get("numberAnalystEstimatedEps"),
            "num_analysts_revenue": item.get("numberAnalystsEstimatedRevenue"),
        })
    # Sort chronologically
    return sorted(out, key=lambda x: x["date"])[:20]


# --- Analyst Recommendation (Buy/Hold/Sell distribution) ---
def analyst_recommendation(symbol: str) -> Optional[Dict]:
    """Analyst ratings: strongBuy, buy, hold, sell, strongSell counts."""
    data = _get("analyst-stock-recommendations", {"symbol": symbol.upper()})
    if not data or not isinstance(data, list):
        return None
    # Usually sorted by date desc?
    # returns list of objects with date
    row = data[0] if data else None
    if not row:
        return None
    return {
        "date": row.get("date"),
        "strong_buy": int(row.get("analystRatingsstrongBuy") or 0),
        "buy": int(row.get("analystRatingsbuy") or 0),
        "hold": int(row.get("analystRatingshold") or 0),
        "sell": int(row.get("analystRatingssell") or 0),
        "strong_sell": int(row.get("analystRatingsstrongSell") or 0),
        "consensus": row.get("analystRatingsScore"),  # usually unused but good to have
    }


# --- Historical price (for chart) ---
def historical_daily(symbol: str, from_date: str, to_date: str) -> List[Dict]:
    """Daily OHLCV for chart. from_date/to_date: YYYY-MM-DD."""
    # V3 endpoint: historical-price-full/SYMBOL?from=..&to=..
    data = _get("historical-price-full", {"symbol": symbol.upper(), "from": from_date, "to": to_date})
    if not data:
        return []
    if isinstance(data, list):
        # some endpoints return list directly
        hist = data
    elif isinstance(data, dict):
        # historical-price-full returns { symbol:..., historical: [...] }
        hist = data.get("historical") or data.get("historicalList") or []
    else:
        return []
    if not isinstance(hist, list):
        return []
    out = []
    for d in hist:
        out.append({
            "date": d.get("date"),
            "open": _float(d.get("open")),
            "high": _float(d.get("high")),
            "low": _float(d.get("low")),
            "close": _float(d.get("close")),
            "volume": int(d.get("volume") or 0),
        })
    return sorted(out, key=lambda x: (x["date"] or ""))[:1000]


# --- Institutional ownership over time (for chart) ---
def institutional_ownership_history(symbol: str) -> List[Dict]:
    """Institutional shares held over time (for dual-axis chart)."""
    data = _get("institutional-holder/symbol-ownership", {"symbol": symbol.upper()})
    if not data or not isinstance(data, list):
        return []
    out = []
    for item in data:
        out.append({
            "date": item.get("dateReported") or item.get("reportDate") or item.get("date"),
            "shares": item.get("totalShares") or item.get("shares") or item.get("numberOfShares"),
        })
    return sorted(out, key=lambda x: (x["date"] or ""))[:24]
