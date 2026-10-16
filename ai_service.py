# Install:
# pip install google-genai feedparser openai

import os
import json
import time
import hashlib
from db import get_cache, set_cache
import google.genai as genai
from google.genai import types

# Make sure GEMINI_API_KEY is an environment variable.
try:
    client = genai.Client()
except Exception as e:
    print(f"Warning: Could not initialize Gemini Client: {e}")
    client = None

def ask_gemini(prompt, system=None, max_tokens=1000, cache_key=None, cache_ttl=600):
    if not client:
        return "Error: Gemini API Key not configured. Please set GEMINI_API_KEY environment variable."
        
    if cache_key:
        cached = get_cache(cache_key)
        if cached and cached.get('text'):
            return cached['text']
            
    try:
        config_kwargs = {"max_output_tokens": max_tokens}
        if system:
            config_kwargs["system_instruction"] = system
            
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs)
        )
        text = response.text
        if cache_key:
            set_cache(cache_key, {'text': text, 'ts': time.time()}, ttl=cache_ttl)
        return text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Error: AI Service Unavailable"

def _extract_json(text):
    """Robustly extract JSON from AI response text, handling markdown fences and extras."""
    import re
    if not text or not isinstance(text, str):
        return None

    # Strategy 1: Try parsing raw text directly
    try:
        return json.loads(text.strip())
    except Exception:
        pass

    # Strategy 2: Extract from markdown code fence ```json ... ``` or ``` ... ```
    fence_patterns = [
        r'```(?:json|JSON)?\s*\n?(.*?)```',   # ```json ... ```
        r'`([\{\[].*?[\}\]])`',                  # inline backtick `{...}`
    ]
    for pattern in fence_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass

    # Strategy 3: Find first { or [ and match to last } or ]
    first_brace = -1
    last_brace = -1
    for i, c in enumerate(text):
        if c in ('{', '['):
            first_brace = i
            break
    for i in range(len(text) - 1, -1, -1):
        if text[i] in ('}', ']'):
            last_brace = i
            break
    if first_brace >= 0 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except Exception:
            pass

    return None


def ask_gemini_json(prompt, system=None, max_tokens=1000, cache_key=None, cache_ttl=600):
    sys_json = (system or '') + '\nRespond ONLY with valid JSON. No markdown code fences. No explanation. Just the raw JSON object.'
    text = ask_gemini(prompt, sys_json, max_tokens, cache_key, cache_ttl)

    result = _extract_json(text)
    if result is not None:
        return result

    # Retry once with stronger instruction if first attempt failed
    print(f"[AI] JSON parse failed on first attempt ({len(text or '')} chars). Retrying...")
    retry_prompt = prompt + "\n\nCRITICAL: Return ONLY raw JSON. No markdown. No code fences. No explanation text."
    text2 = ask_gemini(retry_prompt, sys_json, max_tokens, None, None)
    result2 = _extract_json(text2)
    if result2 is not None:
        return result2

    print(f"[AI] JSON parse failed after retry. Raw text: {(text or '')[:500]}")
    return {'error': 'parse_failed', 'raw': text}

def generate_morning_brief(watchlist, market_indices, top_mover):
    tickers = ', '.join(watchlist) if watchlist else 'none set'
    indices = ', '.join(
        f"{m['name']} {m.get('change_percent',0):+.1f}%" 
        for m in market_indices
    )
    mover_txt = f"{top_mover.get('ticker','N/A')} ({top_mover.get('institution','N/A')} +{top_mover.get('change_pct','?')})"
    
    prompt = f'''
    You are a senior market analyst. Write a 4-sentence morning brief.
    Today indices: {indices}
    User watchlist: {tickers}
    Top institutional mover overnight: {mover_txt}
    
    Cover: 1) Market mood  2) One watchlist stock to watch
    3) Institutional move insight  4) One risk or opportunity
    Tone: Sharp and direct like a Bloomberg terminal alert. No bullets. Prose only.
    '''
    
    from datetime import datetime
    cache_key = f'morning_brief:{datetime.now().strftime("%Y%m%d%H")}'
    return ask_gemini(
        prompt,
        system='You are a professional hedge fund analyst.',
        max_tokens=400, 
        cache_key=cache_key, 
        cache_ttl=3600
    )

ANALYST_SYSTEM = '''You are a senior equity research analyst at a top investment bank.
Write sharp, honest, data-driven analysis. Back every claim with the specific numbers provided.
Present both bull and bear cases fairly. Never use vague hedging language.'''

def analyze_stock(symbol, stock_data):
    q = stock_data.get('quote', {})
    analyst = stock_data.get('analyst', {})
    holdings = stock_data.get('holdings', [])
    km = stock_data.get('key_metrics', {})
    sentiment = stock_data.get('sentiment', 50)
    news = stock_data.get('news', [])
    
    adds = sum(1 for h in holdings if '+' in str(h.get('position_change','')))
    reduces = len(holdings) - adds
    news_titles = '; '.join(n.get('title','') for n in news[:5])
    
    prompt = f'''
    Analyze {symbol} as an investment. Be precise.
    Price: {q.get('price')} | Change: {q.get('change_percent')}%
    Sector: {q.get('sector')} | Beta: {q.get('beta')}
    P/E: {km.get('pe_ratio')} | EPS: {q.get('eps')}
    Analyst target: {analyst.get('avg_price_target')} ({analyst.get('upside_percent')}% upside)
    Institutional flow: {adds} adding, {reduces} reducing
    Insider cluster buys: {stock_data.get('insider_cluster_buys')}
    Sentiment: {sentiment}/100
    Recent headlines: {news_titles}
    
    Write EXACTLY this (no other text):
    BULL_CASE: [2-3 sentences with specific numbers]
    BEAR_CASE: [2-3 sentences on real risks]
    SMART_MONEY: [1-2 sentences on institutional signal]
    VERDICT: BUY or HOLD or SELL | [one sentence reason]
    '''
    
    text = ask_gemini(
        prompt, 
        ANALYST_SYSTEM, 
        max_tokens=500,
        cache_key=f'stock_analysis:{symbol}', 
        cache_ttl=1800
    )
    
    result = {}
    for section in ['BULL_CASE','BEAR_CASE','SMART_MONEY','VERDICT']:
        if section+':' in text:
            result[section.lower()] = text.split(section+':')[1].split('\n')[0].strip()
            
    return result

def generate_portfolio_allocation(amount, risk, sectors, top_picks):
    """Legacy wrapper — calls the new smart portfolio generator."""
    return generate_smart_portfolio(
        amount=amount, risk=risk, sectors=sectors, top_picks=top_picks,
        horizon='1y', goal='growth', exclude_sectors=[], existing_holdings=[],
        news_headlines=[], market_summary='', rebalance_mode='alert_rebalance'
    )


def generate_smart_portfolio(
    amount, risk, sectors, top_picks,
    horizon='1y', goal='growth', exclude_sectors=None,
    existing_holdings=None, news_headlines=None,
    market_summary='', rebalance_mode='alert_rebalance'
):
    """
    Full AI portfolio generation with live context, per-stock reasoning,
    risk flags, scores, entry/exit strategies, and smart allocation.
    """
    from datetime import datetime

    exclude_sectors = exclude_sectors or []
    existing_holdings = existing_holdings or []
    news_headlines = news_headlines or []

    # Build candidate stock descriptions
    picks_text = '\n'.join(
        f'- {p.get("ticker", p.get("symbol", "?"))}: '
        f'${p.get("price", "?")} | '
        f'{p.get("sector","?")} sector | '
        f'{p.get("upside_pct","?")}% analyst upside | '
        f'{p.get("num_institutions","?")} institutions | '
        f'today {p.get("change_percent", 0):+.1f}%'
        for p in top_picks[:20]
    )

    # Horizon descriptions
    horizon_map = {
        '3m': '3 months (short-term swing trades, momentum-focused)',
        '1y': '1 year (medium-term, blend of growth and value)',
        '3-5y': '3-5 years (long-term growth, tolerate volatility)',
        '10y+': '10+ years (buy-and-hold, compound growth, emphasize quality)',
    }
    horizon_desc = horizon_map.get(horizon, horizon)

    # Goal descriptions
    goal_map = {
        'growth': 'Maximum capital appreciation — prioritize high-growth companies',
        'income': 'Dividend income — prioritize high-yield, stable payers',
        'preservation': 'Capital preservation — prioritize stability, low volatility, bonds/ETFs',
        'speculation': 'Speculation — high-risk/high-reward, small caps, momentum plays',
    }
    goal_desc = goal_map.get(goal, goal)

    # Risk allocation rules
    risk_rules = {
        'conservative': 'Max 15% per stock. Prefer ETFs and large caps. Cash buffer 15%. Avoid volatile names.',
        'moderate': 'Max 25% per stock. Weight by conviction. Cash buffer 10%. Mix growth + value.',
        'aggressive': 'Up to 40% in one high-conviction pick. Cash buffer 5%. Allow small caps and momentum.',
    }

    news_block = '\n'.join(f'  - {h}' for h in news_headlines[:15]) if news_headlines else '  No live news available.'

    excludes_text = ', '.join(exclude_sectors) if exclude_sectors else 'None'
    holdings_text = ', '.join(existing_holdings) if existing_holdings else 'None'

    prompt = f'''You are a professional portfolio manager. Today's date is {datetime.now().strftime("%B %d, %Y")}.

═══ CLIENT PROFILE ═══
Investment: ${amount:,.0f}
Risk level: {risk}
Time horizon: {horizon_desc}
Goal: {goal_desc}
Preferred sectors: {', '.join(sectors) if sectors else 'Diversify broadly'}
Excluded sectors: {excludes_text}
Target stocks to manage: {holdings_text}
Rebalance preference: {rebalance_mode}

═══ ALLOCATION RULES ═══
{risk_rules.get(risk, risk_rules['moderate'])}
- Factor in stock volatility (high beta = lower allocation even in aggressive)
- Factor in correlation (don't put 60% in 3 stocks that all move together)
- Factor in market cap (small caps get less allocation weight due to liquidity risk)
- NEVER equal-weight. Weight by conviction: high conviction + low risk = more weight.

═══ AVAILABLE STOCKS (live data as a starting point) ═══
{picks_text}

═══ TODAY'S MARKET NEWS ═══
{news_block}

═══ MARKET CONTEXT ═══
{market_summary or 'Market data not available — reason from news headlines above.'}

═══ INSTRUCTIONS ═══
Before recommending stocks you MUST:
1. Consider current market conditions as of today
2. Check the news headlines above for any negative catalysts per stock/sector
3. Avoid stocks with serious ongoing negative catalysts UNLESS you flag as contrarian opportunity
4. Never return the same portfolio twice — reason fresh based on current conditions
5. Exclude any stocks in sectors the user wants excluded
6. The user provided "Target stocks to manage". YOU MUST include these stocks in your portfolio allocation, sizing them appropriately.
7. For income goal: include dividend-paying stocks; for preservation: include bond ETFs
8. For short horizons (3m): favor momentum and catalysts; for long (10y+): favor quality compounders
9. You are NOT limited to the AVAILABLE STOCKS. You MUST actively research and include other high-quality stocks that fit the client profile.

Select 5-8 stocks. {'At least 3 sectors.' if not sectors else 'Only select from the preferred sectors.'} Return ONLY this JSON:
{{
  "allocations": [
    {{
      "symbol": "AAPL",
      "company_name": "Apple Inc.",
      "sector": "Technology",
      "allocation_percent": 18.0,
      "dollar_amount": 1800,
      "shares": 9,
      "price": 200.0,
      "reasoning": "2-3 sentences WHY this stock now, tied to current news and user's risk/goal",
      "allocation_logic": "Why this % — e.g. High conviction but volatile, capped at 18%",
      "risk_flags": ["Earnings in 2 weeks", "China revenue exposure"],
      "entry_strategy": "Buy all at once" or "Dollar-cost average over 3 weeks",
      "exit_signal": "Sell if drops below $180 or misses next earnings by >10%",
      "scores": {{
        "momentum": 7,
        "fundamentals": 8,
        "sentiment": 6,
        "valuation": 5
      }},
      "drop_analysis": null
    }}
  ],
  "cash_reserve": 1000,
  "cash_percent": 10.0,
  "rationale": "4-sentence complete investment thesis for this portfolio",
  "risk_note": "Key risk to watch",
  "expected_volatility": "medium",
  "diversification_score": 7,
  "estimated_dividend_yield": 1.2,
  "portfolio_type_mix": {{
    "growth": 3,
    "value": 2,
    "income": 1,
    "etf": 0
  }}
}}

If any stock has dropped 20%+ recently, add a "drop_analysis" field:
{{
  "classification": "value_opportunity" or "falling_knife",
  "reason": "Why it dropped and whether fundamentals support a recovery"
}}

CRITICAL: Use the ACTUAL prices from the available stocks data above. Calculate shares = dollar_amount / price.
All allocation_percent values must sum to (100 - cash_percent).
'''

    return ask_gemini_json(
        prompt,
        system='You are an elite portfolio manager at a top wealth management firm. '
               'Build a fresh, data-driven portfolio based on live market conditions. '
               'Never use the same portfolio twice. Return only valid JSON.',
        max_tokens=2500,
        cache_key=None,
        cache_ttl=None
    )

def explain_stock_move(symbol, change_pct, volume_ratio, news):
    direction = 'up' if change_pct > 0 else 'down'
    vol_desc = ('on unusually high volume' if volume_ratio > 2 else
                'on elevated volume' if volume_ratio > 1.3 else 'on normal volume')
    headlines = '; '.join(n.get('title','') for n in news[:4])
    
    prompt = f'''
    {symbol} is moving {direction} {abs(change_pct):.1f}% today {vol_desc}
    (volume is {volume_ratio:.1f}x the 30-day average).
    Recent headlines: {headlines or 'No major news found.'}
    In EXACTLY 2 sentences, explain why this stock is moving today.
    Be direct. Reference the news if relevant.
    If no clear news, note the volume signal and what it implies.
    '''
    
    from datetime import datetime
    return ask_gemini(
        prompt,
        system='You are a market analyst giving a rapid 2-sentence explanation.',
        max_tokens=120,
        cache_key=f'move:{symbol}:{datetime.now().strftime("%Y%m%d%H")}',
        cache_ttl=1800
    )

def analyze_news_article(title, summary, user_watchlist=None):
    watchlist_note = ''
    if user_watchlist:
        watchlist_note = f'User watchlist (flag if affected): {chr(44).join(user_watchlist)}'

    prompt = f'''
    You are a senior institutional trading analyst. Analyze this headline with the depth
    and precision of a Goldman Sachs morning research note.

    HEADLINE: {title}
    DETAILS: {summary}
    {watchlist_note}

    Provide a DEEP, institutional-grade breakdown. Think like a hedge fund PM reading this headline
    at 6 AM — what trades do you make and WHY? Follow real market conventions.

    Return ONLY this JSON (no other text):
    {{
      "verdict": "BULLISH" or "BEARISH" or "NEUTRAL",
      "conviction": 1-10,
      "verdict_emoji": "🟢" or "🔴" or "🟡",
      "summary": "2-sentence plain English what happened and why it matters to markets",
      "deep_analysis": "4-5 sentences of institutional-grade analysis. Cover: 1) the immediate market mechanics (supply/demand/flow impact), 2) second-order effects most people miss, 3) historical parallels if any (e.g. 'last time X happened, Y stocks moved Z%'), 4) the smart money positioning implication. Be specific with numbers and comparisons.",
      "affected_stocks": [
        {{
          "ticker": "AAPL",
          "impact": "positive" or "negative" or "neutral",
          "magnitude": "HIGH" or "MEDIUM" or "LOW",
          "reason": "2 sentences: WHY this stock is affected and HOW MUCH. Include estimated % impact if possible."
        }}
      ],
      "market_impact": "2 sentences on broader market direction and sector rotation implications",
      "urgency": "breaking" or "important" or "informational",
      "action_signals": [
        {{
          "ticker": "AAPL",
          "signal": "STRONG BUY" or "BUY" or "HOLD" or "SELL" or "STRONG SELL",
          "reason": "1-2 sentences: specific rationale tied to this news",
          "entry_zone": "$170-175 range" or "At market" or "Wait for pullback to $X",
          "timeframe": "Immediate" or "This week" or "Next 1-3 months",
          "risk_reward": "Risk $5 downside for $15 upside (3:1)" or similar
        }}
      ],
      "risk_assessment": "1-2 sentences on what could go WRONG with this trade thesis. What invalidates it?",
      "bottom_line": "One bold sentence: the single most important takeaway for a trader reading this right now. Start with BUY, SELL, or WATCH.",
      "medium_term_buys": [
        {{
          "ticker": "NVDA",
          "reason": "3-4 sentences: detailed explanation of WHY this stock is a medium-term BUY based on this news. Reference the specific catalyst from the headline, how it creates an opportunity over 1-3 months, what institutional positioning looks like, and the upside potential. Be concrete with numbers.",
          "entry_zone": "$850-870 range",
          "target_price": "$1,000 (18% upside)",
          "timeframe": "1-3 months",
          "conviction": 8
        }}
      ]
    }}

    Rules:
    - Be SPECIFIC with tickers. Never say "tech stocks" — say NVDA, MSFT, AAPL.
    - For geopolitical/macro news: include ETFs (GLD, TLT, XLE, SPY, QQQ, VIX).
    - For earnings/company news: include the company + competitors + suppliers.
    - Always include 2-5 affected stocks and 1-4 action signals.
    - conviction 1-3 = low (informational), 4-6 = moderate, 7-10 = high conviction trade.
    - If conviction >= 7, the bottom_line MUST start with "BUY" or "SELL".
    - If conviction <= 3, signal should be "HOLD" or "WATCH" — do NOT recommend trades on weak signal.
    - medium_term_buys: 1-3 stocks that are compelling BUYS for the next 1-3 months based on this specific news. Focus on stocks where this news creates a medium-term opportunity (not just a day trade). Each must have a detailed reason explaining why to buy NOW for medium-term gains. If the news is purely negative/risk-off, include defensive plays or hedges as the medium-term picks.
    - All text must be in English.
    '''

    ck = 'news_ai_v4:' + hashlib.md5((title + '|' + (summary or '')).encode()).hexdigest()[:16]
    return ask_gemini_json(
        prompt,
        system='You are an elite institutional trading analyst at a top macro hedge fund. '
               'Analyze news like a professional. Be specific, data-driven, and actionable. '
               'Return ONLY valid JSON.',
        max_tokens=1800,
        cache_key=ck,
        cache_ttl=600
    )


# ─────────────────────────────────────────────────────────────────────────────
# BREAKING NEWS → MARKET SIGNAL ENGINE
# ─────────────────────────────────────────────────────────────────────────────

SIGNAL_SYSTEM = '''You are an elite institutional trading analyst at a top macro hedge fund.
Your job is to instantly parse breaking news and translate it into actionable market signals.
You think like Paul Tudor Jones: protect capital first, then identify asymmetric opportunity.
Be specific with tickers. Never be vague. Back every call with a reason.'''

def analyze_breaking_news_signal(headline, context=''):
    """
    Takes a breaking news headline and returns structured trading signals.
    Used by: /api/analyze-news endpoint and the Bloomberg audio pipeline.

    Returns a list of signal objects:
    [
      {
        "signal_type": "RISK OFF",        # RISK OFF | RISK ON | NEUTRAL | DEFENSIVE
        "analysis": "...",                # 2-3 sentence institutional-grade explanation
        "timeframe": "IMMEDIATE",         # IMMEDIATE | SHORT-TERM (1-5 days) | MEDIUM-TERM (weeks)
        "confidence": 85,                 # 0-100
        "stay_on_sideline": false,        # true if event is too uncertain to trade
        "sideline_reason": "",            # only if stay_on_sideline is true
        "tickers": [
          {"ticker": "GLD", "action": "BUY",  "reason": "Safe haven demand spike"},
          {"ticker": "SPY", "action": "SELL", "reason": "Broad equity panic expected"}
        ]
      }
    ]
    """
    extra = f'\nAdditional context: {context}' if context else ''

    prompt = f'''
    BREAKING NEWS: {headline}{extra}

    Translate this into institutional trading signals. Return a JSON array of signal objects.
    Each object must have:
    - signal_type: "RISK OFF" | "RISK ON" | "NEUTRAL" | "DEFENSIVE"
    - analysis: 2-3 sentence explanation of WHY this matters for markets (institutional-grade, specific)
    - timeframe: "IMMEDIATE" | "SHORT-TERM (1-5 days)" | "MEDIUM-TERM (weeks)"
    - confidence: integer 0-100
    - stay_on_sideline: boolean (true only if event is genuinely too uncertain to trade)
    - sideline_reason: string (empty string if stay_on_sideline is false)
    - tickers: array of 3-6 objects with ticker, action (BUY|SELL|WATCH), reason (max 6 words)

    Use specific tickers:
    - Geopolitical war/conflict → GLD, GDX, LMT, RTX, NOC, XOM, USO, VXX, TLT
    - Fed/rates → TLT, SHY, XLF, KRE, USDU, GLD
    - Energy shock → XLE, USO, XOM, CVX, airlines (AAL, DAL) to SELL
    - Tech/AI news → QQQ, NVDA, MSFT, PLTR, sector ETFs
    - China/Taiwan risk → FXI to SELL, defense to BUY, TSM impact
    - Recession signals → XLU, XLP, GLD, TLT to BUY; XLY, XLK to SELL

    Return ONLY the raw JSON array. No markdown, no explanation, no preamble.
    '''

    ck = 'signal:' + hashlib.md5(headline.encode()).hexdigest()[:16]
    result = ask_gemini_json(
        prompt,
        system=SIGNAL_SYSTEM,
        max_tokens=1200,
        cache_key=ck,
        cache_ttl=300  # 5 min cache — breaking news moves fast
    )

    # ask_gemini_json returns a dict on error, we need a list
    if isinstance(result, dict) and 'error' in result:
        return []
    if isinstance(result, list):
        return result
    return []
