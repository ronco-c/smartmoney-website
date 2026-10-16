"""
Watchlist routes — CRUD, intelligence scanning, and AI-built watchlists.
"""
import logging
import re
import concurrent.futures

from flask import Blueprint, jsonify, request, session, render_template, redirect

from db import get_watchlist, add_to_watchlist, remove_from_watchlist, clear_watchlist
from routes.auth import login_required

logger = logging.getLogger(__name__)

watchlist_bp = Blueprint("watchlist", __name__)


# ---------------------------------------------------------------------------
# Helpers (imported lazily from app to avoid circular imports)
# ---------------------------------------------------------------------------
def _app_helpers():
    """Lazy-import helpers that live in app.py to avoid circular imports."""
    from app import _cache_get, _cache_set, _jsonify_cached, _quote_polygon, _compute_market_signal
    return _cache_get, _cache_set, _jsonify_cached, _quote_polygon, _compute_market_signal


# ---------------------------------------------------------------------------
# Watchlist CRUD
# ---------------------------------------------------------------------------
@watchlist_bp.route("/api/watchlist", methods=["GET"])
def api_watchlist():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    _cache_get, _cache_set, _jsonify_cached, _quote_polygon, _ = _app_helpers()

    tickers = get_watchlist(session["user_id"])
    from fmp_client import price_target_consensus

    def fetch_ticker_data(t):
        q = _quote_polygon(t)
        pt_key = f"price_targets:{t}"
        pt = _cache_get(pt_key)
        if pt is None:
            pt = price_target_consensus(t)
            if not pt:
                try:
                    import yfinance as yf
                    info = yf.Ticker(t).info
                    tm = info.get("targetMeanPrice")
                    if tm:
                        pt = {"target_consensus": tm}
                except Exception:
                    pass
            if pt:
                _cache_set(pt_key, pt)

        upside = None
        downside = None
        if pt and q and q.get("price"):
            target = pt.get("target_consensus")
            if target and target > 0:
                upside = round((target - q["price"]) / q["price"] * 100, 2)
                downside = -upside if upside < 0 else None

        if q:
            return {
                "symbol": t, "name": q.get("name") or t,
                "price": q.get("price"), "change_percent": q.get("change_percent"),
                "change": q.get("change"), "upside_percent": upside,
                "downside_percent": downside,
            }
        return {"symbol": t, "name": t}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        items = list(executor.map(fetch_ticker_data, tickers))

    return jsonify({"watchlist": items})


@watchlist_bp.route("/api/watchlist/add", methods=["POST"])
def api_watchlist_add():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    ticker = data.get("symbol", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Symbol required"}), 400
    success = add_to_watchlist(session["user_id"], ticker)
    if success:
        return jsonify({"message": f"{ticker} added to watchlist", "status": "added"})
    return jsonify({"message": f"{ticker} is already in watchlist", "status": "exists"})


@watchlist_bp.route("/api/watchlist/remove", methods=["POST"])
def api_watchlist_remove():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    ticker = data.get("symbol", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Symbol required"}), 400
    success = remove_from_watchlist(session["user_id"], ticker)
    if success:
        return jsonify({"message": f"{ticker} removed from watchlist", "status": "removed"})
    return jsonify({"message": f"{ticker} not found in watchlist", "status": "not_found"})


@watchlist_bp.route("/api/watchlist/check/<symbol>", methods=["GET"])
def api_watchlist_check(symbol):
    if "user_id" not in session:
        return jsonify({"in_watchlist": False})
    tickers = get_watchlist(session["user_id"])
    return jsonify({"in_watchlist": symbol.upper() in tickers})


@watchlist_bp.route("/category/watchlist")
def category_watchlist():
    if "user_id" not in session:
        return redirect("/auth")
    return render_template("watchlist.html")


# ---------------------------------------------------------------------------
# Intelligence & Build
# ---------------------------------------------------------------------------
@watchlist_bp.route("/api/watchlist/intel", methods=["GET"])
@login_required
def api_watchlist_intel():
    """Scan ENTIRE market news and recommend the best stocks to buy RIGHT NOW."""
    _cache_get, _cache_set, _jsonify_cached, _, _compute_market_signal = _app_helpers()

    cache_key = "wl_intel_market_recs"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=180)

    from finnhub_service import get_market_news, get_company_news

    market_news = get_market_news(category="general", limit=50)
    if not market_news:
        market_news = []
        for sym in ["AAPL", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "JPM", "MSFT"]:
            articles = get_company_news(sym, days=3, limit=5)
            if articles:
                for a in articles:
                    a["related"] = sym
                market_news.extend(articles)

    BULLISH_KW = {
        "beat", "beats", "surge", "surges", "soar", "rally", "upgrade", "record",
        "growth", "bullish", "breakthrough", "profit", "outperform", "strong",
        "boost", "gain", "positive", "raise", "upside", "innovative", "exceeds",
        "dividend", "acquisition", "buy", "expand", "revenue", "earnings", "deal",
        "partnership", "launch", "approve", "win", "wins", "rises", "climbs",
    }
    BEARISH_KW = {
        "miss", "misses", "plunge", "crash", "downgrade", "warning", "bearish",
        "loss", "sell", "decline", "fall", "risk", "concern", "layoff", "cut",
        "weak", "negative", "lawsuit", "probe", "investigation", "recall",
        "tariff", "delay", "fraud", "default", "debt", "drop", "drops", "slump",
        "tumble", "sinks", "slides", "fears", "trouble",
    }
    KNOWN_TICKERS = {
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AMD",
        "NFLX", "CRM", "ORCL", "AVGO", "ADBE", "INTC", "QCOM", "TXN", "PLTR",
        "CRWD", "PANW", "SNOW", "NET", "DDOG", "MDB", "UBER", "SQ", "SHOP",
        "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP", "BLK", "COIN",
        "JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV", "TMO", "ISRG", "MRNA",
        "XOM", "CVX", "COP", "SLB", "OXY", "HAL",
        "WMT", "COST", "HD", "LOW", "TGT", "SBUX", "MCD", "NKE", "LULU",
        "KO", "PEP", "PG", "DIS", "BA", "CAT", "GE", "LMT", "DE",
        "HSBC", "POOL", "SOFI", "HOOD", "PYPL", "AFRM",
    }

    ticker_data = {}
    for article in market_news:
        headline = article.get("headline", "")
        summary = article.get("summary", "")
        related = article.get("related", "")
        text = (headline + " " + summary).lower()
        words = set(text.split())
        bull_count = len(words & BULLISH_KW)
        bear_count = len(words & BEARISH_KW)
        found_tickers = set()
        if related:
            for t in re.split(r'[,;\s]+', related.upper()):
                t = t.strip()
                if t and 2 <= len(t) <= 5 and t.isalpha():
                    found_tickers.add(t)
        headline_upper = headline.upper()
        for known in KNOWN_TICKERS:
            if known in headline_upper:
                found_tickers.add(known)
        for t in found_tickers:
            if t not in ticker_data:
                ticker_data[t] = {"bull": 0, "bear": 0, "headlines": [], "count": 0}
            ticker_data[t]["bull"] += bull_count
            ticker_data[t]["bear"] += bear_count
            ticker_data[t]["count"] += 1
            if headline and len(ticker_data[t]["headlines"]) < 3:
                ticker_data[t]["headlines"].append(headline[:120])

    recommendations = []
    for sym, data in ticker_data.items():
        total = data["bull"] + data["bear"]
        score = max(1, min(10, round((data["bull"] / total) * 10))) if total else 5
        if score >= 7:
            sentiment, action = "bullish", "BUY"
        elif score <= 3:
            sentiment, action = "bearish", "AVOID"
        else:
            sentiment, action = "neutral", "WATCH"

        if sentiment == "bullish":
            reason = f"Positive news flow — {data['bull']} bullish signals across {data['count']} articles"
        elif sentiment == "bearish":
            reason = f"Negative sentiment — {data['bear']} bearish signals across {data['count']} articles"
        else:
            reason = f"Mixed coverage — {data['count']} recent articles, wait for clearer direction"

        recommendations.append({
            "symbol": sym, "score": score, "sentiment": sentiment,
            "action": action, "reason": reason, "news_count": data["count"],
            "top_headline": data["headlines"][0] if data["headlines"] else "",
            "headlines": data["headlines"][:2],
        })

    recommendations.sort(key=lambda x: (-x["score"], -x["news_count"]))
    top_recs = recommendations[:12]
    market_signal = _compute_market_signal()

    result = {
        "recommendations": top_recs,
        "market_signal": market_signal,
        "total_articles_scanned": len(market_news),
        "total_tickers_found": len(ticker_data),
    }
    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=180)


@watchlist_bp.route("/api/watchlist/build", methods=["POST"])
@login_required
def api_watchlist_build():
    data = request.json or {}
    query = data.get("query", "general").lower()
    count = int(data.get("count", 5))
    risk = data.get("risk", "medium").lower()
    user_id = session["user_id"]

    strategy_map = {
        "tech": "tech", "technology": "tech",
        "bank": "finance", "finance": "finance", "financial": "finance",
        "health": "health", "healthcare": "health",
        "energy": "energy", "retail": "retail",
        "div": "dividend", "dividend": "dividend",
        "default": "general", "general": "general",
    }
    strategy = strategy_map.get(query, "general")

    try:
        from smart_screener import scan_market
        picks = scan_market(strategy=strategy, risk=risk, count=count)
    except Exception as e:
        logger.error("Smart screener failed: %s", e)
        return jsonify({"error": "Market scan failed. Try again."}), 500

    if not picks:
        return jsonify({"error": "No stocks found matching criteria."}), 400

    clear_watchlist(user_id)
    added = []
    picks_detail = []
    for pick in picks:
        sym = pick["symbol"].upper()
        success = add_to_watchlist(user_id, sym)
        if success:
            added.append(sym)
            picks_detail.append({
                "symbol": sym, "name": pick.get("name", sym),
                "price": pick.get("price", 0), "score": pick.get("score", 0),
                "reasoning": pick.get("reasoning", ""),
                "change_1d": pick.get("change_1d", 0),
                "change_1w": pick.get("change_1w", 0),
                "change_1m": pick.get("change_1m", 0),
                "momentum": pick.get("momentum", 0),
                "vol_ratio": pick.get("vol_ratio", 1),
                "upside": pick.get("upside", 0),
                "sector": pick.get("sector", ""),
            })

    return jsonify({
        "message": f"Found {len(added)} top picks scanning the market.",
        "added": added, "picks": picks_detail,
        "strategy": strategy, "risk": risk, "status": "success",
    })
