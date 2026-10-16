"""
Polygon.io API client.
Market data: Reference (all tickers), Last Trade / Snapshot for real-time prices.
Set POLYGON_API_KEY in env. Used for all ticker list and real-time pricing.
"""
import os
import logging
import time
from typing import List, Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)
BASE = "https://api.polygon.io"

def _api_key():
    """Lazy read so dotenv has time to load before first call."""
    return os.environ.get("POLYGON_API_KEY", "").strip()

_tickers_cache: Optional[tuple] = None
TICKERS_CACHE_TTL = 600  # 10 min


def _get(path: str, params: Optional[Dict] = None) -> Optional[Any]:
    key = _api_key()
    if not key:
        return None
    url = BASE.rstrip("/") + "/" + path.lstrip("/")
    p = dict(params or {})
    p["apiKey"] = key
    try:
        r = requests.get(url, params=p, timeout=15)
        if not r.ok:
            return None
        return r.json()
    except Exception as e:
        logger.warning("Polygon request failed %s: %s", path, e)
        return None


def reference_tickers(limit: int = 1000, cursor: Optional[str] = None, next_url: Optional[str] = None) -> Dict:
    """
    Reference Data: list of stock tickers. type=CS (common stock), market=stocks.
    Returns { results: [...], next_url: "..." } for pagination.
    """
    if next_url:
        key = _api_key()
        if key and "apiKey" not in next_url:
            next_url = next_url + ("&" if "?" in next_url else "?") + "apiKey=" + key
        try:
            r = requests.get(next_url, timeout=15)
            if not r.ok:
                return {"results": [], "next_url": None}
            data = r.json()
        except Exception as e:
            logger.warning("Polygon next_url failed: %s", e)
            return {"results": [], "next_url": None}
    else:
        params = {"market": "stocks", "type": "CS", "limit": limit, "active": "true"}
        if cursor:
            params["cursor"] = cursor
        data = _get("v3/reference/tickers", params)
    if not data or not isinstance(data, dict):
        return {"results": [], "next_url": None}
    return {
        "results": data.get("results") or [],
        "next_url": data.get("next_url"),
    }


def get_all_tickers() -> List[Dict]:
    """
    Fetch complete list of all available stock symbols from Polygon Reference API.
    Paginates until no more. Cached for TICKERS_CACHE_TTL.
    """
    global _tickers_cache
    now = time.time()
    if _tickers_cache is not None:
        ts, lst = _tickers_cache
        if now - ts < TICKERS_CACHE_TTL and lst:
            return lst
    out = []
    next_url = None
    for _ in range(150):
        page = reference_tickers(limit=1000, next_url=next_url) if next_url else reference_tickers(limit=1000)
        results = page.get("results") or []
        for item in results:
            sym = (item.get("ticker") or "").strip()
            if not sym:
                continue
            out.append({
                "symbol": sym,
                "name": (item.get("name") or item.get("ticker") or sym).strip(),
                "type": item.get("type") or "CS",
            })
        next_url = page.get("next_url")
        if not next_url or not results:
            break
    _tickers_cache = (now, out)
    logger.info("Polygon tickers: loaded %d symbols", len(out))
    return out


def search_tickers(query: str, limit: int = 50) -> List[Dict]:
    """Search all Polygon tickers by symbol prefix or name substring."""
    q = (query or "").strip().upper()
    if not q or len(q) < 1:
        return []
    all_tickers = get_all_tickers()
    if not all_tickers:
        return []
    ql = query.strip().lower()
    exact, prefix, name_match = [], [], []
    for item in all_tickers:
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


def last_trade(symbol: str) -> Optional[Dict]:
    """Last trade for ticker — real-time price. v2/last/trade/{ticker}."""
    data = _get(f"v2/last/trade/{symbol.upper()}")
    if not data or not isinstance(data, dict):
        return None
    res = data.get("results") or data.get("result")
    if not res:
        return None
    if isinstance(res, list) and len(res) > 0:
        t = res[0]
    elif isinstance(res, dict):
        t = res
    else:
        return None
    price = t.get("price") or t.get("p")
    if price is None:
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    return {
        "symbol": symbol.upper(),
        "price": round(price, 2),
        "size": t.get("size") or t.get("s"),
        "timestamp": t.get("s") or t.get("t"),
    }


def snapshot(symbol: str) -> Optional[Dict]:
    """
    Snapshot: day open, close, prev close, volume for change %.
    v2/snapshot/locale/us/markets/stocks/tickers/{ticker}
    """
    data = _get(f"v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}")
    if not data or not isinstance(data, dict):
        return None
    ticker = data.get("ticker") or data
    if isinstance(ticker, dict):
        day = ticker.get("day") or {}
        prev = ticker.get("prevDay") or {}
        cur = day.get("c") or day.get("close") or ticker.get("lastTrade", {}).get("p")
        if cur is None:
            cur = ticker.get("min", {}).get("c") or ticker.get("lastTrade", {}).get("price")
        if cur is None:
            return None
        try:
            cur = float(cur)
        except (TypeError, ValueError):
            return None
        prev_close = prev.get("c") or prev.get("close")
        try:
            prev_close = float(prev_close) if prev_close is not None else cur
        except (TypeError, ValueError):
            prev_close = cur
        change = cur - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        vol = day.get("v") or day.get("volume") or prev.get("v") or 0
        try:
            vol = int(vol)
        except (TypeError, ValueError):
            vol = 0
        return {
            "symbol": symbol.upper(),
            "name": ticker.get("name") or symbol,
            "price": round(cur, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "volume": vol,
            "open": day.get("o") or day.get("open"),
            "high": day.get("h") or day.get("high"),
            "low": day.get("l") or day.get("low"),
        }
    return None


def quote(symbol: str) -> Optional[Dict]:
    """
    Best available real-time quote: Snapshot (has OHLC + prev for change %), else Last Trade (price only).
    """
    snap = snapshot(symbol)
    if snap:
        return snap
    last = last_trade(symbol)
    if last:
        return {
            "symbol": last["symbol"],
            "name": last["symbol"],
            "price": last["price"],
            "change": None,
            "change_percent": None,
            "volume": None,
        }
    return None
