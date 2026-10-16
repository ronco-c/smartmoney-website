"""
AI routes — morning brief, stock analysis, why-moving, chat, news analysis,
signal engine, and market intelligence.
"""
import time
import logging

from flask import Blueprint, jsonify, request, session

from db import get_watchlist, get_big_money_movers
from routes.auth import login_required

logger = logging.getLogger(__name__)

ai_bp = Blueprint("ai", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _app_helpers():
    """Lazy-import helpers from app.py to avoid circular imports."""
    from app import _cache_get, _cache_set, _jsonify_cached, _get_full_stock_data
    return _cache_get, _cache_set, _jsonify_cached, _get_full_stock_data


# ---------------------------------------------------------------------------
# AI Deep Integration
# ---------------------------------------------------------------------------
@ai_bp.route("/api/ai/morning-brief")
def api_ai_morning_brief():
    _cache_get, _, _, _ = _app_helpers()
    from ai_service import generate_morning_brief
    user_id = session.get("user_id")
    watchlist = get_watchlist(user_id) if user_id else []
    market = _cache_get("market_indices:all") or {"indices": []}
    movers = get_big_money_movers(limit=1)
    top_mover = movers.get("movers", [{}])[0] if movers and "movers" in movers else {}
    brief = generate_morning_brief(watchlist, market.get("indices", []), top_mover)
    return jsonify({"brief": brief})


@ai_bp.route("/api/ai/stock/<symbol>/analysis")
def api_ai_stock_analysis(symbol):
    _cache_get, _cache_set, _jsonify_cached, _get_full_stock_data = _app_helpers()
    from ai_service import analyze_stock
    sym = symbol.upper()
    cached = _cache_get(f"stock_analysis:{sym}")
    if cached:
        return _jsonify_cached(cached, cache_seconds=1800)
    stock_data = _get_full_stock_data(sym)
    if not stock_data:
        return jsonify({"error": "Not found"}), 404
    analysis = analyze_stock(sym, stock_data)
    _cache_set(f"stock_analysis:{sym}", analysis)
    return _jsonify_cached(analysis, cache_seconds=1800)


@ai_bp.route("/api/ai/stock/<symbol>/why-moving")
def api_ai_why_moving(symbol):
    _, _, _, _get_full_stock_data = _app_helpers()
    from ai_service import explain_stock_move
    sym = symbol.upper()
    stock_data = _get_full_stock_data(sym)
    if not stock_data:
        return jsonify({"error": "Not found"}), 404
    q = stock_data.get("quote", {})
    change_pct = q.get("change_percent", 0) or 0
    volume = q.get("volume", 0) or 0
    avg_vol = q.get("avg_volume", volume) or volume
    volume_ratio = round(volume / avg_vol, 2) if avg_vol else 1.0
    news = stock_data.get("news", [])
    explanation = explain_stock_move(sym, change_pct, volume_ratio, news)
    return jsonify({"symbol": sym, "explanation": explanation})


@ai_bp.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    _cache_get, _cache_set, _, _ = _app_helpers()
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message required"}), 400

    uid = session.get("user_id", request.remote_addr)
    count_key = f"chat_count:{uid}"
    count = _cache_get(count_key) or 0
    limit = 50 if "user_id" in session else 10
    if count >= limit:
        return jsonify({"error": f"Daily limit of {limit} messages reached"}), 429
    _cache_set(count_key, count + 1)

    user_id = session.get("user_id")
    watchlist = get_watchlist(user_id) if user_id else []
    market = _cache_get("market_indices:all") or {}
    indices_str = ", ".join(
        f"{i['name']} {i.get('change_percent', 0):+.1f}%"
        for i in market.get("indices", [])
    )

    system = f"""You are SmartMoney AI, a helpful, intelligent assistant.
You can answer ANY question the user asks, whether it's about finance, programming, history, or general knowledge. If the user asks about the market, you must use this context:
User watchlist: {', '.join(watchlist) or 'none'}. Market today: {indices_str}.
Always be direct, friendly, and professional. Under 150 words unless asked to expand."""

    from ai_service import ask_gemini
    response = ask_gemini(message, system=system, max_tokens=300)
    return jsonify({"response": response, "usage": count + 1, "limit": limit})


# ---------------------------------------------------------------------------
# News Analysis
# ---------------------------------------------------------------------------
@ai_bp.route("/api/news/analyze", methods=["POST"])
def api_analyze_news():
    data = request.json or {}
    title = data.get("title", "").strip()
    summary = data.get("summary", "").strip()
    if not title:
        return jsonify({"error": "Title required"}), 400
    user_id = session.get("user_id")
    watchlist = get_watchlist(user_id) if user_id else []
    from ai_service import analyze_news_article
    analysis = analyze_news_article(title, summary, watchlist)
    return jsonify({"analysis": analysis})


# ---------------------------------------------------------------------------
# AI Market Intelligence
# ---------------------------------------------------------------------------
@ai_bp.route("/api/ai/market-pulse")
def api_market_pulse():
    """Return the latest AI-generated market intelligence pulse."""
    from ai_market_intel import get_market_pulse, is_pulse_running
    pulse = get_market_pulse()
    if not pulse:
        return jsonify({
            "status": "warming_up",
            "message": "AI Market Intelligence is warming up... First pulse in ~30 seconds.",
            "engine_running": is_pulse_running(),
        })
    pulse["engine_running"] = is_pulse_running()
    return jsonify(pulse)


@ai_bp.route("/api/ai/hot-stocks")
def api_ai_hot_stocks():
    """Return AI-detected hot stocks from headline analysis."""
    from ai_market_intel import get_hot_stocks
    hot = get_hot_stocks()
    return jsonify({"hot_stocks": hot, "count": len(hot)})


# ---------------------------------------------------------------------------
# Signal Engine
# ---------------------------------------------------------------------------
@ai_bp.route("/signal")
def signal_page():
    from flask import render_template
    return render_template("news_signal.html")


@ai_bp.route("/api/analyze-news", methods=["POST"])
def api_analyze_news_signal():
    data = request.json
    headline = data.get("headline", "").strip()
    if not headline:
        return jsonify({"error": "No headline provided"}), 400
    from ai_service import analyze_breaking_news_signal
    signals = analyze_breaking_news_signal(headline)
    return jsonify({"signals": signals, "headline": headline})


@ai_bp.route("/api/analyze-audio", methods=["POST"])
def api_analyze_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400
    audio = request.files["audio"]
    path = f"/tmp/bloomberg_{int(time.time())}.mp3"
    audio.save(path)
    from ai_service import transcribe_and_analyze_bloomberg
    result = transcribe_and_analyze_bloomberg(path)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Live News Scanner
# ---------------------------------------------------------------------------
@ai_bp.route("/api/signal/live")
def api_signal_live():
    """Return the latest auto-scanned live signals."""
    from news_scanner import get_live_signals, is_scanner_running
    limit = request.args.get("limit", 50, type=int)
    signals = get_live_signals(limit=limit)
    return jsonify({
        "signals": signals, "count": len(signals),
        "scanner_running": is_scanner_running(),
    })


@ai_bp.route("/api/signal/live/start", methods=["POST"])
def api_signal_live_start():
    """Start the background news scanner."""
    from news_scanner import start_scanner, is_scanner_running
    start_scanner()
    return jsonify({"status": "started", "running": is_scanner_running()})


@ai_bp.route("/api/signal/live/stop", methods=["POST"])
def api_signal_live_stop():
    """Stop the background news scanner."""
    from news_scanner import stop_scanner, is_scanner_running
    stop_scanner()
    return jsonify({"status": "stopped", "running": is_scanner_running()})
