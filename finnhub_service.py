"""
Finnhub API client — Real-time stock quotes, company news, and intraday candles.
Uses the Finnhub.io REST API (free tier: 60 calls/min).
"""

import os
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
BASE_URL = "https://finnhub.io/api/v1"


def _get(endpoint: str, params: dict = None, timeout: int = 8) -> Optional[dict]:
    """Make an authenticated Finnhub API request."""
    if not FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not set")
        return None

    if params is None:
        params = {}
    params["token"] = FINNHUB_API_KEY

    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=timeout)
        if r.status_code == 429:
            logger.warning("Finnhub rate limited")
            return None
        if r.ok:
            return r.json()
        logger.warning("Finnhub %s returned %d", endpoint, r.status_code)
        return None
    except Exception as e:
        logger.error("Finnhub request failed: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  REAL-TIME QUOTE
# ═══════════════════════════════════════════════════════════════════════════════

def get_realtime_quote(symbol: str) -> Optional[Dict]:
    """
    Get real-time quote for a symbol.
    Returns: {price, change, change_percent, high, low, open, prev_close, timestamp}
    """
    data = _get("quote", {"symbol": symbol.upper()})
    if not data or data.get("c") is None or data.get("c") == 0:
        return None

    return {
        "symbol": symbol.upper(),
        "price": round(data["c"], 2),          # Current price
        "change": round(data["d"] or 0, 2),     # Change
        "change_percent": round(data["dp"] or 0, 2),  # Change %
        "high": round(data["h"] or 0, 2),       # Day high
        "low": round(data["l"] or 0, 2),        # Day low
        "open": round(data["o"] or 0, 2),       # Open
        "prev_close": round(data["pc"] or 0, 2),  # Previous close
        "timestamp": data.get("t", 0),          # Unix timestamp
        "is_market_open": _is_market_open(),
    }


def _is_market_open() -> bool:
    """Check if US market is roughly open (9:30 AM - 4:00 PM ET, weekdays)."""
    now = datetime.now(timezone.utc)
    # ET is UTC-5 (EST) or UTC-4 (EDT). Rough check.
    et_hour = (now.hour - 5) % 24
    is_weekday = now.weekday() < 5
    return is_weekday and 9 <= et_hour < 16


# ═══════════════════════════════════════════════════════════════════════════════
#  GENERAL MARKET NEWS
# ═══════════════════════════════════════════════════════════════════════════════

def get_market_news(category: str = "general", limit: int = 50) -> List[Dict]:
    """
    Get latest general market news (not company-specific).
    category: 'general', 'forex', 'crypto', 'merger'
    Returns list of {headline, summary, source, url, datetime, related, image}.
    """
    data = _get("news", params={"category": category})
    if not data or not isinstance(data, list):
        return []

    results = []
    for item in data[:limit]:
        results.append({
            "headline": item.get("headline", ""),
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "datetime": item.get("datetime", 0),
            "related": item.get("related", ""),  # Ticker symbols mentioned
            "image": item.get("image", ""),
        })
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  COMPANY NEWS
# ═══════════════════════════════════════════════════════════════════════════════

def get_company_news(symbol: str, days: int = 7, limit: int = 15) -> List[Dict]:
    """
    Get latest news articles for a specific company.
    Returns list of {headline, summary, source, url, datetime, image, related}.
    """
    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = now.strftime("%Y-%m-%d")

    data = _get("company-news", {
        "symbol": symbol.upper(),
        "from": from_date,
        "to": to_date,
    })

    if not data or not isinstance(data, list):
        return []

    articles = []
    for item in data[:limit]:
        articles.append({
            "headline": item.get("headline", ""),
            "summary": (item.get("summary") or "")[:400],
            "source": item.get("source", ""),
            "url": item.get("url", "#"),
            "datetime": item.get("datetime", 0),
            "image": item.get("image", ""),
            "related": item.get("related", symbol.upper()),
            "category": item.get("category", ""),
        })

    return articles


# ═══════════════════════════════════════════════════════════════════════════════
#  INTRADAY CANDLES
# ═══════════════════════════════════════════════════════════════════════════════

def get_intraday_candles(symbol: str, resolution: str = "5", count: int = 78) -> List[Dict]:
    """
    Get intraday candle data for live charting.
    resolution: '1', '5', '15', '30', '60' (minutes)
    count: number of candles (78 * 5min ≈ full trading day)
    Returns list of {time, open, high, low, close, volume}.
    """
    now = int(time.time())
    # Go back enough time to get 'count' candles
    resolution_seconds = int(resolution) * 60
    from_ts = now - (count * resolution_seconds + 3600)  # Extra hour buffer

    data = _get("stock/candle", {
        "symbol": symbol.upper(),
        "resolution": resolution,
        "from": from_ts,
        "to": now,
    })

    if not data or data.get("s") != "ok":
        return []

    candles = []
    timestamps = data.get("t", [])
    opens = data.get("o", [])
    highs = data.get("h", [])
    lows = data.get("l", [])
    closes = data.get("c", [])
    volumes = data.get("v", [])

    for i in range(len(timestamps)):
        dt = datetime.fromtimestamp(timestamps[i], tz=timezone.utc)
        candles.append({
            "time": dt.strftime("%H:%M"),
            "time_full": dt.isoformat(),
            "open": round(opens[i], 2),
            "high": round(highs[i], 2),
            "low": round(lows[i], 2),
            "close": round(closes[i], 2),
            "volume": volumes[i] if i < len(volumes) else 0,
        })

    return candles[-count:]  # Limit to requested count


# ═══════════════════════════════════════════════════════════════════════════════
#  AI NEWS VERDICT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_news_verdict(symbol: str, news: List[Dict], current_price: float = None) -> Optional[Dict]:
    """
    Use Claude to analyze company-specific news and give a BUY/SELL/HOLD verdict.
    """
    if not news:
        return None

    headlines = "\n".join(
        f"  [{i+1}] {n['headline']} ({n['source']}, {datetime.fromtimestamp(n['datetime'], tz=timezone.utc).strftime('%b %d') if n.get('datetime') else 'recent'})"
        for i, n in enumerate(news[:12])
    )

    price_ctx = f"Current price: ${current_price:.2f}" if current_price else "Price data unavailable"

    prompt = f"""You are an elite hedge fund analyst. Analyze these recent news articles about {symbol} and determine if investors should BUY, SELL, or HOLD this stock based ONLY on the news sentiment and catalysts.

{price_ctx}

═══ RECENT NEWS FOR {symbol} ═══
{headlines}

Return ONLY this JSON:
{{
  "verdict": "BUY" or "SELL" or "HOLD",
  "confidence": 1-10 (how confident are you in this verdict),
  "reasoning": "3-4 sentence analysis explaining your verdict based on the specific news above. Be concrete, cite specific headlines.",
  "catalysts": ["List of 2-3 key catalysts driving your verdict"],
  "risks": ["List of 1-2 key risks to this thesis"],
  "timeframe": "Short-term (days)" or "Medium-term (weeks)" or "Long-term (months)",
  "sentiment_score": 0-100 (0 = extremely bearish, 100 = extremely bullish)
}}

Rules:
- Base your analysis ONLY on the actual news provided — don't make up facts
- Be specific — cite actual headlines in your reasoning
- If news is mixed or neutral, default to HOLD
- Confidence 1-3 means low conviction, 7-10 means high conviction
"""

    try:
        from ai_service import ask_claude_json
        result = ask_claude_json(
            prompt,
            system="You are a senior equity research analyst. Return ONLY valid JSON.",
            max_tokens=600,
            cache_key=f"news_verdict:{symbol}:{len(news)}",
            cache_ttl=300,  # 5 min cache
        )

        if isinstance(result, dict) and "verdict" in result:
            result["symbol"] = symbol
            result["news_count"] = len(news)
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            return result

    except Exception as e:
        logger.error("News verdict generation failed for %s: %s", symbol, e)

    # ── Fallback: keyword-based sentiment analysis ──
    logger.info("Using fallback sentiment analysis for %s", symbol)
    return _fallback_verdict(symbol, news, current_price)


def _fallback_verdict(symbol: str, news: List[Dict], price: float = None) -> Dict:
    """Rule-based sentiment analysis when Claude is unavailable."""
    BULLISH = {
        "beat", "beats", "surge", "surges", "soar", "rally", "upgrade",
        "record", "growth", "bullish", "breakthrough", "profit", "buy",
        "outperform", "strong", "boost", "gain", "positive", "raise",
        "upside", "innovative", "exceeds", "dividend", "acquisition",
    }
    BEARISH = {
        "miss", "misses", "plunge", "crash", "downgrade", "warning",
        "bearish", "loss", "sell", "decline", "fall", "risk", "concern",
        "layoff", "cut", "weak", "negative", "lawsuit", "probe",
        "investigation", "recall", "tariff", "delay",
    }

    score = 0
    catalysts = []
    risks = []

    for n in news[:12]:
        h = (n.get("headline") or "").lower()
        words = set(h.split())

        bull_hits = words & BULLISH
        bear_hits = words & BEARISH

        if bull_hits:
            score += len(bull_hits)
            if len(catalysts) < 3:
                catalysts.append(n["headline"][:80])
        if bear_hits:
            score -= len(bear_hits)
            if len(risks) < 2:
                risks.append(n["headline"][:80])

    # Normalize score to 0-100
    max_possible = len(news[:12]) * 2
    normalized = max(0, min(100, int(50 + (score / max(max_possible, 1)) * 50)))

    if normalized >= 60:
        verdict, confidence = "BUY", min(10, 3 + abs(score))
    elif normalized <= 40:
        verdict, confidence = "SELL", min(10, 3 + abs(score))
    else:
        verdict, confidence = "HOLD", 4

    top_headlines = [n["headline"][:60] for n in news[:3]]
    reasoning = f"Based on {len(news)} recent news articles for {symbol}. "
    if score > 0:
        reasoning += f"Headlines lean bullish with positive catalysts including: {top_headlines[0]}. "
    elif score < 0:
        reasoning += f"Headlines lean bearish with concerns around: {top_headlines[0]}. "
    else:
        reasoning += f"Headlines show mixed sentiment. "
    reasoning += f"Overall news sentiment score: {normalized}/100."

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
        "catalysts": catalysts[:3] or ["No strong catalysts detected"],
        "risks": risks[:2] or ["General market conditions"],
        "timeframe": "Short-term (days)",
        "sentiment_score": normalized,
        "news_count": len(news),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "rule_based",
    }
