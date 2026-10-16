"""
News routes — RSS feed endpoints for the News Hub.
"""
import re
import logging
from flask import Blueprint, jsonify, request, session, make_response
from news_service import fetch_all_rss, HIGH_IMPACT_PATTERN
from db import get_watchlist

logger = logging.getLogger(__name__)

news_bp = Blueprint("news", __name__)

# Known tickers to detect in headlines
_KNOWN_TICKERS = {
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA',
    'JPM', 'JNJ', 'V', 'UNH', 'XOM', 'PG', 'MA', 'HD', 'CVX', 'MRK',
    'ABBV', 'PEP', 'KO', 'PFE', 'COST', 'AVGO', 'TMO', 'MCD', 'WMT',
    'CSCO', 'ACN', 'ABT', 'CRM', 'AMD', 'TXN', 'DHR', 'ADBE',
    'NFLX', 'ORCL', 'INTC', 'QCOM', 'BA', 'GE', 'CAT', 'HON',
    'DIS', 'PYPL', 'SQ', 'COIN', 'PLTR', 'UBER', 'SNAP', 'SHOP',
    'SPY', 'QQQ', 'GLD', 'TLT', 'LLY', 'NVO', 'ARM', 'SMCI',
    'CRWD', 'PANW', 'NET', 'DDOG', 'SNOW', 'RIVN', 'SOFI', 'MARA',
    'GME', 'AMC', 'BAC', 'GS', 'MS', 'BLK', 'C', 'WFC',
}
_TICKER_RE = re.compile(r'\b([A-Z]{2,5})\b')


def _enrich_article(art):
    """Add impact_score and mentioned_tickers to an RSS article dict."""
    text = (art.get('title', '') + ' ' + art.get('summary', '')).upper()
    tickers = sorted({m for m in _TICKER_RE.findall(text) if m in _KNOWN_TICKERS})

    title_lower = (art.get('title', '') + ' ' + art.get('summary', '')).lower()
    matches = HIGH_IMPACT_PATTERN.findall(title_lower)
    score = min(len(matches) * 2, 6)
    if HIGH_IMPACT_PATTERN.search((art.get('title', '') or '').lower()):
        score += 4
    score = min(score, 10)

    art['impact_score'] = score
    art['mentioned_tickers'] = tickers
    return art


@news_bp.route("/api/news/feed")
def api_news_feed():
    """Return enriched RSS articles for the News Hub Live Wire."""
    articles = fetch_all_rss(limit=60)
    enriched = [_enrich_article(a) for a in articles]
    # Sort high-impact first, then by published date
    enriched.sort(key=lambda a: (-a.get('impact_score', 0), a.get('published') or ''), reverse=False)
    resp = make_response(jsonify({"articles": enriched, "count": len(enriched)}))
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp


@news_bp.route("/api/news/watchlist-feed")
def api_news_watchlist_feed():
    """Return RSS articles filtered to the user's watchlist tickers."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login required"}), 401

    watchlist = get_watchlist(user_id) or []
    if not watchlist:
        return jsonify({
            "articles": [],
            "count": 0,
            "message": "Your watchlist is empty. Add stocks to see personalized news."
        })

    wl_set = {s.upper() for s in watchlist}
    articles = fetch_all_rss(limit=80)
    enriched = [_enrich_article(a) for a in articles]

    filtered = [
        a for a in enriched
        if any(t in wl_set for t in a.get('mentioned_tickers', []))
    ]

    return jsonify({"articles": filtered, "count": len(filtered)})
