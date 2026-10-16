"""
Real-time Stock Picks & Market Intelligence Dashboard
Serves best stocks to buy today, live news, and actionable economic advice (e.g. after inflation: jump in or stay out).
"""
import os
import sys
import json
import logging
import time
import requests
import threading
import webbrowser
from datetime import datetime, timezone, timedelta
from pathlib import Path
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

# Add parent and institutional_analyzer to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "institutional_analyzer"))

# Load .env files so API keys are available
try:
    from dotenv import load_dotenv
    for env_path in [ROOT / "smart_money" / ".env", ROOT / "webapp" / ".env", ROOT / ".env"]:
        if env_path.exists():
            load_dotenv(env_path, override=False)
except ImportError:
    pass  # python-dotenv not installed — keys must be in env already

try:
    from flask import Flask, jsonify, send_from_directory, request, render_template, make_response, session, redirect
except ImportError:
    print("Flask is not installed. Run: pip3 install flask")
    raise SystemExit(1)
from news_service import get_news_and_advice
from db import (
    init_db, has_data, get_cache, get_consensus_with_change, 
    get_big_money_movers, get_all_institution_summaries, set_cache,
    create_user, get_user_by_email, get_user_by_id, 
    set_reset_token, get_user_by_reset_token, update_password,
    add_to_watchlist, remove_from_watchlist, get_watchlist,
    clear_watchlist, get_user_preferences, update_user_preferences,
    add_alert, get_user_alerts, deactivate_alert,
    create_notification, get_user_notifications, mark_notifications_read
)

# ---------------------------------------------------------------------------
# Unified TTL cache — avoids hammering FMP/Polygon on every page refresh
# ---------------------------------------------------------------------------
_MEM_CACHE = {}
MAX_CACHE_SIZE = 500
CACHE_TTL = {
    "quote": 30,           # near-real-time; 30s is enough to avoid burst
    "holders": 300,        # 13F data changes quarterly
    "analyst": 300,        # analyst targets change infrequently
    "news": 120,           # refresh news every 2 min
    "hot_stocks": 90,      # hot stocks refresh
    "breakout": 90,        # institutional breakout refresh
    "full_stock": 60,      # combined stock detail page
    "market_indices": 30,  # market indices bar — 30s to avoid rate-limit storms
    "insider": 300,        # insider trades change infrequently
    "chart": 600,          # price chart data
    "batch_quotes": 30,    # batch quotes for live daily % column
}

def _cache_get(key: str):
    """Return cached data if still valid, else None."""
    entry = _MEM_CACHE.get(key)
    if entry is None:
        return None
    ts, data = entry
    # Determine TTL from key prefix
    prefix = key.split(":")[0] if ":" in key else key
    ttl = CACHE_TTL.get(prefix, 60)
    if time.time() - ts > ttl:
        try:
            del _MEM_CACHE[key]
        except KeyError:
            pass
        return None
    return data

def _cache_set(key: str, data):
    _MEM_CACHE[key] = (time.time(), data)
    if len(_MEM_CACHE) > MAX_CACHE_SIZE:
        keys_to_delete = list(_MEM_CACHE.keys())[:100]
        for k in keys_to_delete:
            _MEM_CACHE.pop(k, None)

def _jsonify_cached(data, cache_seconds=60):
    """Return jsonify response with Cache-Control header."""
    resp = make_response(jsonify(data))
    resp.headers["Cache-Control"] = f"public, max-age={cache_seconds}"
    return resp

# Lazy init of institutional data fetcher (used for yfinance quote only)
_data_fetcher = None

def _get_data_fetcher():
    global _data_fetcher
    if _data_fetcher is None:
        try:
            from data_fetcher import InstitutionalDataFetcher
            _data_fetcher = InstitutionalDataFetcher()
        except Exception as e:
            logger.warning("Data fetcher init failed: %s", e)
    return _data_fetcher

# Static symbol list for search when no API key (top US symbols)
SEARCH_SYMBOLS = [
    ("AAPL", "Apple Inc"), ("MSFT", "Microsoft"), ("GOOGL", "Alphabet/Google"), ("AMZN", "Amazon"),
    ("NVDA", "NVIDIA"), ("META", "Meta Platforms"), ("TSLA", "Tesla"), ("BRK.B", "Berkshire Hathaway"),
    ("UNH", "UnitedHealth"), ("JNJ", "Johnson & Johnson"), ("V", "Visa"), ("JPM", "JPMorgan Chase"),
    ("WMT", "Walmart"), ("MA", "Mastercard"), ("PG", "Procter & Gamble"), ("HD", "Home Depot"),
    ("DIS", "Walt Disney"), ("BAC", "Bank of America"), ("ADBE", "Adobe"), ("NFLX", "Netflix"),
    ("CRM", "Salesforce"), ("PYPL", "PayPal"), ("INTC", "Intel"), ("CMCSA", "Comcast"),
    ("PEP", "PepsiCo"), ("TMO", "Thermo Fisher"), ("COST", "Costco"), ("AVGO", "Broadcom"),
    ("CSCO", "Cisco"), ("ABT", "Abbott"), ("XOM", "Exxon Mobil"), ("KO", "Coca-Cola"),
    ("NEE", "NextEra Energy"), ("MCD", "McDonald's"), ("DHR", "Danaher"), ("ABBV", "AbbVie"),
    ("TXN", "Texas Instruments"), ("ACN", "Accenture"), ("NKE", "Nike"), ("PM", "Philip Morris"),
    ("CVX", "Chevron"), ("LLY", "Eli Lilly"), ("HON", "Honeywell"), ("ORCL", "Oracle"),
    ("AMD", "AMD"), ("IBM", "IBM"), ("QCOM", "Qualcomm"), ("GE", "General Electric"),
    ("AMGN", "Amgen"), ("CAT", "Caterpillar"), ("AXP", "American Express"), ("LOW", "Lowe's"),
    ("SPY", "SPDR S&P 500"), ("QQQ", "Invesco QQQ"), ("GME", "GameStop"), ("AMC", "AMC Entertainment"),
    ("BA", "Boeing"), ("RTX", "Raytheon"), ("UPS", "United Parcel Service"), ("UNP", "Union Pacific"),
    ("SBUX", "Starbucks"), ("GS", "Goldman Sachs"), ("MS", "Morgan Stanley"), ("BLK", "BlackRock"),
    ("C", "Citigroup"), ("BRK-B", "Berkshire Hathaway"), ("PFE", "Pfizer")
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sentiment: keyword-based score 0–100 from headlines (0–30 bearish, 70–100 bullish)
SENTIMENT_POSITIVE = (
    "beat, beats, surge, rally, buy, upgrade, strong, growth, record, high, gain, approval, "
    "outperform, raised, beat expectations, bullish, recovery, breakthrough"
).replace(",", " ").split()
SENTIMENT_NEGATIVE = (
    "miss, cut, downgrade, fall, drop, weak, loss, layoff, probe, fraud, sell, "
    "bearish, lowered, miss expectations, decline, bankruptcy, lawsuit"
).replace(",", " ").split()


def _sentiment_from_headlines(headlines: list) -> int:
    """Score 0–100 from list of headline strings. 0–30 bearish, 70–100 bullish."""
    if not headlines:
        return 50
    text = " ".join((h if isinstance(h, str) else (h.get("title") or "")) for h in headlines).lower()
    pos = sum(1 for w in SENTIMENT_POSITIVE if w in text)
    neg = sum(1 for w in SENTIMENT_NEGATIVE if w in text)
    score = 50 + (pos - neg) * 8
    return max(0, min(100, score))

# Use absolute paths so the site works when run from any cwd
WEBAPP_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(WEBAPP_DIR / "static"), template_folder=str(WEBAPP_DIR / "templates"))
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key_change_in_prod")
if os.environ.get("FLASK_ENV") == "production" and app.secret_key == "dev_secret_key_change_in_prod":
    raise RuntimeError("Set FLASK_SECRET_KEY in production!")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Register modular route blueprints (auth, watchlist, ai)
from routes import register_blueprints
register_blueprints(app)

# In-memory cache for stocks (refresh via /api/refresh or on first load from report)
_stocks_cache = None
_stocks_updated_at = None
REPORTS_DIR = ROOT / "institutional_analyzer" / "reports"
if not REPORTS_DIR.exists():
    REPORTS_DIR = ROOT / "reports"


def _load_stocks_from_latest_report():
    """Load best stocks from latest buy_recommendations CSV in reports."""
    global _stocks_cache, _stocks_updated_at
    try:
        if not REPORTS_DIR.exists():
            return None
        csvs = list(REPORTS_DIR.glob("buy_recommendations_*.csv"))
        if not csvs:
            return None
        latest = max(csvs, key=lambda p: p.stat().st_mtime)
        import pandas as pd
        df = pd.read_csv(latest)
        # Normalize column names (Hebrew or English)
        col_map = {
            "מקום": "rank", "Rank": "rank",
            "סימבול": "symbol", "Symbol": "symbol",
            "ציון כולל": "rank_score", "Rank Score": "rank_score",
            "ציון ביטחון": "confidence", "Confidence": "confidence",
            "שינוי בהחזקה %": "position_change_pct", "Position Change %": "position_change_pct",
            "מספר מוסדות": "num_institutions", "Num Institutions": "num_institutions",
            "פוטנציאל עלייה %": "upside_pct", "Upside %": "upside_pct",
            "Breakout": "breakout",
            "רמת המלצה": "recommendation", "Recommendation": "recommendation",
            "מגמה": "trend", "Trend": "trend",
        }
        try:
            from trends import GLOBAL_TRENDS
            trend_he_to_en = {v["name_he"]: v["name_en"] for v in GLOBAL_TRENDS.values()}
        except Exception:
            trend_he_to_en = {}
        rec_he_to_en = {"🟢 חזק מאוד": "Strong buy", "🟢 חזק": "Buy", "🟡 טוב": "Consider", "🟠 מתון": "Moderate"}
        breakout_he_to_en = {"✅ כן": "Yes", "❌ לא": "No"}
        out = []
        for _, row in df.iterrows():
            item = {}
            for c in df.columns:
                key = col_map.get(c, c.replace(" ", "_").lower())
                if key:
                    val = row[c]
                    if hasattr(val, "item"):
                        val = val.item() if hasattr(val, "item") else val
                    if isinstance(val, str) and key == "recommendation":
                        val = rec_he_to_en.get(val, val)
                    if isinstance(val, str) and key == "breakout":
                        val = breakout_he_to_en.get(val, val)
                    if isinstance(val, str) and key == "trend":
                        val = trend_he_to_en.get(val, val)
                    item[key] = val
            if "symbol" not in item:
                for k, v in col_map.items():
                    if v == "symbol" and k in df.columns:
                        item["symbol"] = row[k]
                        break
            out.append(item)
        _stocks_cache = out
        _stocks_updated_at = datetime.now(timezone.utc)
        return out
    except Exception as e:
        logger.warning("Could not load report: %s", e)
        return None


def _run_analyzer():
    """Run institutional analyzer and return recommendations (can be slow)."""
    try:
        import config
        from analyzer import InstitutionalAnalyzer
        import pandas as pd
        analyzer = InstitutionalAnalyzer()
        recommendations = analyzer.analyze_institutions(config.MAJOR_INSTITUTIONS, use_cache=False)
        if recommendations is None or recommendations.empty:
            return _load_stocks_from_latest_report()
        # Build list from dataframe (use English columns from reporter if we add them)
        recs = recommendations.head(30)
        out = []
        for i, (_, row) in enumerate(recs.iterrows(), 1):
            out.append({
                "rank": i,
                "symbol": row.get("symbol", ""),
                "rank_score": round(float(row.get("rank_score", 0)), 3),
                "confidence": f"{row.get('confidence_score', row.get('rank_score', 0)):.1%}",
                "position_change_pct": f"{row.get('avg_change_percent', 0):.2f}%",
                "num_institutions": int(row.get("num_institutions", 0)),
                "upside_pct": f"{row.get('estimated_upside', 0):.1f}%" if row.get("estimated_upside") is not None else "N/A",
                "raw_upside": float(row.get("estimated_upside", 0)) if pd.notna(row.get("estimated_upside")) else 0,
                "price": float(row.get("current_price", 0)) if pd.notna(row.get("current_price")) else 0,
                "sector": row.get("sector") or "Unknown",
                "breakout": "Yes" if row.get("is_breakout") else "No",
                "recommendation": _recommendation_label(row),
                "trend": row.get("trend_name_en") or row.get("trend_name_he") or "—",
            })
        global _stocks_cache, _stocks_updated_at
        _stocks_cache = out
        _stocks_updated_at = datetime.now(timezone.utc)
        return out
    except Exception as e:
        logger.exception("Analyzer failed: %s", e)
        return _load_stocks_from_latest_report()


def _recommendation_label(row):
    from utils import get_recommendation_label
    return get_recommendation_label(row.get("confidence_score"), row.get("rank_score"))


@app.route("/")
def index():
    return send_from_directory(app.template_folder, "index.html")


@app.route("/api/stocks")
def api_stocks():
    """Return best stocks to buy today. Uses cache or latest report; ?refresh=1 runs analyzer."""
    global _stocks_cache, _stocks_updated_at
    if request.args.get("refresh"):
        data = _run_analyzer()
    else:
        data = _stocks_cache
        if data is None:
            data = _load_stocks_from_latest_report()
        # Never run heavy analyzer on first load — return empty so page loads fast; user can click Refresh
        if data is None:
            data = []
    if data is None:
        data = []
    return _jsonify_cached({
        "stocks": data,
        "updated_at": _stocks_updated_at.isoformat().replace("+00:00", "Z") if _stocks_updated_at else None,
        "count": len(data),
    }, cache_seconds=30)


def _get_dividend_picks():
    """
    Fetch top 25 dividend stocks using FMP (commercial API, no yfinance):
    1. Curated list of Top Dividend Stocks (Aristocrats, High Yielders).
    2. FMP quote + key-metrics-ttm for yield, PE, payout.
    3. FMP price-target-consensus for analyst targets.
    4. FMP grades for analyst firms.
    5. Rank by Upside Potential.
    """
    candidates = [
        "O", "MAIN", "SCHD", "JEPI", "VYM", "JNJ", "PG", "KO", "PEP", "ABBV",
        "CVX", "XOM", "T", "VZ", "MCD", "LOW", "HD", "TXN", "AVGO", "CSCO",
        "IBM", "MMM", "WBA", "FRT", "NNN", "OHI", "VICI", "MPW", "STAG", "AGNC",
        "MO", "PM", "BTI", "EPD", "ET", "KMI", "WPC", "ADC", "IRM", "DLR", "AMT", 
        "CCI", "PFE", "BMY", "GILD", "AMGN", "JPM", "BAC", "MS", "GS", "NEE", "DUK", "SO"
    ]
    
    valid_picks = []
    try:
        from concurrent.futures import ThreadPoolExecutor
        from fmp_client import quote as fmp_quote, price_target_consensus, key_metrics_ttm, grades as fmp_grades, profile as fmp_profile
        
        def process_ticker(sym):
            try:
                q = fmp_quote(sym)
                if not q or not q.get("price"):
                    return None
                price = q["price"]
                name = q.get("name") or sym
                
                # Key metrics for dividend data
                metrics = key_metrics_ttm(sym)
                yield_val = 0
                pe_ratio = None
                if metrics:
                    yield_val = metrics.get("dividend_yield") or 0
                    pe_ratio = metrics.get("pe_ratio")
                
                if yield_val < 1.5:  # Filter out < 1.5%
                    return None
                
                # Analyst target
                pt = price_target_consensus(sym)
                target_mean = pt.get("target_consensus") if pt else None
                if not target_mean:
                    target_mean = price
                
                upside_pct = ((target_mean - price) / price) * 100 if target_mean and price else 0
                
                # Analyst grades
                analyst_firms = []
                gr = fmp_grades(sym, limit=3)
                if gr:
                    analyst_firms = [g.get("grading_company", "") for g in gr if g.get("grading_company")]
                
                # Profile for sector
                prof = fmp_profile(sym)
                sector = (prof or {}).get("sector", "N/A") if prof else "N/A"
                
                firms_str = f" ({', '.join(analyst_firms[:3])})" if analyst_firms else ""
                thesis = (f"Analysts{firms_str} consensus target ${round(target_mean, 2)} "
                          f"({round(upside_pct, 1)}% upside). "
                          f"Yields {round(yield_val, 2)}%. Sector: {sector}.")

                return {
                    "symbol": sym,
                    "name": name,
                    "price": round(price, 2),
                    "dividend_yield": round(yield_val, 2),
                    "sector": sector,
                    "analyst_rating": "Buy",
                    "upside_pct": round(upside_pct, 1),
                    "target_price": round(target_mean, 2) if target_mean else None,
                    "thesis": thesis,
                    "logo_url": f"https://financialmodelingprep.com/image-stock/{sym}.png",
                    "analyst_firms": analyst_firms[:3],
                    "metrics": {
                        "pe": round(pe_ratio, 2) if pe_ratio else "N/A",
                        "eps": "N/A",
                        "payout": "N/A"
                    }
                }
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            for result in executor.map(process_ticker, candidates):
                if result:
                    valid_picks.append(result)
                
        # Rank by Upside
        valid_picks.sort(key=lambda x: x["upside_pct"], reverse=True)
        
        return valid_picks[:25]

    except Exception as e:
        logger.error("Dividend picks failed: %s", e)
        return []




@app.route("/api/dividend-picked")
def api_dividend_picks():
    """Return Top 25 Dividend Picks."""
    # check cache "dividend_picks"
    if not request.args.get("refresh"):
        cached = _cache_get("dividend_picks")
        if cached:
            return _jsonify_cached({"picks": cached}, cache_seconds=3600) # Cache for 1 hour

    picks = _get_dividend_picks()
    _cache_set("dividend_picks", picks)
    return _jsonify_cached({"picks": picks}, cache_seconds=3600)



@app.route("/api/sector-picks")
def api_sector_picks():
    """Return Top 10 Recommended Stocks by Sector.
    Uses FMP real Wall Street analyst consensus data:
    - /stable/quote for current price
    - /stable/price-target-consensus for analyst target prices
    - /stable/grades for latest analyst upgrade/downgrade actions
    """
    sector = request.args.get("sector", "Technology")
    cache_key = f"sector_picks:{sector}"
    if not request.args.get("refresh"):
        cached = _cache_get(cache_key)
        if cached:
            return _jsonify_cached({"picks": cached}, cache_seconds=3600)
    
    from db import get_sector_holdings
    holdings = get_sector_holdings(sector, limit=10)
    
    picks = []
    for h in holdings:
        if not h.get("price"):
            continue
            
        picks.append({
            "symbol": h["ticker"],
            "name": h["ticker"],
            "price": round(float(h["price"]), 2),
            "analyst_target": round(float(h["analyst_target"]), 2) if h.get("analyst_target") else None,
            "target_high": None,
            "target_low": None,
            "target_median": None,
            "upside_pct": round(float(h["upside_pct"]), 1) if h.get("upside_pct") else None,
            "latest_grade": None,
        })
    
    picks.sort(key=lambda x: x["upside_pct"] if x["upside_pct"] is not None else -999, reverse=True)

    if picks:
        _cache_set(cache_key, picks)
        return _jsonify_cached({"picks": picks}, cache_seconds=3600)
    else:
        return _jsonify_cached({"picks": []}, cache_seconds=10)


def _quote_polygon(symbol: str):
    """Real-time price from Polygon.io, fallback to FMP. No yfinance."""
    try:
        from polygon_client import quote as polygon_quote
        ans = polygon_quote(symbol)
        if ans and ans.get("price"):
            return ans
    except Exception as e:
        logger.warning("Polygon quote failed for %s: %s", symbol, e)
    # Fallback: FMP quote (commercial API, reliable)
    try:
        from fmp_client import quote as fmp_quote
        ans = fmp_quote(symbol)
        if ans and ans.get("price"):
            return ans
    except Exception as e:
        logger.warning("FMP quote fallback failed for %s: %s", symbol, e)
    return None


def _search_stocks(q):
    """Search: Polygon Reference (all tickers) first, then FMP tradable list, FMP search, Finnhub, static."""
    q = (q or "").strip()
    if not q or len(q) < 1:
        return []
    # 1) Polygon.io – Reference Data API (complete list of all available stock symbols)
    try:
        from polygon_client import search_tickers
        results = search_tickers(q, limit=50)
        if results:
            return results
    except Exception as e:
        logger.warning("Polygon search failed: %s", e)
    # 2) FMP – full tradable list filtered by query
    try:
        from fmp_client import search_tradable
        results = search_tradable(q, limit=50)
        if results:
            return results
    except Exception as e:
        logger.warning("FMP search_tradable failed: %s", e)
    # 3) FMP – legacy search endpoint
    try:
        from fmp_client import search as fmp_search
        results = fmp_search(q, limit=30)
        if results:
            return results
    except Exception as e:
        logger.warning("FMP search failed: %s", e)
    # 4) Finnhub
    finnhub_key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if finnhub_key:
        try:
            r = requests.get(
                "https://finnhub.io/api/v1/search",
                params={"q": q, "token": finnhub_key},
                timeout=8,
            )
            if r.ok:
                data = r.json()
                results = data.get("result") or []
                out = []
                seen = set()
                for item in results[:30]:
                    sym = (item.get("symbol") or "").strip()
                    if not sym or sym in seen:
                        continue
                    seen.add(sym)
                    desc = (item.get("description") or item.get("displaySymbol") or sym)
                    out.append({"symbol": sym, "name": desc, "type": item.get("type", "stock")})
                if out:
                    return out
        except Exception as e:
            logger.warning("Finnhub search failed: %s", e)
    # 3) Static list
    ql = q.lower()
    q_upper = q.upper()
    out = []
    for sym, name in SEARCH_SYMBOLS:
        if q_upper in sym or ql in name.lower():
            out.append({"symbol": sym, "name": name, "type": "stock"})
    return out[:30]


@app.route("/api/hot-stocks")
def api_hot_stocks():
    """
    Hot stocks: high momentum (volume breakout, significant % change). Excludes low-vol names.
    Merges FMP gainers + most_active; min |change %| filter. Cached 90s.
    Falls back to yfinance for a curated list of volatile/momentum tickers if FMP v3 is deprecated.
    """
    cache_key = "hot_stocks:all"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=90)
    min_change_pct = request.args.get("min_change", 2.0, type=float)
    limit = request.args.get("limit", 25, type=int)
    out = []
    seen = set()
    # Try FMP first
    try:
        from fmp_client import stock_market_gainers, stock_market_most_active
        for item in stock_market_gainers(limit=50) + stock_market_most_active(limit=50):
            sym = (item.get("symbol") or "").strip()
            if not sym or sym in seen:
                continue
            ch = item.get("change_percent") or 0
            if abs(ch) < min_change_pct:
                continue
            seen.add(sym)
            price = item.get("price")
            out.append({
                "symbol": sym,
                "name": item.get("name") or sym,
                "price": price,
                "change": item.get("change"),
                "change_percent": ch,
                "volume": item.get("volume"),
            })
            if len(out) >= limit:
                break
    except Exception as e:
        logger.warning("Hot stocks FMP failed: %s", e)
    result = {"hot_stocks": out, "count": len(out)}
    # Fallback: if FMP returned nothing, use FMP batch quote for momentum tickers
    if not out:
        try:
            from fmp_client import batch_quote
            momentum_syms = ["TSLA", "NVDA", "AMD", "META", "COIN", "PLTR", "SOFI",
                             "MARA", "RIOT", "SQ", "SHOP", "SNAP", "UBER", "RBLX",
                             "SMCI", "ARM", "MSTR", "NET", "DDOG", "CRWD"]
            quotes = batch_quote(momentum_syms)
            for q in quotes:
                ch = q.get("change_percent") or 0
                if abs(ch) >= min_change_pct:
                    out.append({
                        "symbol": q["symbol"],
                        "name": q.get("name") or q["symbol"],
                        "price": q["price"],
                        "change": q.get("change"),
                        "change_percent": ch,
                        "volume": q.get("volume", 0),
                    })
            out.sort(key=lambda x: abs(x.get("change_percent", 0)), reverse=True)
            out = out[:limit]
        except Exception as e:
            logger.warning("Hot stocks FMP batch fallback failed: %s", e)
        result = {"hot_stocks": out, "count": len(out)}
    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=90)


@app.route("/api/institutional-breakout")
def api_institutional_breakout():
    """
    Institutional Breakout: high momentum + net positive institutional inflow only.
    Cached 90s to avoid excessive 13F API calls.
    """
    cache_key = "breakout:all"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=90)
    min_change_pct = request.args.get("min_change", 2.0, type=float)
    limit = request.args.get("limit", 25, type=int)
    out = []
    seen = set()
    try:
        from fmp_client import (
            stock_market_gainers,
            stock_market_most_active,
            institutional_net_direction,
        )
        candidates = []
        for item in stock_market_gainers(limit=60) + stock_market_most_active(limit=60):
            sym = (item.get("symbol") or "").strip()
            if not sym or sym in seen:
                continue
            ch = item.get("change_percent") or 0
            if abs(ch) < min_change_pct:
                continue
            seen.add(sym)
            candidates.append({
                "symbol": sym,
                "name": item.get("name") or sym,
                "price": item.get("price"),
                "change_percent": ch,
                "change": item.get("change"),
                "volume": item.get("volume"),
            })
        # Check institutional direction — cached per-symbol in _api_cache
        for item in candidates:
            if len(out) >= limit:
                break
            sym = item["symbol"]
            dir_key = f"holders:{sym}:dir"
            direction = _cache_get(dir_key)
            if direction is None:
                direction = institutional_net_direction(sym)
                _cache_set(dir_key, direction)
            if direction == "sell":
                continue
            price = item.get("price")
            if price is None:
                try:
                    from fmp_client import quote as fmp_quote
                    q = fmp_quote(sym)
                    if q:
                        price = q.get("price")
                except Exception:
                    pass
            out.append({
                "symbol": sym,
                "name": item.get("name") or sym,
                "price": price,
                "change": item.get("change"),
                "change_percent": item.get("change_percent"),
                "volume": item.get("volume"),
                "institutional_flow": direction,
            })
    except Exception as e:
        logger.warning("Institutional breakout failed: %s", e)
    result = {
        "institutional_breakout": out,
        "count": len(out),
        "description": "High momentum + net positive institutional inflow (13F). Filtered out net sell.",
    }
    if out:
        _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=90)


@app.route("/api/search")
def api_search():
    """Search all stocks from API symbol list (full market). Query param: q."""
    q = request.args.get("q", "")
    results = _search_stocks(q)
    return _jsonify_cached({"results": results, "query": q}, cache_seconds=300)


# login_required decorator is now in routes/auth.py — import for use in remaining routes
from routes.auth import login_required




@app.route("/api/quote/<symbol>")
def api_quote(symbol):
    """Real-time quote: FMP first (most reliable), then Polygon, then yfinance."""
    sym = symbol.upper().strip()
    cache_key = f"quote:{sym}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=30)
    # FMP is primary — reliable and consistent
    try:
        from fmp_client import quote as fmp_quote
        q = fmp_quote(sym)
        if q:
            _cache_set(cache_key, q)
            return _jsonify_cached(q, cache_seconds=30)
    except Exception:
        pass
    # Polygon fallback
    quote_data = _quote_polygon(sym)
    if quote_data:
        _cache_set(cache_key, quote_data)
        return _jsonify_cached(quote_data, cache_seconds=30)
    # yfinance last resort
    fetcher = _get_data_fetcher()
    if fetcher:
        quote_data = fetcher.get_live_quote(sym)
        if quote_data:
            _cache_set(cache_key, quote_data)
            return _jsonify_cached(quote_data, cache_seconds=30)
    return jsonify({"error": "Symbol not found or no data"}), 404


def _get_full_stock_data(symbol: str):
    """
    Full stock detail: real-time quote (FMP → Polygon → yfinance), analyst (FMP),
    institutional holders ONLY from FMP (13F). No fake/simulated data.
    """
    sym = symbol.upper().strip()
    # Check full_stock cache first
    cache_key = f"full_stock:{sym}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    quote_data = None
    analyst = None
    holdings = []

    # 1) Real-time price: FMP first (most reliable), then Polygon, then yfinance
    try:
        from fmp_client import quote as fmp_quote, profile as fmp_profile
        q = fmp_quote(sym)
        if q:
            quote_data = {
                "symbol": q.get("symbol", sym),
                "name": q.get("name", sym),
                "price": q.get("price"),
                "change": q.get("change"),
                "change_percent": q.get("change_percent"),
                "volume": q.get("volume"),
                "market_cap": q.get("market_cap"),
            }
            prof = fmp_profile(sym)
            if prof:
                if quote_data.get("market_cap") is None:
                    quote_data["market_cap"] = prof.get("mktCap") or prof.get("marketCap")
                quote_data["beta"] = prof.get("beta")
                quote_data["eps"] = prof.get("eps") or prof.get("ttmEps")
                quote_data["sector"] = prof.get("sector")
                quote_data["industry"] = prof.get("industry")
                quote_data["description"] = prof.get("description")
    except Exception as e:
        logger.warning("FMP quote failed for %s: %s", sym, e)
    if quote_data is None:
        quote_data = _quote_polygon(sym)
        if quote_data:
            quote_data = {
                "symbol": quote_data.get("symbol", sym),
                "name": quote_data.get("name", sym),
                "price": quote_data.get("price"),
                "change": quote_data.get("change"),
                "change_percent": quote_data.get("change_percent"),
                "volume": quote_data.get("volume"),
                "market_cap": quote_data.get("market_cap"),
            }

    # Enrich missing fundamentals with FMP key-metrics-ttm (no yfinance)
    yf_data = {}
    if quote_data and (not quote_data.get("pe_ratio") or not quote_data.get("beta")):
        try:
            from fmp_client import key_metrics_ttm
            km = key_metrics_ttm(sym)
            if km:
                if not quote_data.get("beta"):
                    quote_data["beta"] = km.get("beta")
                if not quote_data.get("eps"):
                    quote_data["eps"] = km.get("eps")
                yf_data["pe_ratio"] = km.get("pe_ratio")
                yf_data["dividend_yield"] = km.get("dividend_yield")
                yf_data["payout_ratio"] = km.get("payout_ratio")
        except Exception as e:
            logger.warning("FMP key-metrics enrichment failed for %s: %s", sym, e)

    if quote_data is None:
        return None

    # 2) Parallelize ALL Data Fetching using ThreadPoolExecutor
    insider_list = []
    cluster_buys = False
    chart_price = []
    chart_institutional = []
    sentiment_score = 50
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from fmp_client import (
            institutional_holders, analyst_price_target, key_metrics_ttm, 
            price_target_consensus, analyst_recommendation, analyst_estimates, stock_news,
            insider_trading as fmp_insider, historical_daily, institutional_ownership_history
        )
        
        holders_key = f"holders:{sym}"
        analyst_key = f"analyst:{sym}"
        km_key = f"key_metrics:{sym}"
        pt_key = f"price_targets:{sym}"
        rec_key = f"recommendation:{sym}"
        est_key = f"estimates:{sym}"
        news_key = f"news:{sym}"
        
        holdings = _cache_get(holders_key)
        analyst = _cache_get(analyst_key)
        km = _cache_get(km_key)
        pt = _cache_get(pt_key)
        rec = _cache_get(rec_key)
        est = _cache_get(est_key)
        n = _cache_get(news_key)
        
        key_metrics = km or {}
        price_targets = pt or {}
        recommendation = rec or {}
        news = n or []
        estimates = []
        if est:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            estimates = [e for e in est if e.get("date", "") >= today][:8]

        # Chart date range
        from datetime import timedelta
        to_d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        from_d = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")

        with ThreadPoolExecutor(max_workers=11) as ex:
            futures = {}
            if holdings is None: futures[ex.submit(institutional_holders, sym)] = "holdings"
            if analyst is None: futures[ex.submit(analyst_price_target, sym)] = "analyst"
            if km is None: futures[ex.submit(key_metrics_ttm, sym)] = "km"
            if pt is None: futures[ex.submit(price_target_consensus, sym)] = "pt"
            if rec is None: futures[ex.submit(analyst_recommendation, sym)] = "rec"
            if est is None: futures[ex.submit(analyst_estimates, sym)] = "est"
            if n is None: futures[ex.submit(stock_news, 15, sym)] = "news"
            # Also fetch insider, chart, and institutional ownership in parallel
            futures[ex.submit(fmp_insider, sym, 20)] = "insider"
            futures[ex.submit(historical_daily, sym, from_d, to_d)] = "chart_price"
            futures[ex.submit(institutional_ownership_history, sym)] = "chart_inst"
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    res = future.result()
                    if name == "holdings":
                        holdings = res or []
                        if holdings: _cache_set(holders_key, holdings)
                    elif name == "analyst":
                        analyst = res
                        if analyst: _cache_set(analyst_key, analyst)
                    elif name == "km":
                        if res: 
                            key_metrics = res
                            _cache_set(km_key, res)
                    elif name == "pt":
                        if res: 
                            price_targets = res
                            _cache_set(pt_key, res)
                    elif name == "rec":
                        if res: 
                            recommendation = res
                            _cache_set(rec_key, res)
                    elif name == "est":
                        if res:
                            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                            estimates = [e for e in res if e.get("date", "") >= today][:8]
                            _cache_set(est_key, res)
                    elif name == "news":
                        if res:
                            news = res[:15]
                            _cache_set(news_key, res[:15])
                    elif name == "insider":
                        if res:
                            insider_list = res
                            buys = [x for x in insider_list if x.get("is_buy")]
                            if len(buys) >= 2:
                                cluster_buys = True
                    elif name == "chart_price":
                        if res:
                            chart_price = res
                    elif name == "chart_inst":
                        if res:
                            chart_institutional = res
                except Exception as exc:
                    logger.warning("FMP %s failed for %s: %s", name, sym, exc)
    except Exception as e:
        logger.warning("Parallel FMP calls setup failed for %s: %s", sym, e)
        
    # Fill analyst from YF if missing
    if not analyst and yf_data.get("analyst"):
        analyst = yf_data["analyst"]
        
    # Fill key_metrics from YF if missing
    if not key_metrics and yf_data:
        if yf_data.get("pe_ratio"):
            key_metrics["pe_ratio"] = yf_data["pe_ratio"]
        if yf_data.get("dividend_yield"):
            key_metrics["dividend_yield"] = yf_data["dividend_yield"]
    
    if yf_data and yf_data.get("payout_ratio") is not None:
        key_metrics["payout_ratio"] = yf_data["payout_ratio"]

    # Fill targets/rec from YF if missing
    if not price_targets and yf_data.get("price_targets"):
        price_targets = yf_data["price_targets"]
    if not recommendation and yf_data.get("recommendation"):
        recommendation = yf_data["recommendation"]
    # NO fallback to data_fetcher.get_holdings_for_stock() — that generates fake data
    # Normalize holdings for response (position_change: Add/Reduce; never leave empty)
    current_price = quote_data.get("price") if quote_data else None
    out_holdings = []
    for h in holdings:
        pc = h.get("position_change")
        if pc is None:
            pc = "—"
        elif isinstance(pc, (int, float)):
            pc = f"+{pc:.1f}%" if pc >= 0 else f"{pc:.1f}%"
        elif isinstance(pc, str) and not pc.strip():
            pc = "—"
        else:
            pc = str(pc).strip()
        avg = h.get("avg_price")
        # Sanity: if avg_price is absurd vs current price (e.g. 10x+), use current price for display only
        if current_price and current_price > 0 and avg is not None:
            if avg <= 0 or avg > current_price * 50:
                avg = round(float(current_price), 2)
        out_holdings.append({
            "institution": h.get("institution") or "",
            "shares": h.get("shares"),
            "value": h.get("value"),
            "date_reported": h.get("date_reported") or "",
            "position_change": pc,
            "avg_price": avg,
        })
    # Analyst: upside/downside % from current price
    if analyst and current_price and current_price > 0:
        target = analyst.get("avg_price_target")
        if target is not None:
            analyst["upside_percent"] = round((float(target) - current_price) / current_price * 100, 2)
            analyst["downside_percent"] = -analyst["upside_percent"] if analyst["upside_percent"] < 0 else None
    # Institutional avg: only from avg_prices in reasonable range (0.1x–10x current price)
    valid_avgs = [x["avg_price"] for x in out_holdings if x.get("avg_price") is not None and x["avg_price"] > 0]
    if current_price and current_price > 0:
        valid_avgs = [a for a in valid_avgs if 0.1 * current_price <= a <= 10 * current_price]
    if not valid_avgs and current_price:
        valid_avgs = [current_price]
    inst_avg = round(sum(valid_avgs) / len(valid_avgs), 2) if valid_avgs else (round(current_price, 2) if current_price else None)
    total_val = sum(x.get("value") or 0 for x in out_holdings)

    # Bottom Line: Verdict, Why, EOY Target
    upside = analyst.get("upside_percent") if analyst else None
    eoy_target = analyst.get("avg_price_target") if analyst else None
    if upside is not None:
        if upside >= 10:
            verdict = "Buy"
        elif upside <= -10:
            verdict = "Sell"
        else:
            verdict = "Hold"
    else:
        verdict = "Hold"
    why_parts = []
    if out_holdings:
        adds = sum(1 for h in out_holdings if h.get("position_change") and ("+" in str(h.get("position_change")) or "Added" in str(h.get("position_change"))))
        if adds > len(out_holdings) / 2:
            why_parts.append("Institutional accumulation is high.")
        elif adds < len(out_holdings) / 3:
            why_parts.append("Institutions have been reducing exposure.")
    if analyst and eoy_target is not None and current_price:
        why_parts.append("Analyst 12-month target ${:.2f} ({:+.1f}% {}).".format(
            eoy_target, upside, "upside" if upside >= 0 else "downside"))
    bottom_line = {
        "verdict": verdict,
        "why": " ".join(why_parts) if why_parts else "Insufficient data for summary.",
        "eoy_target": eoy_target,
        "eoy_upside_percent": upside,
    }

    # Sentiment 0–100 from news titles (already fetched above in parallel)
    titles = [n_item.get("title") or "" for n_item in news if n_item.get("title")]
    if titles:
        sentiment_score = _sentiment_from_headlines(titles[:10])

    result = {
        "symbol": sym,
        "quote": quote_data,
        "analyst": analyst,
        "key_metrics": key_metrics,
        "price_targets": price_targets,
        "recommendation": recommendation,
        "estimates": estimates,
        "holdings": out_holdings,
        "institutional_avg_price": inst_avg,
        "total_institutional_value": round(total_val, 2),
        "num_institutions": len(out_holdings),
        "bottom_line": bottom_line,
        "insider": insider_list,
        "insider_cluster_buys": cluster_buys,
        "chart_price": chart_price,
        "chart_institutional": chart_institutional,
        "sentiment": sentiment_score,
        "news": news,
    }
    _cache_set(cache_key, result)
    return result


@app.route("/api/stock/<symbol>/full")
def api_stock_full(symbol):
    """Full stock detail: quote, analyst consensus, institutional holders (13F)."""
    data = _get_full_stock_data(symbol)
    if data is None:
        return jsonify({"error": "Symbol not found or no data"}), 404
    return jsonify(data)


@app.route("/api/stock/<symbol>/chart")
def api_stock_chart(symbol):
    """Price chart data with timeframe support: 1D, 1W, 1M, 3M, YTD, 1Y, 5Y."""
    from fmp_client import historical_daily
    sym = symbol.upper().strip()
    range_param = request.args.get("range", "1Y").upper()
    cache_key = f"chart:{sym}:{range_param}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=300)
    now = datetime.now(timezone.utc)
    to_d = now.strftime("%Y-%m-%d")
    range_map = {
        "1D": timedelta(days=5),       # 5 trading days to ensure data
        "1W": timedelta(weeks=1),
        "1M": timedelta(days=30),
        "3M": timedelta(days=90),
        "YTD": None,                    # special
        "1Y": timedelta(days=365),
        "5Y": timedelta(days=365 * 5),
    }
    
    chart_data = None
    if range_param != "1D":
        if range_param == "YTD":
            from_d = f"{now.year}-01-01"
        else:
            delta = range_map.get(range_param, timedelta(days=365))
            from_d = (now - delta).strftime("%Y-%m-%d")
        chart_data = historical_daily(sym, from_d, to_d)

    # Chart data comes from FMP historical_daily only (no yfinance fallback)
    if not chart_data:
        chart_data = []  # Return empty if FMP has no data
    
    # For 1D, only return most recent trading day
    if range_param == "1D" and chart_data:
        last_day_prefix = chart_data[-1].get("date", "")[:10]  # Extracts YYYY-MM-DD
        chart_data = [d for d in chart_data if d.get("date", "").startswith(last_day_prefix)]
        if not chart_data:
            chart_data = [chart_data[-1]] if chart_data else []
    result = {"symbol": sym, "range": range_param, "data": chart_data}
    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=300)


# ---------------------------------------------------------------------------
# Finnhub Live Stock Intelligence
# ---------------------------------------------------------------------------
@app.route("/api/stock/<symbol>/live-quote")
def api_stock_live_quote(symbol):
    """Real-time stock quote from Finnhub (10s cache for rapid polling)."""
    sym = symbol.upper().strip()
    cache_key = f"live_quote:{sym}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=10)

    from finnhub_service import get_realtime_quote
    quote = get_realtime_quote(sym)
    if not quote:
        return jsonify({"error": "Quote not available", "symbol": sym}), 404

    _cache_set(cache_key, quote)
    return _jsonify_cached(quote, cache_seconds=10)


@app.route("/api/stock/<symbol>/live-chart")
def api_stock_live_chart(symbol):
    """Intraday 5-min candles — Finnhub with yfinance fallback."""
    sym = symbol.upper().strip()
    resolution = request.args.get("resolution", "5")
    cache_key = f"live_chart:{sym}:{resolution}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=60)

    candles = []

    # Try Finnhub first
    try:
        from finnhub_service import get_intraday_candles
        candles = get_intraday_candles(sym, resolution=resolution)
    except Exception as e:
        logger.warning("Finnhub candles failed for %s: %s", sym, e)

    # FMP intraday fallback (no yfinance)
    if not candles:
        try:
            from fmp_client import _get
            data = _get("historical-chart/5min", {"symbol": sym})
            if data and isinstance(data, list):
                for item in data[:78]:  # ~6.5 hours of 5-min candles
                    candles.append({
                        "time": item.get("date", "")[-8:-3] if item.get("date") else "",
                        "time_full": item.get("date", ""),
                        "open": round(float(item.get("open", 0)), 2),
                        "high": round(float(item.get("high", 0)), 2),
                        "low": round(float(item.get("low", 0)), 2),
                        "close": round(float(item.get("close", 0)), 2),
                        "volume": int(item.get("volume", 0)),
                    })
                candles.reverse()  # FMP returns newest first
        except Exception as e:
            logger.warning("FMP intraday fallback failed for %s: %s", sym, e)

    result = {"symbol": sym, "resolution": resolution, "candles": candles, "count": len(candles)}
    if candles:
        _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=60)


@app.route("/api/stock/<symbol>/news-ai")
def api_stock_news_ai(symbol):
    """Company-specific news from Finnhub + AI buy/sell verdict."""
    sym = symbol.upper().strip()
    cache_key = f"news_ai:{sym}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=300)

    from finnhub_service import get_company_news, generate_news_verdict, get_realtime_quote

    # Fetch news
    news = get_company_news(sym, days=7, limit=15)

    # Get current price for context
    quote = get_realtime_quote(sym)
    price = quote["price"] if quote else None

    # Generate AI verdict
    verdict = None
    if news:
        verdict = generate_news_verdict(sym, news, current_price=price)

    result = {
        "symbol": sym,
        "news": news,
        "news_count": len(news),
        "verdict": verdict,
        "current_price": price,
    }
    if news:
        _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=300)


@app.route("/api/stock/<symbol>/holdings")
def api_stock_holdings(symbol):
    """
    Institutional holdings for a stock: big corps, position change %, avg price per holder.
    Returns aggregate average price (value-weighted) across institutions.
    """
    data = _get_full_stock_data(symbol)
    if data is None:
        return jsonify({"error": "Symbol not found"}), 404
    return jsonify({
        "symbol": data["symbol"],
        "quote": data["quote"],
        "holdings": data["holdings"],
        "institutional_avg_price": data.get("institutional_avg_price"),
        "institutional_weighted_avg_price": data.get("institutional_avg_price"),
        "total_institutional_value": data.get("total_institutional_value"),
        "num_institutions": data.get("num_institutions"),
    })


@app.route("/api/whale-portfolio/<ticker>")
def api_whale_portfolio(ticker):
    """Whale Tracker / Big Tech Portfolios endpoint."""
    from whale_data import WHALE_PORTFOLIOS
    from fmp_client import quote as fmp_quote
    
    ticker = ticker.upper()
    if ticker not in WHALE_PORTFOLIOS:
        return jsonify({"error": "Whale portfolio not found"}), 404
        
    cache_key = f"whale_portfolio:{ticker}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=300)
        
    whale = WHALE_PORTFOLIOS[ticker]
    enriched_holdings = []
    total_value = 0
    
    for h in whale["holdings"]:
        sym = h["symbol"]
        shares = h["shares"]
        avg_price = h["avg_buy_price"]
        is_new = h.get("is_new", False)
        shares_change_pct = h.get("shares_change_pct")
        
        q = fmp_quote(sym)
        
        if q and q.get("price"):
            current_price = q["price"]
            change = q.get("change", 0)
            change_pct = q.get("change_percent", 0)
        else:
            current_price = avg_price
            change = 0
            change_pct = 0
            
        position_value = shares * current_price
        total_value += position_value
        
        profit_loss = position_value - (shares * avg_price)
        profit_loss_pct = ((current_price - avg_price) / avg_price * 100) if avg_price else 0
        
        enriched_holdings.append({
            "symbol": sym,
            "shares": shares,
            "avg_buy_price": avg_price,
            "current_price": current_price,
            "day_change": change,
            "day_change_percent": change_pct,
            "position_value": position_value,
            "profit_loss": round(profit_loss, 2),
            "profit_loss_percent": round(profit_loss_pct, 2),
            "is_new": is_new,
            "shares_change_pct": shares_change_pct
        })
        
    for h in enriched_holdings:
        h["weight_percent"] = round((h["position_value"] / total_value * 100), 2) if total_value > 0 else 0
        
    enriched_holdings.sort(key=lambda x: x["weight_percent"], reverse=True)
        
    result = {
        "ticker": ticker,
        "name": whale["name"],
        "manager": whale["manager"],
        "description": whale["description"],
        "total_value": round(total_value, 2),
        "holdings": enriched_holdings
    }
    
    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=300)


@app.route("/api/whale-top-picks")
def api_whale_top_picks():
    """Returns top 10 holdings aggregated from all whale portfolios."""
    from whale_data import WHALE_PORTFOLIOS
    from fmp_client import quote as fmp_quote
    
    cache_key = "whale_top_picks"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=300)
        
    all_holdings = {}
    for whale_ticker, data in WHALE_PORTFOLIOS.items():
        for h in data["holdings"]:
            sym = h["symbol"]
            val = h["shares"] * h["avg_buy_price"]
            if sym not in all_holdings:
                all_holdings[sym] = {"symbol": sym, "total_value": 0, "whales": []}
            all_holdings[sym]["total_value"] += val
            all_holdings[sym]["whales"].append(whale_ticker)
            
    # Sort by total value
    sorted_holdings = sorted(all_holdings.values(), key=lambda x: x["total_value"], reverse=True)[:10]
    
    # Enrich with live data
    for h in sorted_holdings:
        q = fmp_quote(h["symbol"])
        if q and q.get("price"):
            h["price"] = q["price"]
            h["change_percent"] = q.get("change_percent", 0)
            h["name"] = q.get("name", h["symbol"])
        else:
            h["price"] = 0
            h["change_percent"] = 0
            h["name"] = h["symbol"]
            
    result = {"picks": sorted_holdings}
    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=300)

@app.route("/api/market-indices")
def api_market_indices():
    """S&P 500, NASDAQ, DOW Jones mini tickers for header bar. Cached 30s."""
    import math
    def _safe_num(v):
        """Return None if value is NaN/Inf, otherwise return value."""
        if v is None:
            return None
        try:
            if math.isnan(v) or math.isinf(v):
                return None
        except (TypeError, ValueError):
            return None
        return v

    cache_key = "market_indices:all"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=30)
    indices = []
    etf_map = {"SPY": "S&P 500", "QQQ": "NASDAQ", "DIA": "DOW"}
    # 1) Instant read from Decoupled DB
    try:
        from db import get_stock_prices
        db_quotes = get_stock_prices(["SPY", "QQQ", "DIA"])
        for sym in ["SPY", "QQQ", "DIA"]:
            q = db_quotes.get(sym)
            if q:
                indices.append({
                    "symbol": sym,
                    "name": etf_map[sym],
                    "price": _safe_num(q.get("price")),
                    "change": _safe_num(q.get("change")),
                    "change_percent": _safe_num(q.get("change_percent")),
                })
    except Exception as e:
        logger.warning("Market indices DB failed: %s", e)
    result = {"indices": indices}
    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=30)


@app.route("/api/batch-quotes")
def api_batch_quotes():
    """Batch quote endpoint: returns live price + daily change % for multiple symbols.
    Used by the frontend to power the live 'Daily %' column on consensus picks.
    Query param: symbols (comma-separated, e.g. ?symbols=AAPL,MSFT,NVDA)
    Primary: FMP batch quote (single API call). Fallback: Polygon, then yfinance.
    """
    symbols_str = request.args.get("symbols", "")
    if not symbols_str:
        return jsonify({"quotes": []}), 200
    symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
    if not symbols:
        return jsonify({"quotes": []}), 200
    # Limit to 50 symbols max to avoid abuse
    symbols = symbols[:50]

    # Check cache
    cache_key = f"batch_quotes:{','.join(sorted(symbols))}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=30)

    quotes = []  # FIX: was missing — caused NameError

    # 1) Instant read from Decoupled DB
    try:
        from db import get_stock_prices
        db_quotes = get_stock_prices(symbols)
        for sym in symbols:
            q = db_quotes.get(sym)
            if q and q.get("price"):
                quotes.append({
                    "symbol": sym,
                    "price": q.get("price"),
                    "change": q.get("change"),
                    "change_percent": q.get("change_percent"),
                })
    except Exception as e:
        logger.warning("DB batch quotes failed: %s", e)

    result = {"quotes": quotes}
    if quotes:
        _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=30)

# ═══════════════════════════════════════════════════════════════════════════════
#  INSTITUTIONAL PORTFOLIO ENDPOINTS (SEC EDGAR 13F)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/institutions")
def api_institutions():
    """List all 12 tracked institutions with portfolio summaries. Reads from DB first."""
    cache_key = "institutions:all"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=3600)

    # Try DB cache first (pre-computed by cache_job)
    try:
        from db import get_cache
        db_cached = get_cache("institution_summaries")
        if db_cached and db_cached.get("count", 0) > 0:
            _cache_set(cache_key, db_cached)
            return _jsonify_cached(db_cached, cache_seconds=3600)
    except Exception as e:
        logger.warning("DB cache institution_summaries read failed: %s", e)

    # Fallback: live DB query
    try:
        if has_data():
            summaries = get_all_institution_summaries()
            if summaries:
                result = {"institutions": summaries, "count": len(summaries)}
                # Only cache if we have a reasonable number of institutions
                # (avoids caching partial data during cache job warm-up)
                from edgar_13f import INSTITUTIONS
                if len(summaries) >= len(INSTITUTIONS) * 0.8:
                    _cache_set(cache_key, result)
                return _jsonify_cached(result, cache_seconds=60)
    except Exception as e:
        logger.warning("DB institutions read failed: %s", e)

    # Fallback to live EDGAR
    try:
        from edgar_13f import get_institutions_summary
        summaries = get_institutions_summary()
        result = {"institutions": summaries, "count": len(summaries)}
        _cache_set(cache_key, result)
        return _jsonify_cached(result, cache_seconds=3600)
    except Exception as e:
        logger.error("Institutions endpoint failed: %s", e)
        return _jsonify_cached({"institutions": [], "count": 0, "error": str(e)}, cache_seconds=30)


@app.route("/api/institution/<cik>")
def api_institution_detail(cik):
    """Full portfolio for one institution by CIK, with QoQ change. Cached 6h."""
    cache_key = f"institution:{cik}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=21600)
    # Try DB first (has QoQ change data)
    try:
        from db import get_institution_holdings_with_change
        result = get_institution_holdings_with_change(cik)
        if result and result.get("holdings"):
            _cache_set(cache_key, result)
            return _jsonify_cached(result, cache_seconds=21600)
    except Exception as e:
        logger.warning("DB institution detail failed for %s: %s", cik, e)
    # Fallback to live EDGAR
    try:
        from edgar_13f import fetch_13f_holdings
        result = fetch_13f_holdings(cik, max_holdings=5000)
        if not result:
            return _jsonify_cached({"error": "Institution not found"}, cache_seconds=60), 404
        _cache_set(cache_key, result)
        return _jsonify_cached(result, cache_seconds=21600)
    except Exception as e:
        logger.error("Institution detail failed for %s: %s", cik, e)
        return _jsonify_cached({"error": str(e)}, cache_seconds=30), 500


@app.route("/api/top-picks")
def api_top_picks():
    """
    Consensus top 25 stocks: cross-referenced across all 12 institutions.
    Now reads from DB with QoQ institutional change data. Cached 1h.
    """
    cache_key = "top_picks:consensus"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=3600)

    n = request.args.get("limit", 25, type=int)

    # Try DB first (instant, has QoQ change data)
    result = None
    try:
        if has_data():
            result = get_consensus_with_change(n=min(n, 50))
    except Exception as e:
        logger.warning("DB consensus failed: %s", e)

    # Fallback to live EDGAR (no QoQ change in this path)
    if not result or not result.get("picks"):
        try:
            from edgar_13f import build_consensus_picks
            result = build_consensus_picks(n=min(n, 50))
        except Exception as e:
            logger.error("Top picks failed: %s", e)
            return _jsonify_cached({"picks": [], "error": str(e)}, cache_seconds=30)

    # Enrich with prices from DB (instant — no API calls on page load)
    try:
        from db import get_stock_prices
        tickers = [p.get("ticker", "") for p in result.get("picks", []) if p.get("ticker")]
        db_prices = get_stock_prices(tickers) if tickers else {}
    except Exception:
        db_prices = {}

    for pick in result.get("picks", []):
        ticker = pick.get("ticker", "")
        if not ticker:
            continue
        q = db_prices.get(ticker)
        if q:
            pick["price"] = q.get("price")
            pick["change"] = q.get("change")
            pick["change_percent"] = q.get("change_percent")
            pick["market_cap"] = q.get("market_cap")
            pick["name"] = q.get("name") or pick.get("issuer", ticker)
            if q.get("analyst_target") and q.get("price") and q["price"] > 0:
                pick["analyst_target"] = q["analyst_target"]
                pick["upside_pct"] = q.get("upside_pct") or round(
                    (q["analyst_target"] - q["price"]) / q["price"] * 100, 1
                )

    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=3600)


@app.route("/api/stock/<symbol>/holders")
def api_stock_holders(symbol):
    """
    All institutional holders for a stock: who holds it, how many shares,
    position value. Cached 1h.
    """
    cache_key = f"holders:{symbol.upper()}"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=3600)
    try:
        from edgar_13f import get_stock_holders
        result = get_stock_holders(symbol)

        # Enrich with upside
        try:
            from fmp_client import quote as fmp_quote, analyst_price_target
            q = fmp_quote(symbol.upper())
            if q:
                result["price"] = q.get("price")
                result["change_percent"] = q.get("change_percent")
            target = analyst_price_target(symbol.upper())
            if target and result.get("price"):
                result["analyst_target"] = target.get("avg_price_target")
                if target.get("avg_price_target"):
                    result["upside_pct"] = round(
                        (target["avg_price_target"] - result["price"]) / result["price"] * 100, 1
                    )
        except Exception:
            pass

        _cache_set(cache_key, result)
        return _jsonify_cached(result, cache_seconds=3600)
    except Exception as e:
        logger.error("Stock holders failed for %s: %s", symbol, e)
        return _jsonify_cached({"error": str(e)}, cache_seconds=30), 500


@app.route("/api/breaking-news")
def api_breaking_news():
    """
    Breaking news with SELL alerts. Fetches news, runs sentiment analysis,
    and flags significantly negative items with SELL!!! alert.
    """
    cache_key = "breaking_news:live"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=60)

    data = get_news_and_advice(limit_news=25)
    news_items = data.get("news", [])

    enhanced = []
    for item in news_items:
        title = item.get("title", "")
        headline_lower = title.lower()

        # Sentiment scoring
        pos = sum(1 for w in SENTIMENT_POSITIVE if w in headline_lower)
        neg = sum(1 for w in SENTIMENT_NEGATIVE if w in headline_lower)
        total = pos + neg or 1
        sentiment = int(50 + (pos - neg) / total * 50)
        sentiment = max(0, min(100, sentiment))

        alert = None
        if sentiment <= 20:
            alert = "SELL!!!"
        elif sentiment <= 35:
            alert = "CAUTION"
        elif sentiment >= 75:
            alert = "BULLISH"

        enhanced.append({
            "title": title,
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "date": item.get("date", ""),
            "sentiment": sentiment,
            "alert": alert,
        })

    result = {"news": enhanced, "count": len(enhanced)}
    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=60)


@app.route("/api/big-money-movers")
def api_big_money_movers():
    """
    Big Money Movers: stocks where any institution increased position >30%
    AND position value > $10M. The "Hot Stock" algorithm from 13F data.
    """
    cache_key = "big_money_movers:all"
    cached = _cache_get(cache_key)
    if cached:
        return _jsonify_cached(cached, cache_seconds=3600)

    min_change = request.args.get("min_change", 30.0, type=float)
    min_value = request.args.get("min_value", 10_000_000, type=int)
    limit = request.args.get("limit", 25, type=int)

    result = None
    try:
        if has_data():
            result = get_big_money_movers(
                min_change_pct=min_change,
                min_value=min_value,
                limit=limit,
            )
    except Exception as e:
        logger.warning("DB big money movers failed: %s", e)

    if not result:
        result = {"movers": [], "count": 0}

    # Enrich movers with prices from DB (instant — no API calls)
    try:
        from db import get_stock_prices
        mover_tickers = [m.get("ticker", "") for m in result.get("movers", []) if m.get("ticker")]
        db_prices = get_stock_prices(mover_tickers) if mover_tickers else {}
    except Exception:
        db_prices = {}

    for mover in result.get("movers", []):
        ticker = mover.get("ticker", "")
        if not ticker:
            continue
        q = db_prices.get(ticker)
        if q:
            mover["price"] = q.get("price")
            mover["name"] = q.get("name") or mover.get("issuer", ticker)
            mover["daily_change_pct"] = q.get("change_percent")

    _cache_set(cache_key, result)
    return _jsonify_cached(result, cache_seconds=3600)


@app.route("/sector/<sector_name>")
def sector_page(sector_name):
    """Dynamic Sector Detail Page."""
    import urllib.parse
    return render_template("sector_detail.html", sector_name=urllib.parse.unquote(sector_name))

@app.route("/stock/<symbol>")
def stock_detail_page(symbol):
    """Dynamic Stock Detail Page: /stock/[symbol]."""
    return render_template("stock_detail.html", symbol=symbol.upper().strip())

@app.route("/category/dividend-picks")
def category_dividend_picks():
    return render_template("dividend_picks.html")

@app.route("/category/big-money-movers")
def category_big_money_movers():
    return render_template("big_money_movers.html")

@app.route("/category/hot-stocks")
def category_hot_stocks():
    return render_template("hot_stocks.html")

@app.route("/category/big-tech-portfolios")
def category_big_tech_portfolios():
    return render_template("big_tech.html")

@app.route("/category/allocator")
def category_allocator():
    return render_template("allocator.html")

@app.route("/learn")
def learn_page():
    return render_template("learn.html")

@app.route("/news")
def news_hub_page():
    return render_template("news_hub.html")

@app.route("/learn/<chapter>")
def learn_chapter(chapter):
    return render_template("learn.html", chapter=chapter)



# (logging already imported at top)

def enrich_picks_with_prices(picks):
    """
    Fetch real prices for each pick.
    Uses FMP only (commercial API). No yfinance.
    """
    enriched = []
    for pick in picks[:30]:
        ticker = (pick.get('ticker') or pick.get('symbol') or '').upper().strip()
        if not ticker:
            continue
        
        price       = None
        name        = ticker
        sector      = pick.get('sector') or 'N/A'
        change_pct  = 0
        upside_pct  = pick.get('upside_pct') or 0
        num_inst    = pick.get('num_institutions') or pick.get('num_inst') or 0
        
        # Check DB cache first
        try:
            from db import get_stock_prices
            db_prices = get_stock_prices([ticker])
            if db_prices and db_prices.get(ticker):
                q = db_prices[ticker]
                if q.get('price') and float(q['price']) > 0:
                    price      = float(q['price'])
                    name       = q.get('name') or ticker
                    change_pct = float(q.get('change_percent') or 0)
        except Exception as e:
            logging.warning(f'DB price cache failed for {ticker}: {e}')

        # FMP quote (reliable commercial API) - only if cache miss
        if price is None:
            try:
                from fmp_client import quote as fmp_quote
                q = fmp_quote(ticker)
                if q and q.get('price') and float(q['price']) > 0:
                    price      = float(q['price'])
                    name       = q.get('name') or q.get('companyName') or ticker
                    change_pct = float(q.get('change_percent') or q.get('changesPercentage') or 0)
                    sector     = q.get('sector') or sector
            except Exception as e:
                logging.warning(f'FMP quote failed for {ticker}: {e}')
        
        # ── If still no price — skip this pick entirely ────────────────
        if not price or price <= 0:
            logging.warning(f'Could not get price for {ticker} — skipping')
            continue
        
        # ── Also fetch analyst upside if missing ───────────────────────
        if not upside_pct:
            try:
                from fmp_client import analyst_consensus
                ac = analyst_consensus(ticker)
                if ac:
                    target = float(ac.get('priceTarget') or ac.get('targetPrice') or 0)
                    if target > 0 and price > 0:
                        upside_pct = round(((target - price) / price) * 100, 1)
            except Exception:
                pass
        
        pick.update({
            'ticker':         ticker,
            'symbol':         ticker,
            'name':           name,
            'price':          round(price, 2),
            'sector':         sector,
            'change_percent': round(change_pct, 2),
            'upside_pct':     upside_pct,
            'num_institutions': num_inst,
        })
        enriched.append(pick)
    
    return enriched

def _smart_allocate(picks, amount, risk, horizon='1y', goal='growth'):
    """
    Conviction-weighted fallback allocator. Outputs the same per-stock fields
    as the AI generator so the frontend renders identically.
    """
    # How many stocks to pick based on risk profile
    target_count = {'conservative': 6, 'moderate': 7, 'aggressive': 8}.get(risk, 7)
    max_w    = {'conservative': 0.15, 'moderate': 0.25, 'aggressive': 0.40}.get(risk, 0.25)
    cash_pct = {'conservative': 0.15, 'moderate': 0.10, 'aggressive': 0.05}.get(risk, 0.10)
    investable = amount * (1 - cash_pct)
    
    # ── Score each stock with AGGRESSIVE differentiation ──────────────
    import hashlib, random
    for i, p in enumerate(picks):
        institutions  = float(p.get('num_institutions') or 0)
        upside        = float(str(p.get('upside_pct') or 0).replace('%','') or 0)
        change_today  = float(p.get('change_percent') or 0)
        price         = float(p.get('price') or 100)
        ticker        = p.get('ticker') or p.get('symbol') or ''
        
        # Multi-factor conviction with dramatic differentiation
        # Factor 1: Institutional backing (0-10 range, boost high counts)  
        inst_score = min(institutions * 1.5, 15)
        
        # Factor 2: Analyst upside (bigger upside = exponentially more weight)
        upside_score = max(upside, 0) ** 1.4
        
        # Factor 3: Price-based market cap proxy (higher price = typically bigger company)
        # This creates big differentiation: $500 stock vs $50 stock
        cap_score = (price ** 0.5) / 3  # sqrt scales nicely: $100→3.3, $500→7.4, $1000→10.5
        
        # Factor 4: Today's change (slight dip buying bonus)
        dip_bonus = 1.0
        if change_today < -3 and upside > 10:
            dip_bonus = 1.5
        elif change_today < -1 and upside > 5:
            dip_bonus = 1.2
        
        # Hash-based jitter so same picks produce different weights on retry
        seed = hashlib.md5(f"{ticker}{amount}{risk}{horizon}".encode()).hexdigest()
        jitter = 0.7 + (int(seed[:8], 16) % 60) / 100  # 0.7 to 1.3 range
        
        conviction = (inst_score + upside_score + cap_score) * dip_bonus * jitter
        
        # Ensure some minimum differentiation
        p['_conviction'] = max(conviction, 0.5 + i * 0.1)

        # Generate basic scores (1-10)
        p['_momentum'] = max(1, min(10, 5 + int(change_today)))
        p['_fundamentals'] = max(1, min(10, max(int(institutions), int(cap_score))))
        p['_sentiment'] = max(1, min(10, 5 + int(upside / 5)))
        p['_valuation'] = max(1, min(10, int(upside / 3) + 3))
    
    # ── Select top N stocks by conviction ───────────────────────────────
    picks.sort(key=lambda p: -p['_conviction'])
    picks = picks[:target_count]
    
    total_conviction = sum(p['_conviction'] for p in picks)
    
    allocations = []
    for p in picks:
        raw_weight  = p['_conviction'] / total_conviction
        capped_weight = min(raw_weight, max_w)
        alloc_amount  = round(investable * capped_weight, 2)
        price         = p.get('price') or 100
        shares        = max(1, int(alloc_amount / price))
        upside        = p.get('upside_pct') or 0
        num_inst      = p.get('num_institutions') or 0
        change_today  = p.get('change_percent') or 0
        
        # Build reasoning
        why_parts = []
        if num_inst:
            why_parts.append(f"{num_inst} institutions holding")
        if upside:
            why_parts.append(f"{upside}% analyst upside")
        if change_today < -2:
            why_parts.append(f"↓{abs(change_today):.1f}% today — buying dip")
        reasoning = '. '.join(why_parts) + '.' if why_parts else 'Top institutional pick.'

        # Build risk flags  
        risk_flags = []
        if abs(change_today) > 5:
            risk_flags.append(f"High volatility today ({change_today:+.1f}%)")
        if upside > 30:
            risk_flags.append("Analyst targets may be stale")
        
        # Entry/exit
        entry = 'Dollar-cost average over 2 weeks' if risk == 'conservative' else 'Buy at market'
        exit_sig = f'Sell if drops below ${price * 0.85:.0f} or fundamentals deteriorate'
        
        alloc_pct = round(capped_weight * 100, 1)
        alloc_logic = f"{alloc_pct}% weight — {'capped at max' if capped_weight >= max_w else 'conviction-weighted'}"
        
        allocations.append({
            'symbol':           p.get('ticker') or p.get('symbol'),
            'company_name':     p.get('name') or p.get('ticker'),
            'name':             p.get('name') or p.get('ticker'),
            'amount':           alloc_amount,
            'dollar_amount':    alloc_amount,
            'allocation_percent': alloc_pct,
            'weight_pct':       alloc_pct,
            'shares':           shares,
            'price':            round(price, 2),
            'sector':           p.get('sector') or 'N/A',
            'upside_pct':       upside,
            'change_today':     change_today,
            'reasoning':        reasoning,
            'reason':           reasoning,
            'allocation_logic': alloc_logic,
            'risk_flags':       risk_flags,
            'entry_strategy':   entry,
            'exit_signal':      exit_sig,
            'scores': {
                'momentum':     p.get('_momentum', 5),
                'fundamentals': p.get('_fundamentals', 5),
                'sentiment':    p.get('_sentiment', 5),
                'valuation':    p.get('_valuation', 5),
            },
            'drop_analysis':    None,
            'conviction_boost': change_today < -3 and upside > 10,
        })
    
    # Re-normalize weights
    total_alloc = sum(a['amount'] for a in allocations)
    if total_alloc > 0 and total_alloc != investable:
        factor = investable / total_alloc
        for a in allocations:
            a['amount']            = round(a['amount'] * factor, 2)
            a['dollar_amount']     = a['amount']
            a['weight_pct']        = round((a['amount'] / amount) * 100, 1)
            a['allocation_percent'] = a['weight_pct']
            a['shares']            = max(1, int(a['amount'] / a['price']))
    
    return sorted(allocations, key=lambda x: -x['amount'])

def _build_world_context(allocations, risk):
    """
    Build the full world context block for the portfolio results.
    Calls Claude once with everything — risks, trends, good news, thesis.
    Returns a dict with all sections.
    """
    sectors  = list(set(a.get('sector','') for a in allocations if a.get('sector')))
    tickers  = [a.get('symbol','') for a in allocations]

    # Pull latest news headlines for context
    news_headlines = []
    try:
        from news_service import fetch_all_rss
        articles = fetch_all_rss(limit=30)
        news_headlines = [a.get('title','') for a in articles[:15]]
    except Exception:
        pass
    headlines_str = '; '.join(news_headlines) if news_headlines else 'No live news available'

    # Pull market data
    market_indices = []
    try:
        market = _cache_get('market_indices:all') or {}
        market_indices = market.get('indices', [])
    except Exception:
        pass
    indices_str = ', '.join(
        f"{m['name']} {float(m.get('change_percent') or 0):+.1f}%" for m in market_indices
    ) if market_indices else 'Market data unavailable'

    prompt = f"""
You are a senior portfolio strategist. A {risk}-risk investor just built this portfolio:
Sectors: {', '.join(sectors)}
Tickers: {', '.join(tickers)}
Current market: {indices_str}
Latest news: {headlines_str}

Generate a complete world context report for this portfolio. Return ONLY this JSON:
{{
  "macro_context": "3-sentence overview of the current macro environment and what it means for this specific portfolio",
  
  "risk_warnings": [
    {{
      "icon": "⚔️",
      "title": "Risk title (5 words max)",
      "body": "2 sentences on the risk and which of the portfolio tickers it directly affects",
      "severity": "high",
      "affected_tickers": ["AAPL"]
    }}
  ],
  
  "tailwinds": [
    {{
      "icon": "🚀",
      "title": "Positive catalyst title",
      "body": "2 sentences on the good news / opportunity and which tickers benefit",
      "affected_tickers": ["NVDA", "MSFT"]
    }}
  ],
  
  "mega_trends": [
    {{
      "icon": "🤖",
      "title": "Trend name",
      "body": "2 sentences explaining the trend and why it matters for the portfolio over 1-3 years",
      "affected_tickers": ["NVDA"]
    }}
  ],
  
  "portfolio_thesis": "4-sentence complete investment thesis for this specific portfolio. Cover: why these sectors now, the macro tailwind behind the picks, the main risk to watch, and the expected time horizon.",
  
  "one_watch": {{
    "ticker": "ONE ticker from the portfolio to watch most closely this quarter",
    "reason": "2 sentences explaining why this specific stock is the key name to monitor"
  }}
}}

Rules:
- risk_warnings: exactly 3-4 items. Include at least: one geopolitical (wars/tariffs), one macro (inflation/rates), one market-specific
- tailwinds: exactly 3 items. Include real positive catalysts from current news or known trends
- mega_trends: exactly 3 items. Long-term structural trends (AI boom, GLP-1/obesity drugs, energy transition, defense spending, reshoring, etc.)
- All tickers in affected_tickers must come from the actual portfolio above
- Be specific, data-driven, direct. No vague language. No disclaimers in the JSON fields.
"""

    result = {}
    try:
        from ai_service import ask_gemini_json
        import hashlib, json
        key = f"world_context:{hashlib.md5((','.join(tickers)+risk).encode()).hexdigest()[:16]}"
        result = ask_gemini_json(prompt,
            system="You are a portfolio strategist. Return ONLY valid JSON.",
            max_tokens=1200,
            cache_key=key,
            cache_ttl=3600)
    except Exception as e:
        logger.warning('World context AI failed: %s', e)

    # ── Validate each section — fill with hardcoded content if empty ──
    if not result.get('risk_warnings'):
        result['risk_warnings'] = [
            {
                "icon": "⚔️",
                "title": "Geopolitical Tensions",
                "body": f"Ongoing conflicts in Eastern Europe and Middle East create supply chain and energy price volatility. Stocks like {tickers[0] if tickers else 'your holdings'} in global sectors face exposure to sudden market shocks.",
                "severity": "high",
                "affected_tickers": tickers[:2]
            },
            {
                "icon": "📈",
                "title": "Elevated Inflation Risk",
                "body": "Core inflation remains sticky above the Fed's 2% target, keeping interest rates higher for longer. Growth stocks face valuation compression when discount rates stay elevated.",
                "severity": "medium",
                "affected_tickers": tickers[2:4] if len(tickers) > 2 else tickers
            },
            {
                "icon": "🏦",
                "title": "Fed Rate Policy Uncertainty",
                "body": "The Federal Reserve may delay or reduce expected rate cuts if the labor market stays hot. This creates headwind for high-multiple technology stocks and benefits financial stocks short-term.",
                "severity": "medium",
                "affected_tickers": tickers[:3]
            },
            {
                "icon": "🌏",
                "title": "China-US Trade Tensions",
                "body": "Escalating tariffs and technology export restrictions between the US and China directly affect semiconductor, consumer tech, and manufacturing supply chains.",
                "severity": "medium",
                "affected_tickers": [t for t in tickers if t in ['AAPL','NVDA','QCOM','MSFT']][:2] or tickers[:1]
            }
        ]
    
    if not result.get('tailwinds'):
        result['tailwinds'] = [
            {
                "icon": "🤖",
                "title": "AI Capital Expenditure Supercycle",
                "body": "Microsoft, Google, Meta, and Amazon are committing $300B+ in AI infrastructure in 2025 alone. This creates massive revenue tailwinds for cloud providers, semiconductor companies, and data center operators in your portfolio.",
                "affected_tickers": [t for t in tickers if t in ['MSFT','GOOGL','NVDA','AMZN','META']] or tickers[:2]
            },
            {
                "icon": "💊",
                "title": "GLP-1 Healthcare Revolution",
                "body": "Obesity and diabetes drugs are the fastest-growing pharmaceutical category in history. Eli Lilly and Novo Nordisk are posting 30-50% revenue growth, with the market potentially reaching $150B by 2030.",
                "affected_tickers": [t for t in tickers if t in ['LLY','NVO','JNJ']] or []
            },
            {
                "icon": "🏛️",
                "title": "US Defense Spending Surge",
                "body": "NATO allies are increasing defense budgets rapidly following geopolitical instability. US defense contractors are seeing multi-year order backlogs at record levels.",
                "affected_tickers": [t for t in tickers if t in ['RTX','LMT','NOC','GD']] or []
            }
        ]
    
    if not result.get('mega_trends'):
        result['mega_trends'] = [
            {
                "icon": "🤖",
                "title": "Artificial Intelligence Infrastructure",
                "body": "The AI compute buildout is the largest capital investment cycle since the internet. GPU demand, data center power, and AI software subscriptions will compound for 5-10 years. This is the defining investment theme of this decade.",
                "affected_tickers": [t for t in tickers if t in ['NVDA','MSFT','GOOGL','AMZN','META']] or tickers[:2]
            },
            {
                "icon": "⚡",
                "title": "Energy Transition & Power Demand",
                "body": "AI data centers and EV adoption are creating a power demand surge not seen in 50 years. Utilities, nuclear, and natural gas are all benefiting from a multi-decade grid investment cycle.",
                "affected_tickers": [t for t in tickers if t in ['XOM','NEE','DUK','SO','VST']] or []
            },
            {
                "icon": "🏭",
                "title": "US Manufacturing Reshoring",
                "body": "The CHIPS Act, Inflation Reduction Act, and supply chain de-risking are bringing hundreds of billions in manufacturing back to the US. Industrial and materials companies face a multi-year capex boom.",
                "affected_tickers": [t for t in tickers if t in ['CAT','DE','HON','GE','EMR']] or []
            }
        ]
    
    if not result.get('portfolio_thesis'):
        result['portfolio_thesis'] = (
            f"This {risk}-risk portfolio is positioned across {', '.join(sectors[:3])} to capture "
            f"the AI infrastructure supercycle and long-term structural growth trends. "
            f"The selection prioritizes companies with strong institutional backing and analyst upside consensus. "
            f"Key risk is a 'higher for longer' rate environment which could compress valuations — "
            f"the cash reserve provides flexibility to add on any significant pullback."
        )

    if not result.get('macro_context'):
        result['macro_context'] = 'Market remains in a structurally strong but high-multiple environment driven by technological mega-trends, requiring discipline in high-conviction positioning.'

    return result

# ── Stock search for Build Your Own Portfolio ──────────────────────────────
@app.route("/api/stock/search", methods=["GET"])
def api_stock_search():
    """Search / validate a stock ticker. Returns name, price, sector."""
    ticker = (request.args.get('q') or '').upper().strip()
    if not ticker or len(ticker) > 6:
        return jsonify({'error': 'Invalid ticker'}), 400
    try:
        from fmp_client import quote as fmp_quote, profile as fmp_profile
        q = fmp_quote(ticker)
        if not q or not q.get('price'):
            return jsonify({'error': f'No data for {ticker}'}), 404
        price = q['price']
        name = q.get('name') or ticker
        sector = 'N/A'
        prof = fmp_profile(ticker)
        if prof:
            name = prof.get('companyName') or name
            sector = prof.get('sector') or 'N/A'
        return jsonify({
            'symbol': ticker,
            'name': name,
            'price': round(float(price), 2),
            'sector': sector,
        })
    except Exception as e:
        return jsonify({'error': f'Could not find {ticker}'}), 404

@app.route("/api/portfolio/allocate", methods=["POST"])
def api_portfolio_allocate():
    try:
        data    = request.json or {}
        amount  = float(data.get('amount', 10000))
        risk    = data.get('risk', 'moderate').lower()
        sectors = data.get('sectors', [])
        mode    = data.get('mode', 'ai')    # 'manual' = Build Your Own, 'ai' = AI-Automated

        # ── New fields ────────────────────────────────────────────────────
        horizon           = data.get('horizon', '1y')
        goal              = data.get('goal', 'growth')
        exclude_sectors   = data.get('exclude_sectors', [])
        existing_holdings = data.get('existing_holdings', [])
        rebalance_mode    = data.get('rebalance_mode', 'alert_rebalance')

        if amount < 100:
            return jsonify({'error': 'Minimum investment is $100'}), 400

        # ═══ BUILD YOUR OWN mode: ONLY use user-selected stocks ═══
        if mode == 'manual' and existing_holdings:
            picks = [{'ticker': t, 'sector': 'N/A', 'upside_pct': 0, 'num_institutions': 0} for t in existing_holdings]
            logger.info('Manual mode: using %d user-selected stocks: %s', len(picks), existing_holdings)
        else:
            # ── Get picks from DB cache (fast, already computed) ──────────────
            picks = []
            try:
                from db import get_consensus_with_change
                result = get_consensus_with_change(n=30)
                picks  = result.get('picks', []) if result else []
            except Exception as e:
                logger.warning('DB picks failed: %s', e)

            # ── Fallback: broad diversified list (candidates) ─
            if not picks:
                picks = [
                    {'ticker':'AAPL','sector':'Technology','upside_pct':12,'num_institutions':8},
                    {'ticker':'MSFT','sector':'Technology','upside_pct':15,'num_institutions':10},
                    {'ticker':'NVDA','sector':'Technology','upside_pct':25,'num_institutions':9},
                    {'ticker':'GOOGL','sector':'Technology','upside_pct':18,'num_institutions':7},
                    {'ticker':'AMZN','sector':'Technology','upside_pct':20,'num_institutions':8},
                    {'ticker':'JPM','sector':'Financials','upside_pct':10,'num_institutions':6},
                    {'ticker':'V','sector':'Financials','upside_pct':14,'num_institutions':8},
                    {'ticker':'BRK-B','sector':'Financials','upside_pct':8,'num_institutions':7},
                    {'ticker':'LLY','sector':'Healthcare','upside_pct':22,'num_institutions':7},
                    {'ticker':'UNH','sector':'Healthcare','upside_pct':16,'num_institutions':6},
                    {'ticker':'JNJ','sector':'Healthcare','upside_pct':8,'num_institutions':5},
                    {'ticker':'XOM','sector':'Energy','upside_pct':9,'num_institutions':5},
                    {'ticker':'CVX','sector':'Energy','upside_pct':11,'num_institutions':4},
                    {'ticker':'KO','sector':'Consumer','upside_pct':6,'num_institutions':4},
                    {'ticker':'PG','sector':'Consumer','upside_pct':7,'num_institutions':5},
                    {'ticker':'HD','sector':'Consumer Cyclical','upside_pct':13,'num_institutions':6},
                    {'ticker':'AVGO','sector':'Technology','upside_pct':28,'num_institutions':8},
                    {'ticker':'LMT','sector':'Defense','upside_pct':10,'num_institutions':5},
                    {'ticker':'NEE','sector':'Utilities','upside_pct':9,'num_institutions':4},
                    {'ticker':'AMT','sector':'Real Estate','upside_pct':12,'num_institutions':5},
                ]

            # ── Inject Target Stocks/Existing Holdings into AI mode ───────────
            for t in existing_holdings:
                if not any(p.get('ticker') == t or p.get('symbol') == t for p in picks):
                    picks.append({'ticker': t, 'sector': 'N/A', 'upside_pct': 0, 'num_institutions': 0})

        # ── Enrich with live prices (this also fills sector from yfinance/FMP) ──
        picks = enrich_picks_with_prices(picks)

        # ── Sector map for matching user labels to actual sector names ──
        sector_map = {
            'financial services': ['financials', 'financial services', 'banks', 'finance'],
            'financials':         ['financials', 'financial services', 'banks', 'finance'],
            'healthcare':         ['healthcare', 'health care', 'biotech', 'pharmaceuticals', 'medical'],
            'technology':         ['technology', 'tech', 'information technology', 'software', 'semiconductors'],
            'consumer cyclical':  ['consumer cyclical', 'consumer discretionary', 'retail'],
            'communication':      ['communication', 'communication services', 'telecom', 'media'],
            'communication services': ['communication', 'communication services', 'telecom', 'media'],
            'energy':             ['energy', 'oil', 'gas'],
            'defense':            ['defense', 'aerospace', 'military', 'industrials'],
            'real estate':        ['real estate', 'reit'],
            'utilities':          ['utilities', 'utility'],
            'crypto':             ['crypto', 'cryptocurrency', 'blockchain'],
        }

        def matches_sector(pick_sector, user_sectors):
            ps = (pick_sector or '').lower().strip()
            if not ps or ps == 'n/a':
                return False
            for us in user_sectors:
                aliases = sector_map.get(us.lower(), [us.lower()])
                if any(alias in ps or ps in alias for alias in aliases):
                    return True
            return False

        # ── STRICT filter by preferred sector ─────────────────────────────
        if sectors:
            filtered = [p for p in picks if matches_sector(p.get('sector',''), sectors)]
            logger.info('Sector filter: %d/%d picks match sectors=%s', len(filtered), len(picks), sectors)
            if filtered:
                picks = filtered
            # If 0 matched, keep all — AI will handle sector selection via prompt

        # ── Exclude sectors ───────────────────────────────────────────────
        if exclude_sectors:
            picks = [p for p in picks if not matches_sector(p.get('sector',''), exclude_sectors)]

        if len(picks) < 3:
            logger.error('CRITICAL: Enrichment returned only %d picks.', len(picks))

        # ── Gather live market context ────────────────────────────────────
        news_headlines = []
        try:
            from news_service import fetch_all_rss
            articles = fetch_all_rss(limit=20)
            news_headlines = [a.get('title', '') for a in articles if a.get('title')]
        except Exception:
            pass

        market_summary = ''
        try:
            market = _cache_get('market_indices:all') or {}
            indices = market.get('indices', [])
            if indices:
                market_summary = ', '.join(
                    f"{m['name']} {float(m.get('change_percent') or 0):+.1f}%"
                    for m in indices
                )
        except Exception:
            pass

        # ── Try AI allocation ─────────────────────────────────────────────
        allocations     = []
        ai_rationale    = ''
        ai_risk_note    = ''
        ai_volatility   = 'medium'
        ai_diversify    = 5
        ai_dividend     = 0.0
        ai_type_mix     = {}
        try:
            from ai_service import generate_smart_portfolio
            logger.info('Calling AI portfolio: %d picks, %d headlines, risk=%s, horizon=%s, goal=%s',
                       len(picks), len(news_headlines), risk, horizon, goal)
            ai_result = generate_smart_portfolio(
                amount=amount, risk=risk, sectors=sectors, top_picks=picks,
                horizon=horizon, goal=goal, exclude_sectors=exclude_sectors,
                existing_holdings=existing_holdings, news_headlines=news_headlines,
                market_summary=market_summary, rebalance_mode=rebalance_mode
            )
            # Check for parse error from ask_gemini_json
            if ai_result and isinstance(ai_result, dict) and ai_result.get('error'):
                logger.warning('AI returned error: %s. Raw: %s',
                             ai_result.get('error'), str(ai_result.get('raw', ''))[:300])
                ai_result = None
            
            if ai_result and ai_result.get('allocations'):
                allocations     = ai_result['allocations']
                ai_rationale    = ai_result.get('rationale', '')
                ai_risk_note    = ai_result.get('risk_note', '')
                ai_volatility   = ai_result.get('expected_volatility', 'medium')
                ai_diversify    = ai_result.get('diversification_score', 5)
                ai_dividend     = ai_result.get('estimated_dividend_yield', 0.0)
                ai_type_mix     = ai_result.get('portfolio_type_mix', {})
                logger.info('AI portfolio SUCCESS: %d stocks allocated', len(allocations))
            else:
                logger.warning('AI returned no allocations. Result keys: %s',
                             list(ai_result.keys()) if ai_result and isinstance(ai_result, dict) else 'None')
        except Exception as e:
            logger.warning('AI allocation FAILED: %s', e, exc_info=True)

        # ── Math fallback if AI fails ─────────────────────────────────────
        if not allocations:
            allocations = _smart_allocate(picks, amount, risk, horizon, goal)
            ai_rationale = (
                f"Conviction-weighted {risk} portfolio for {goal} goal. "
                f"Stocks with high institutional backing and analyst upside receive larger positions. "
                f"Beaten-down stocks with strong upside received a dip-buying boost."
            )

        # Normalize field names for frontend compatibility
        for a in allocations:
            a.setdefault('company_name', a.get('name', a.get('symbol', '')))
            a.setdefault('reasoning', a.get('reason', ''))
            a.setdefault('allocation_percent', a.get('weight_pct', 0))
            a.setdefault('dollar_amount', a.get('amount', 0))
            a.setdefault('risk_flags', [])
            a.setdefault('scores', {'momentum': 5, 'fundamentals': 5, 'sentiment': 5, 'valuation': 5})
            a.setdefault('entry_strategy', 'Buy at market')
            a.setdefault('exit_signal', 'Review if drops 15%+ or fundamentals change')
            a.setdefault('allocation_logic', '')
            a.setdefault('drop_analysis', None)

        # ── Sector breakdown ──────────────────────────────────────────────
        sector_totals = {}
        for a in allocations:
            sec = a.get('sector','Other')
            sector_totals[sec] = sector_totals.get(sec,0) + float(a.get('amount', a.get('dollar_amount', 0)))
        sector_breakdown = [
            {'sector':k,'amount':round(v,2),'pct':round(v/amount*100,1)}
            for k,v in sorted(sector_totals.items(), key=lambda x:-x[1])
        ]

        total_allocated = sum(float(a.get('amount', a.get('dollar_amount', 0))) for a in allocations)
        exp_upside = (sum(
            float(a.get('amount', a.get('dollar_amount', 0))) *
            float(str(a.get('upside_pct',0)).replace('%','') or 0)
            for a in allocations
        ) / total_allocated) if total_allocated else 0

        # ── Generate world context via AI ─────────────────────────────────
        world_context = _build_world_context(allocations, risk)

        return jsonify({
            'status':               'success',
            'amount':               amount,
            'risk_level':           risk,
            'horizon':              horizon,
            'goal':                 goal,
            'allocations':          allocations,
            'cash_reserve':         round(amount - total_allocated, 2),
            'expected_upside_pct':  round(exp_upside, 1),
            'sector_breakdown':     sector_breakdown,
            'ai_rationale':         ai_rationale,
            'ai_risk_note':         ai_risk_note,
            'expected_volatility':  ai_volatility,
            'diversification_score': ai_diversify,
            'estimated_dividend_yield': ai_dividend,
            'portfolio_type_mix':   ai_type_mix,
            'world_context':        world_context,
            'num_stocks':           len(allocations),
        })

    except Exception as e:
        logger.exception('Portfolio allocate error: %s', e)
        return jsonify({'error': str(e), 'status': 'error'}), 500

def _calculate_sector_averages(sector: str) -> dict:
    """Calculates median PE and ROI for a given sector using cached recommendations"""
    try:
        from db import _conn as get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT result_json FROM cache_results WHERE endpoint = 'institutional_recommendations'")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"median_pe": 20.0, "median_roi": 10.0} # Fallback
            
        data = json.loads(row[0])
        sector_stocks = [r for r in data if r.get("sector") == sector]
        
        pes = []
        rois = []
        from fmp_client import key_metrics_ttm
        for stock in sector_stocks:
             try:
                 km = key_metrics_ttm(stock["symbol"])
                 if km:
                     pe = km.get("pe_ratio")
                     roi = km.get("roe")  # Return on Equity
                     if pe and pe > 0: pes.append(pe)
                     if roi: rois.append(roi * 100)
             except:
                 pass
                 
        if not pes: pes = [20.0]
        if not rois: rois = [10.0]
        
        import statistics
        return {
            "median_pe": round(statistics.median(pes), 2),
            "median_roi": round(statistics.median(rois), 2)
        }
            
    except Exception as e:
        print(f"Error calculating sector averages: {e}")
        return {"median_pe": 20.0, "median_roi": 10.0}

@app.route("/api/analysis/deep/<ticker>")
def api_deep_analysis(ticker):
    try:
        from fmp_client import quote as fmp_quote, profile as fmp_profile, key_metrics_ttm
        ticker = ticker.upper()
        
        # 1. Fetch FMP data instead of yfinance
        q = fmp_quote(ticker)
        if not q or not q.get("price"):
            return jsonify({"error": "Ticker not found"}), 404
        
        prof = fmp_profile(ticker)
        km = key_metrics_ttm(ticker)
        
        sector = (prof or {}).get("sector", "Unknown")
        price = q["price"]
        pe = (km or {}).get("pe_ratio", 0) or 0
        roi = ((km or {}).get("roe", 0) or 0) * 100
        sma_50 = (prof or {}).get("fiftyDayAverage", 0) or 0
        sma_200 = (prof or {}).get("twoHundredDayAverage", 0) or 0
        
        # 2. Fetch Sector Baselines
        baselines = _cache_get(f"sector_avg_{sector}")
        if not baselines:
             baselines = _calculate_sector_averages(sector)
             _cache_set(f"sector_avg_{sector}", baselines) # 24hr via LRU
             
        # 3. Fetch Insider Activity
        import institutional_analyzer.data_fetcher as df
        fetcher = df.InstitutionalDataFetcher()
        insider = fetcher.get_insider_activity(ticker)
        
        # ---------------- EVALUATION LOGIC ----------------
        
        # A. Valuation
        val_status = "FAIR_VALUE"
        val_thesis = f"Trading roughly inline with the {sector} sector average."
        if pe and pe > 0:
            if pe < (baselines["median_pe"] * 0.8) and roi >= baselines["median_roi"]:
                val_status = "UNDERVALUED"
                val_thesis = f"Trading at a significant discount to the {sector} sector median P/E, while delivering higher Return on Equity."
            elif pe > (baselines["median_pe"] * 1.5) and roi < baselines["median_roi"]:
                val_status = "OVERVALUED"
                val_thesis = f"Trading at a hefty premium (P/E > 150% of sector) while lagging the {sector} median Return on Equity. Proceed with caution."
                
        # B. Insider Signals
        ins_signal = "NEUTRAL"
        ins_thesis = "No extreme insider accumulation or distribution detected in the last 6 months."
        if insider:
            net = insider["net_shares"]
            buys = insider["total_buys"]
            sales = insider["total_sales"]
            
            if buys > 0 and sales == 0:
                ins_signal = "STRONG_BUY"
                ins_thesis = f"Heavy accumulation. {insider['unique_buyers']} distinct executives purchased {buys:,} shares on the open market with absolutely zero insider selling."
            elif net > 100000:
                ins_signal = "ACCUMULATION"
                ins_thesis = f"Net accumulation of {net:,} shares over the last 6 months shows positive conviction from management."
            elif sales > 0 and buys == 0:
                 ins_signal = "DISTRIBUTION"
                 ins_thesis = f"Open market selling pressure. Insiders have sold {sales:,} shares without a single open market purchase."
                 
        # C. Technical Trend
        trend_dir = "SIDEWAYS"
        trend_signals = []
        trend_thesis = "Consolidating near major moving averages. No clear momentum."
        
        if sma_50 > 0 and sma_200 > 0:
            if price > sma_50 and sma_50 > sma_200:
                trend_dir = "UPTREND"
                trend_signals.append("ABOVE_200_SMA")
                if (price / sma_50) < 1.05 and (price > sma_50):
                     trend_signals.append("FRESH_BREAKOUT")
                     trend_thesis = "Bullish structure. Price has recently crossed tightly above the 50-day moving average, confirming a new localized uptrend."
                else:
                     trend_thesis = "Confirmed long-term uptrend. Price remains robustly above both the 50-day and 200-day moving averages."
            elif price < sma_50 and sma_50 < sma_200:
                trend_dir = "DOWNTREND"
                trend_signals.append("BELOW_200_SMA")
                trend_thesis = "Bearish structure. Stock is trapped below its 50-day and 200-day moving averages."
                
        # Build Response
        return jsonify({
            "symbol": ticker,
            "company_name": (prof or {}).get("companyName", ticker),
            "sector": sector,
            "current_price": round(price, 2),
            "valuation": {
                "status_flag": val_status,
                "metrics": {
                    "stock_pe": round(pe, 2) if pe else None,
                    "stock_roi": round(roi, 2) if roi else None,
                    "sector_median_pe": baselines["median_pe"],
                    "sector_median_roi": baselines["median_roi"]
                },
                "thesis": val_thesis
            },
            "insider_activity": {
                "signal": ins_signal,
                "timeframe": "6_Months",
                "metrics": insider or {"total_buys": 0, "total_sales": 0, "net_shares": 0, "unique_buyers": 0},
                "thesis": ins_thesis
            },
            "technical_trend": {
                "direction": trend_dir,
                "signals": trend_signals,
                "metrics": {
                    "sma_50": round(sma_50, 2),
                    "sma_200": round(sma_200, 2)
                },
                "thesis": trend_thesis
            }
        })

    except Exception as e:
        logger.error(f"Deep Analysis API Error on {ticker}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# Watchlist routes moved to routes/watchlist.py
# _compute_market_signal kept here as it is imported by the watchlist blueprint
# ---------------------------------------------------------------------------

# api_watchlist_intel moved to routes/watchlist.py

def _compute_market_signal():
    """Compute a global GO / CAUTION / DANGER market signal."""
    try:
        from fmp_client import quote as fmp_quote, historical_daily
        from datetime import timedelta

        q = fmp_quote("SPY")
        if not q or not q.get("price"):
            return {"signal": "neutral", "label": "Market data unavailable", "score": 5}

        now = datetime.now(timezone.utc)
        to_d = now.strftime("%Y-%m-%d")
        from_d = (now - timedelta(days=10)).strftime("%Y-%m-%d")
        hist = historical_daily("SPY", from_d, to_d)
        
        if not hist or len(hist) < 2:
            return {"signal": "neutral", "label": "Market data unavailable", "score": 5}

        closes = [h["close"] for h in hist if h.get("close")]
        if len(closes) < 2:
            return {"signal": "neutral", "label": "Market data unavailable", "score": 5}

        spy_change_1d = ((closes[-1] / closes[-2]) - 1) * 100
        spy_change_5d = ((closes[-1] / closes[0]) - 1) * 100

        ms = 5.0
        ms += spy_change_1d * 1.0
        ms += spy_change_5d * 0.5

        ms = max(1, min(10, round(ms)))

        if ms >= 7:
            signal, label = "go", f"Market strong — S&P 500 {'up' if spy_change_1d >= 0 else 'down'} {abs(spy_change_1d):.1f}% today, {'+' if spy_change_5d >= 0 else ''}{spy_change_5d:.1f}% this week"
        elif ms <= 3:
            signal, label = "danger", f"Market weak — S&P 500 {'up' if spy_change_1d >= 0 else 'down'} {abs(spy_change_1d):.1f}% today, {'+' if spy_change_5d >= 0 else ''}{spy_change_5d:.1f}% this week"
        else:
            signal, label = "neutral", f"Market mixed — S&P 500 {'+' if spy_change_1d >= 0 else ''}{spy_change_1d:.1f}% today"

        return {
            "signal": signal,
            "label": label,
            "score": ms,
            "spy_1d": round(spy_change_1d, 2),
            "spy_5d": round(spy_change_5d, 2),
        }
    except Exception as e:
        logger.warning("Market signal calc failed: %s", e)
        return {"signal": "neutral", "label": "Market data unavailable", "score": 5}


# api_watchlist_build moved to routes/watchlist.py

# ═══════════════════════════════════════════════════════════════════════════════
#  ALPHA SCREENER ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/alpha-screener")
def api_alpha_screener():
    """Multi-parameter screener: find the next big stock.
    Returns top 10 stocks with composite scores + per-parameter breakdown."""
    cache_key = "alpha_screener:top10"
    if not request.args.get("refresh"):
        cached = _cache_get(cache_key)
        if cached:
            return _jsonify_cached(cached, cache_seconds=3600)

    try:
        from alpha_screener import get_alpha_picks
        picks = get_alpha_picks(force_refresh=bool(request.args.get("refresh")))
        result = {
            "picks": picks,
            "count": len(picks),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "description": "Multi-parameter screener: stocks with potential for explosive growth based on 15+ signals.",
        }
        if picks:
            _cache_set(cache_key, result)
        return _jsonify_cached(result, cache_seconds=3600)
    except Exception as e:
        logger.error("Alpha screener failed: %s", e)
        return _jsonify_cached({"picks": [], "error": str(e)}, cache_seconds=60)


# AI routes moved to routes/ai.py
# ---------------------------------------------------------------------------
def _startup():
    """Initialize DB and start background workers. Called on startup regardless of server."""
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("DB init failed: %s", e)

    # Clean up old cache and compact DB
    try:
        import sqlite3
        db_path = str(Path(__file__).resolve().parent / "smart_money.db")
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM cache_results WHERE updated_at < datetime('now', '-7 days')")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
        conn.close()
        logger.info('DB cleanup complete')
    except Exception as e:
        logger.warning('DB cleanup failed: %s', e)

    # Delay 15s between thread starts so they don't all hammer APIs at once

    # Start background cache thread
    try:
        from cache_job import start_background_cache
        start_background_cache()
    except Exception as e:
        logger.warning("Background cache start failed: %s", e)

    time.sleep(15)
    # Start background alert thread
    try:
        from alert_job import start_background_alerts
        start_background_alerts()
    except Exception as e:
        logger.warning("Background alerts start failed: %s", e)

    time.sleep(15)
    # Start live news scanner
    try:
        from news_scanner import start_scanner
        start_scanner()
    except Exception as e:
        logger.warning("News scanner start failed: %s", e)

    time.sleep(15)
    # Start AI Market Pulse engine
    try:
        from ai_market_intel import start_pulse_engine
        start_pulse_engine()
    except Exception as e:
        logger.warning("Market pulse engine start failed: %s", e)

    time.sleep(15)
    # Start market data worker (live quotes every 15s)
    try:
        from market_worker import start_background_worker
        start_background_worker()
    except Exception as e:
        logger.warning("Market worker start failed: %s", e)

    time.sleep(15)
    # Start alpha screener background refresh
    try:
        from alpha_screener import start_alpha_background
        start_alpha_background()
    except Exception as e:
        logger.warning("Alpha screener start failed: %s", e)


# Run startup in a background thread so gunicorn doesn't block waiting for it
# (the 15s sleeps between workers would cause gunicorn to time out otherwise)
_startup_thread = threading.Thread(target=_startup, daemon=True, name="startup")
_startup_thread.start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print("\n" + "=" * 50)
    print(f"  Server running at: http://127.0.0.1:{port}")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)