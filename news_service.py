"""
News and economic events service.
Fetches financial news (FMP, Finnhub) and filters to High-Impact only (earnings, Fed, M&A, volatility).
"""
import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Keywords that indicate high-impact, market-moving news (earnings, Fed, M&A, volatility)
HIGH_IMPACT_KEYWORDS = [
    "earnings", "beat", "miss", "eps", "revenue beat", "guidance",
    "fed", "fomc", "rate cut", "rate hike", "powell", "interest rate", "rate decision",
    "merger", "acquisition", "m&a", "takeover", "deal",
    "cpi", "inflation", "jobs report", "payroll", "unemployment",
    "volatility", "surge", "plunge", "rally", "sell-off", "correction",
    "fda", "approval", "lawsuit", "sec", "investigation",
    "dividend", "buyback", "split",
]
HIGH_IMPACT_PATTERN = re.compile("|".join(re.escape(k) for k in HIGH_IMPACT_KEYWORDS), re.I)


def _score_impact(item: Dict) -> int:
    """Score 0-10; higher = more market-moving. Title weighted more than summary."""
    title = (item.get("title") or "").lower()
    summary = (item.get("summary") or item.get("text") or "").lower()
    text = title + " " + summary[:400]
    matches = HIGH_IMPACT_PATTERN.findall(text)
    if not matches:
        return 0
    # More matches + title match = higher score
    score = min(len(matches) * 2, 6)
    if HIGH_IMPACT_PATTERN.search(title):
        score += 4
    return min(score, 10)


def filter_high_impact_news(news: List[Dict], min_score: int = 3, max_items: int = 25) -> List[Dict]:
    """Keep only high-impact headlines; sort by impact score descending."""
    scored = [(item, _score_impact(item)) for item in news]
    scored = [(item, s) for item, s in scored if s >= min_score]
    scored.sort(key=lambda x: -x[1])
    return [item for item, _ in scored[:max_items]]


def fetch_financial_news(limit: int = 15, high_impact_only: bool = True) -> List[Dict]:
    """Fetch real-time news from FMP (primary) or Finnhub; optionally filter to high-impact only."""
    news = []
    # 1) FMP (Financial Modeling Prep) – real-time stock news
    if FMP_API_KEY:
        try:
            from fmp_client import stock_news
            raw = stock_news(limit=min(limit * 2, 50))  # fetch extra for filtering
            for n in raw:
                ts = n.get("time")
                if isinstance(ts, str) and ts:
                    try:
                        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        ts = int(t.timestamp())
                    except Exception:
                        ts = int(datetime.now(timezone.utc).timestamp())
                elif not ts:
                    ts = int(datetime.now(timezone.utc).timestamp())
                news.append({
                    "title": n.get("title") or "",
                    "summary": (n.get("text") or "")[:300],
                    "url": n.get("url") or "#",
                    "source": n.get("source") or "FMP",
                    "time": ts,
                    "tickers": n.get("tickers") or [],
                })
            if news:
                if high_impact_only:
                    news = filter_high_impact_news(news, min_score=2, max_items=limit)
                else:
                    news = news[:limit]
                return news
        except Exception as e:
            logger.warning("FMP news fetch failed: %s", e)
    # 2) Finnhub
    if FINNHUB_API_KEY:
        try:
            r = requests.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "token": FINNHUB_API_KEY},
                timeout=10,
            )
            if r.ok:
                data = r.json()
                for i, item in enumerate(data[: limit * 2]):
                    news.append({
                        "title": item.get("headline", ""),
                        "summary": (item.get("summary") or "")[:300],
                        "url": item.get("url", "#"),
                        "source": item.get("source", "Finnhub"),
                        "time": item.get("datetime", 0),
                        "tickers": item.get("related", "").split(",") if item.get("related") else [],
                    })
                if news:
                    if high_impact_only:
                        news = filter_high_impact_news(news, min_score=2, max_items=limit)
                    else:
                        news = news[:limit]
                    return news
        except Exception as e:
            logger.warning("Finnhub news fetch failed: %s", e)
    return _sample_news(limit)


    # 3) yfinance Fallback (Real News)
    try:
        import yfinance as yf
        # Fetch news for a mix of major indices and popular tickers to get broad market news
        # SPY/QQQ for macro, others for sector-specific buzz
        tickers = ["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "AMD", "TSLA", "AMZN", "GOOGL", "META"] 
        all_news = []
        seen_urls = set()
        
        for sym in tickers:
            try:
                t = yf.Ticker(sym)
                # yfinance .news is a list of dicts:
                # [{'uuid': '...', 'title': '...', 'publisher': '...', 'link': '...', 'providerPublishTime': ...}]
                rec_news = t.news
                for item in rec_news:
                    link = item.get("link")
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    
                    # Parse timestamp
                    ts = item.get("providerPublishTime")
                    if not ts:
                        ts = int(datetime.now(timezone.utc).timestamp())
                    
                    all_news.append({
                        "title": item.get("title"),
                        "summary": item.get("title"),  # yfinance often lacks summary, use title
                        "url": link,
                        "source": item.get("publisher"),
                        "time": ts,
                        "tickers": item.get("relatedTickers", [sym]),
                    })
            except Exception:
                continue

        if all_news:
            # Sort by time desc
            all_news.sort(key=lambda x: x["time"], reverse=True)
            
            if high_impact_only:
                 # Filter but ensure we return at least some news if everything is filtered out
                 high_impact = filter_high_impact_news(all_news, min_score=2, max_items=limit)
                 if high_impact:
                     return high_impact
                 # If no high impact found, return top general news instead of nothing
                 return all_news[:limit]
            
            return all_news[:limit]

    except Exception as e:
        logger.warning("yfinance news fetch failed: %s", e)

    return _sample_news(limit)


def _sample_news(limit: int) -> List[Dict]:
    """Sample financial news for demo when no API key."""
    now = datetime.now(timezone.utc)
    samples = [
        {"title": "CPI Report Shows Inflation Cooled to 3.2% Year-Over-Year", "topic": "inflation", "source": "Reuters"},
        {"title": "Fed Holds Rates Steady, Signals One Cut in 2025", "topic": "fed", "source": "Bloomberg"},
        {"title": "Job Growth Beats Expectations; Unemployment Holds at 3.7%", "topic": "jobs", "source": "CNBC"},
        {"title": "Tech Earnings Beat Estimates; Megacaps Lead Rally", "topic": "earnings", "source": "MarketWatch"},
        {"title": "Oil Prices Rise on Supply Concerns", "topic": "commodities", "source": "Reuters"},
        {"title": "Treasury Yields Fall After Soft Retail Sales Data", "topic": "rates", "source": "Bloomberg"},
        {"title": "Dollar Weakens as Traders Bet on Rate Cuts", "topic": "fx", "source": "Reuters"},
        {"title": "Housing Starts Drop More Than Expected", "topic": "housing", "source": "CNBC"},
        {"title": "Consumer Confidence Rises to Five-Month High", "topic": "sentiment", "source": "MarketWatch"},
        {"title": "PCE Inflation Data Due Thursday; Fed Watchers on Alert", "topic": "inflation", "source": "Reuters"},
    ]
    out = []
    for i, s in enumerate(samples[:limit]):
        ts = (now - timedelta(hours=i * 2)).timestamp()
        out.append({
            "title": s["title"],
            "summary": "Market-moving headline. Check source for full story.",
            "url": "#",
            "source": s["source"],
            "time": int(ts),
            "topic": s.get("topic", ""),
        })
    return out


def detect_economic_events(news: List[Dict]) -> List[Dict]:
    """Detect economic data releases (CPI, jobs, Fed, etc.) from news."""
    events = []
    keywords = {
        "inflation": ["cpi", "inflation", "pce", "consumer price", "core inflation"],
        "jobs": ["jobs report", "nonfarm", "employment", "unemployment", "payrolls", "job growth"],
        "fed": ["fed", "fomc", "interest rate", "powell", "rate cut", "rate decision"],
        "retail": ["retail sales", "consumer spending"],
        "gdp": ["gdp", "growth", "quarterly growth"],
    }
    for n in news:
        title = (n.get("title") or "").lower()
        topic = n.get("topic", "")
        for event_type, terms in keywords.items():
            if any(t in title for t in terms) or (topic and topic in event_type):
                events.append({
                    "type": event_type,
                    "title": n.get("title", ""),
                    "source": n.get("source", ""),
                    "time": n.get("time"),
                })
                break
    return events


def get_actionable_advice(events: List[Dict], news: List[Dict]) -> List[Dict]:
    """
    For each major economic event (e.g. inflation data), return:
    - action: "jump_in" | "stay_out" | "selective"
    - reason: short explanation why
    - event_type, title
    """
    advice_list = []
    seen = set()
    for ev in events:
        etype = ev.get("type", "")
        if etype in seen:
            continue
        seen.add(etype)
        action, reason = _advice_for_event(etype, ev, news)
        advice_list.append({
            "event_type": etype,
            "title": ev.get("title", ""),
            "action": action,
            "reason": reason,
            "source": ev.get("source", ""),
        })
    # If no events detected, add general market advice based on latest news
    if not advice_list and news:
        action, reason = _general_advice(news)
        advice_list.append({
            "event_type": "market",
            "title": "General market view",
            "action": action,
            "reason": reason,
            "source": "Analysis",
        })
    return advice_list


def _advice_for_event(event_type: str, event: Dict, news: List[Dict]) -> tuple:
    """Return (action, reason) for a given event type. Simulated logic for demo."""
    title = (event.get("title") or "").lower()
    # Inflation
    if event_type == "inflation":
        if "cooled" in title or "below" in title or "drop" in title or "fall" in title:
            return (
                "jump_in",
                "Inflation cooling is positive for risk assets. Lower inflation reduces pressure on the Fed to keep rates high, which typically supports stock valuations. Consider adding exposure to growth and quality names.",
            )
        if "hot" in title or "above" in title or "rise" in title or "surge" in title:
            return (
                "stay_out",
                "Hot inflation keeps the Fed hawkish and supports higher-for-longer rates. That usually weighs on multiples and risk appetite. Prefer staying defensive or reducing size until the next data point.",
            )
        return (
            "selective",
            "Inflation data in line with expectations. No clear signal—stay selective: favor sectors that benefit from stable rates (e.g. quality growth, some cyclicals) and avoid rate-sensitive names until trend is clear.",
        )
    # Fed / rates
    if event_type == "fed":
        if "cut" in title or "dovish" in title or "hold" in title:
            return (
                "jump_in",
                "Fed signaling cuts or holding steady is generally supportive for equities. Lower discount rates and improved liquidity support risk-on moves. Consider adding exposure on pullbacks.",
            )
        if "hike" in title or "hawkish" in title:
            return (
                "stay_out",
                "Hawkish Fed or rate hikes increase discount rates and can compress multiples. Prefer staying in cash or defensive names until the rate path becomes clearer.",
            )
        return (
            "selective",
            "Fed message is mixed. Stay selective: overweight quality and earnings visibility; avoid highly leveraged or long-duration growth until the next Fed meeting.",
        )
    # Jobs
    if event_type == "jobs":
        if "beat" in title or "strong" in title or "rise" in title:
            return (
                "selective",
                "Strong jobs data supports soft-landing hopes but can delay rate cuts. Cyclicals and value may do better than long-duration growth. Be selective rather than all-in or all-out.",
            )
        if "miss" in title or "weak" in title or "drop" in title:
            return (
                "jump_in",
                "Weaker jobs data can bring forward Fed cut expectations, which often supports growth and risk assets. Consider adding quality growth or index exposure on dips.",
            )
        return (
            "selective",
            "Jobs report in line. No major shift in Fed pricing—stay with your plan and favor quality names.",
        )
    # Default
    return (
        "selective",
        "Economic data can move markets quickly. Prefer defined risk and avoid chasing. Wait for clarity before sizing up.",
    )


def _general_advice(news: List[Dict]) -> tuple:
    """General market advice when no specific event is detected."""
    titles = " ".join((n.get("title") or "").lower() for n in news[:5])
    if "rally" in titles or "beat" in titles or "surge" in titles:
        return (
            "jump_in",
            "Headlines point to positive momentum and strong earnings. Consider adding exposure in quality names with clear catalysts, using strict risk management.",
        )
    if "fall" in titles or "recession" in titles or "miss" in titles:
        return (
            "stay_out",
            "Negative headlines suggest caution. Reduce risk or stay in cash until volatility subsides and catalysts turn more favorable.",
        )
    return (
        "selective",
        "Mixed signals in the news. Stay selective: focus on high-conviction ideas and keep position sizes moderate until a clearer trend emerges.",
    )


def get_news_and_advice(limit_news: int = 15) -> Dict:
    """Fetch news, detect events, and return news + actionable advice."""
    news = fetch_financial_news(limit=limit_news)
    events = detect_economic_events(news)
    advice = get_actionable_advice(events, news)
    return {
        "news": news,
        "economic_events": events,
        "advice": advice,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

# -----------------------------------------------------------------------------
# RSS Feed Real-Time Financial News (Live News Hub)
# -----------------------------------------------------------------------------
import feedparser
import hashlib
from concurrent.futures import ThreadPoolExecutor

RSS_SOURCES = {
    'Reuters Business':  'https://feeds.reuters.com/reuters/businessNews',
    'Reuters Markets':   'https://feeds.reuters.com/reuters/marketsNews',
    'CNBC Top':          'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
    'MarketWatch':       'https://feeds.marketwatch.com/marketwatch/topstories/',
    'Yahoo Finance':     'https://finance.yahoo.com/rss/topfinstories',
}

def _parse_one_feed(name, url):
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:15]:
            pub = entry.get('published_parsed')
            pub_dt = datetime(*pub[:6], tzinfo=timezone.utc).isoformat() if pub else None
            articles.append({
                'id':        hashlib.md5(entry.get('link','').encode()).hexdigest()[:12],
                'title':     entry.get('title', ''),
                'summary':   entry.get('summary', '')[:300],
                'url':       entry.get('link', ''),
                'source':    name,
                'published': pub_dt,
            })
        return articles
    except:
        return []

def fetch_all_rss(limit=60):
    all_articles, seen = [], set()
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(_parse_one_feed, n, u) for n, u in RSS_SOURCES.items()]
        for f in futures:
            for art in f.result():
                if art['id'] not in seen:
                    seen.add(art['id'])
                    all_articles.append(art)
                    
    all_articles.sort(key=lambda x: x.get('published') or '', reverse=True)
    return all_articles[:limit]
