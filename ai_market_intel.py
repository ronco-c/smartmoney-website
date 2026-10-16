"""
AI Market Intelligence Engine
─────────────────────────────
Background-running AI engine that continuously analyzes news feeds,
detects hot stocks, surfaces breaking news, and generates actionable
market intelligence every few minutes via Claude.

Usage:
    from ai_market_intel import get_market_pulse, start_pulse_engine, stop_pulse_engine
"""

import re
import time
import logging
import threading
import hashlib
from datetime import datetime, timezone
from collections import Counter
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
PULSE_INTERVAL_SECONDS = 300    # Generate pulse every 5 min
TICKER_PATTERN = re.compile(
    r'\b([A-Z]{1,5})\b'
)

# Known tickers to match against (prevents matching random words like "A", "I", "IT")
KNOWN_TICKERS = {
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK',
    'JPM', 'JNJ', 'V', 'UNH', 'XOM', 'PG', 'MA', 'HD', 'CVX', 'MRK',
    'ABBV', 'PEP', 'KO', 'PFE', 'COST', 'AVGO', 'TMO', 'MCD', 'WMT',
    'CSCO', 'ACN', 'ABT', 'CRM', 'LIN', 'AMD', 'TXN', 'DHR', 'ADBE',
    'NFLX', 'ORCL', 'INTC', 'QCOM', 'INTU', 'AMAT', 'ISRG', 'BKNG',
    'ADP', 'MDLZ', 'REGN', 'VRTX', 'ADI', 'PANW', 'LRCX', 'SNPS',
    'BA', 'GE', 'CAT', 'MMM', 'HON', 'RTX', 'LMT', 'NOC', 'GD',
    'DIS', 'PYPL', 'SQ', 'COIN', 'HOOD', 'RBLX', 'SNAP', 'UBER', 'LYFT',
    'SPY', 'QQQ', 'DIA', 'IWM', 'GLD', 'TLT', 'VXX', 'XLE', 'XLF',
    'XLK', 'XLV', 'XLU', 'XLI', 'XLP', 'XLY', 'XLRE', 'XLB',
    'TSM', 'ASML', 'SHOP', 'PLTR', 'ABNB', 'DDOG', 'NET', 'CRWD',
    'ZS', 'SNOW', 'MDB', 'RIVN', 'LCID', 'NIO', 'LI', 'XPEV',
    'GME', 'AMC', 'SOFI', 'MARA', 'RIOT', 'MSTR', 'SMCI', 'ARM',
    'LLY', 'NVO', 'MRNA', 'BNTX',
    'USO', 'SLV', 'ARKK', 'SOXL', 'TQQQ',
    'AAL', 'DAL', 'UAL', 'LUV',
    'DELL', 'HPE', 'IBM',
    'WFC', 'BAC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'KRE',
    'AI', 'PATH', 'UPST', 'AFRM',
}

# ── State ─────────────────────────────────────────────────────────────────────
_pulse_thread = None
_stop_event = threading.Event()
_lock = threading.Lock()

_latest_pulse = None
_latest_hot_stocks = []


# ═══════════════════════════════════════════════════════════════════════════════
#  HOT STOCK DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_hot_stocks(articles: List[Dict]) -> List[Dict]:
    """
    Scan RSS headlines for ticker mentions, count frequency,
    and flag stocks mentioned 2+ times across different sources.
    """
    ticker_mentions = Counter()
    ticker_sources = {}
    ticker_headlines = {}

    for art in articles:
        text = (art.get('title', '') + ' ' + art.get('summary', '')).upper()
        # Extract tickers from text
        found_tickers = set()
        for match in TICKER_PATTERN.finditer(text):
            ticker = match.group(1)
            if ticker in KNOWN_TICKERS and len(ticker) >= 2:
                found_tickers.add(ticker)

        source = art.get('source', 'Unknown')
        for ticker in found_tickers:
            ticker_mentions[ticker] += 1
            if ticker not in ticker_sources:
                ticker_sources[ticker] = set()
                ticker_headlines[ticker] = []
            ticker_sources[ticker].add(source)
            if len(ticker_headlines[ticker]) < 3:
                ticker_headlines[ticker].append(art.get('title', ''))

    # Filter: 2+ mentions or from 2+ sources
    hot = []
    for ticker, count in ticker_mentions.most_common(15):
        sources = ticker_sources.get(ticker, set())
        if count >= 2 or len(sources) >= 2:
            # Determine sentiment from headlines
            headlines = ticker_headlines.get(ticker, [])
            sentiment = _quick_sentiment(headlines)

            hot.append({
                'ticker': ticker,
                'mentions': count,
                'sources': list(sources),
                'num_sources': len(sources),
                'headlines': headlines,
                'sentiment': sentiment,
                'heat_score': count * 2 + len(sources) * 3,
            })

    hot.sort(key=lambda x: -x['heat_score'])
    return hot[:10]


def _quick_sentiment(headlines: List[str]) -> str:
    """Quick keyword-based sentiment from headlines."""
    text = ' '.join(headlines).lower()
    pos = sum(1 for w in ['beat', 'surge', 'rally', 'upgrade', 'buy', 'rise',
                           'soar', 'jump', 'gain', 'bullish', 'record', 'high']
              if w in text)
    neg = sum(1 for w in ['miss', 'drop', 'fall', 'cut', 'sell', 'crash',
                           'plunge', 'warning', 'risk', 'bearish', 'concern', 'low']
              if w in text)
    if pos > neg:
        return 'bullish'
    elif neg > pos:
        return 'bearish'
    return 'neutral'


# ═══════════════════════════════════════════════════════════════════════════════
#  AI MARKET PULSE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_market_pulse() -> Dict:
    """
    Generate a comprehensive AI market pulse by analyzing current RSS headlines,
    live signals, and hot stock data.
    Returns a structured dict with all intelligence sections.
    """
    from news_service import fetch_all_rss

    # 1. Fetch latest RSS articles
    articles = fetch_all_rss(limit=60)
    if not articles:
        return _empty_pulse("No news articles available")

    # 2. Detect hot stocks
    hot_stocks = detect_hot_stocks(articles)

    # 3. Get live scanner signals if available
    live_signals = []
    try:
        from news_scanner import get_live_signals
        live_signals = get_live_signals(limit=10)
    except Exception:
        pass

    # 4. Get market indices
    market_data = ""
    try:
        from db import get_cache
        cached = get_cache("market_indices:all")
        if cached and cached.get("indices"):
            market_data = ", ".join(
                f"{m['name']} {float(m.get('change_percent', 0)):+.1f}%"
                for m in cached["indices"]
            )
    except Exception:
        pass

    # 5. Build context for Claude
    headlines = [a.get('title', '') for a in articles[:20]]
    headlines_str = '\n'.join(f"  - {h}" for h in headlines)

    hot_str = '\n'.join(
        f"  - {h['ticker']}: {h['mentions']} mentions across {h['num_sources']} sources, "
        f"sentiment: {h['sentiment']}, headlines: {'; '.join(h['headlines'][:2])}"
        for h in hot_stocks[:8]
    ) if hot_stocks else "  No hot stocks detected this cycle."

    signals_str = '\n'.join(
        f"  - [{s.get('headline', '')}] → {len(s.get('signals', []))} signals"
        for s in live_signals[:5]
    ) if live_signals else "  No live trading signals."

    prompt = f"""You are an elite Wall Street market intelligence analyst.
Analyze the following real-time market data and provide a comprehensive market pulse.

═══ CURRENT TIME ═══
{datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M UTC')}

═══ MARKET INDICES ═══
{market_data or 'Market data unavailable'}

═══ LATEST NEWS HEADLINES ═══
{headlines_str}

═══ HOT STOCKS (AI-detected from headline frequency) ═══
{hot_str}

═══ LIVE TRADING SIGNALS (from news scanner) ═══
{signals_str}

Generate a complete market intelligence report. Return ONLY this JSON:
{{
  "market_mood": "RISK ON" or "RISK OFF" or "MIXED" or "CAUTIOUS",
  "mood_emoji": "🟢" or "🔴" or "🟡" or "🟠",
  "mood_reason": "One sentence explaining the current market mood",

  "breaking_digest": [
    {{
      "headline": "The most important headline right now",
      "impact": "high" or "medium" or "low",
      "analysis": "2-sentence analysis of why this matters for traders",
      "affected_tickers": ["SPY", "QQQ"]
    }}
  ],

  "hot_stocks": [
    {{
      "ticker": "NVDA",
      "reason": "2-sentence reason why this stock is hot right now",
      "signal": "BUY" or "SELL" or "WATCH",
      "catalyst": "What's driving the attention (earnings beat, analyst upgrade, etc.)",
      "urgency": "high" or "medium"
    }}
  ],

  "sector_heat": [
    {{
      "sector": "Technology",
      "status": "hot" or "warm" or "cold" or "mixed",
      "emoji": "🔥" or "🌡️" or "❄️" or "🔄",
      "reason": "One sentence about sector outlook"
    }}
  ],

  "recommendations": [
    {{
      "ticker": "AAPL",
      "action": "BUY" or "SELL" or "WATCH",
      "reasoning": "2-3 sentence reasoning with specific catalysts",
      "entry_zone": "$170-175" or "At market",
      "risk": "Stop below $165",
      "timeframe": "Swing (1-2 weeks)" or "Position (1-3 months)"
    }}
  ],

  "risk_radar": [
    {{
      "risk": "Title of the risk",
      "severity": "high" or "medium" or "low",
      "detail": "One sentence explanation",
      "hedge": "Suggested hedge or protection"
    }}
  ],

  "medium_term_picks": [
    {{
      "ticker": "NVDA",
      "company_name": "NVIDIA Corporation",
      "sector": "Technology",
      "action": "BUY",
      "buy_reason": "3-4 sentence detailed reason why this stock is a medium-term buy right now. Reference specific catalysts from today's news, earnings momentum, institutional flows, sector tailwinds, or valuation opportunity. Be specific with numbers.",
      "entry_zone": "$850-870",
      "target_price": "$1,000",
      "stop_loss": "Below $780",
      "timeframe": "1-3 months",
      "catalyst": "One sentence: the primary catalyst driving this opportunity",
      "risk": "One sentence: the main risk that could invalidate this thesis",
      "conviction": 8
    }}
  ],

  "one_liner": "A single punchy one-liner summary of the market right now (max 15 words)"
}}

Rules:
- breaking_digest: exactly 3 items, most important first
- hot_stocks: 3-5 items from the detected hot stocks OR other stocks driving today's action
- sector_heat: exactly 6 main sectors (Technology, Energy, Healthcare, Financial, Consumer, Industrial)
- recommendations: exactly 3-4 items, actionable with specific entry/exit
- risk_radar: exactly 2-3 items
- medium_term_picks: exactly 3-5 stocks. These are MEDIUM-TERM buys (1-3 months). Focus on stocks with strong catalysts from current news, institutional accumulation, or sector momentum. Each must have a detailed buy_reason explaining WHY to buy NOW for the medium term.
- Be specific with tickers and numbers. No vague advice.
- Base everything on the ACTUAL headlines and data above, not generic advice.
- All text must be in English.
"""

    try:
        from ai_service import ask_gemini_json as ask_claude_json
        cache_key = f"market_pulse:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')[:-1]}"
        result = ask_claude_json(
            prompt,
            system='You are a Goldman Sachs senior strategist. Return ONLY valid JSON. No markdown.',
            max_tokens=2000,
            cache_key=cache_key,
            cache_ttl=PULSE_INTERVAL_SECONDS
        )

        if isinstance(result, dict) and 'error' not in result:
            result['_meta'] = {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'articles_analyzed': len(articles),
                'hot_stocks_detected': len(hot_stocks),
                'live_signals_count': len(live_signals),
            }
            result['raw_hot_stocks'] = hot_stocks
            return result

    except Exception as e:
        logger.error("Market pulse AI generation failed: %s", e)

    # Fallback — return structured data without AI analysis
    return _fallback_pulse(articles, hot_stocks, live_signals)


def _empty_pulse(reason: str) -> Dict:
    return {
        'market_mood': 'MIXED',
        'mood_emoji': '🟡',
        'mood_reason': reason,
        'breaking_digest': [],
        'hot_stocks': [],
        'sector_heat': [],
        'recommendations': [],
        'risk_radar': [],
        'one_liner': 'Waiting for market data...',
        'raw_hot_stocks': [],
        '_meta': {'generated_at': datetime.now(timezone.utc).isoformat(), 'error': reason},
    }


def _fallback_pulse(articles, hot_stocks, live_signals) -> Dict:
    """Build a basic pulse from raw data when Claude is unavailable."""
    breaking = []
    for art in articles[:3]:
        breaking.append({
            'headline': art.get('title', ''),
            'impact': 'medium',
            'analysis': art.get('summary', '')[:200],
            'affected_tickers': [],
        })

    hot = []
    for hs in hot_stocks[:5]:
        hot.append({
            'ticker': hs['ticker'],
            'reason': f"Mentioned {hs['mentions']} times across {hs['num_sources']} sources",
            'signal': 'WATCH',
            'catalyst': hs['headlines'][0] if hs['headlines'] else 'Multiple news mentions',
            'urgency': 'high' if hs['heat_score'] > 10 else 'medium',
        })

    return {
        'market_mood': 'MIXED',
        'mood_emoji': '🟡',
        'mood_reason': 'AI analysis temporarily unavailable — showing raw data',
        'breaking_digest': breaking,
        'hot_stocks': hot,
        'sector_heat': [],
        'recommendations': [],
        'risk_radar': [],
        'one_liner': 'Market intelligence loading...',
        'raw_hot_stocks': hot_stocks,
        '_meta': {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'articles_analyzed': len(articles),
            'fallback': True,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def get_market_pulse() -> Optional[Dict]:
    """Return the latest cached market pulse."""
    with _lock:
        return _latest_pulse


def get_hot_stocks() -> List[Dict]:
    """Return the latest detected hot stocks."""
    with _lock:
        return list(_latest_hot_stocks)


def start_pulse_engine():
    """Start the background market pulse engine."""
    global _pulse_thread
    if _pulse_thread and _pulse_thread.is_alive():
        logger.info("[MarketPulse] Already running.")
        return

    _stop_event.clear()
    _pulse_thread = threading.Thread(
        target=_pulse_loop,
        daemon=True,
        name="market-pulse"
    )
    _pulse_thread.start()
    logger.info("[MarketPulse] Engine started (interval: %ds)", PULSE_INTERVAL_SECONDS)


def stop_pulse_engine():
    """Stop the background market pulse engine."""
    global _pulse_thread
    _stop_event.set()
    logger.info("[MarketPulse] Stop requested.")
    _pulse_thread = None


def is_pulse_running() -> bool:
    return _pulse_thread is not None and _pulse_thread.is_alive()


def _pulse_loop():
    """Main loop: generate pulse at regular intervals."""
    global _latest_pulse, _latest_hot_stocks
    time.sleep(10)  # Initial delay for app startup
    logger.info("[MarketPulse] First pulse generating...")

    while not _stop_event.is_set():
        try:
            pulse = generate_market_pulse()
            with _lock:
                _latest_pulse = pulse
                _latest_hot_stocks = pulse.get('raw_hot_stocks', [])
            logger.info("[MarketPulse] ✓ Pulse generated (%d hot stocks, mood: %s)",
                        len(_latest_hot_stocks),
                        pulse.get('market_mood', '?'))
        except Exception as e:
            logger.error("[MarketPulse] Generation error: %s", e, exc_info=True)

        for _ in range(PULSE_INTERVAL_SECONDS):
            if _stop_event.is_set():
                break
            time.sleep(1)

    logger.info("[MarketPulse] Engine stopped.")
