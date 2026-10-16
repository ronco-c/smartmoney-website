"""
Live News Scanner — Background thread that polls RSS feeds for breaking
financial news, detects high-impact headlines, and auto-generates
institutional trading signals via the Claude signal pipeline.

Usage:
    from news_scanner import start_scanner, stop_scanner, get_live_signals

    start_scanner()          # starts daemon thread
    signals = get_live_signals()  # returns list of recent signal dicts
    stop_scanner()           # stops polling
"""

import time
import logging
import threading
import hashlib
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
SCAN_INTERVAL_SECONDS = 120     # Poll RSS every 2 minutes
MIN_IMPACT_SCORE = 4            # Only process headlines scoring ≥ 4
MAX_STORED_SIGNALS = 50         # Keep last 50 signal results in memory
MAX_HEADLINES_PER_CYCLE = 1     # Limit Claude calls per cycle to control costs

# ── State ─────────────────────────────────────────────────────────────────────
_scanner_thread = None
_stop_event = threading.Event()
_lock = threading.Lock()

_seen_ids = set()               # MD5 hashes of headlines already processed
_live_signals = deque(maxlen=MAX_STORED_SIGNALS)


def get_live_signals(limit=50):
    """Return the most recent auto-scanned signals, newest first."""
    with _lock:
        return list(_live_signals)[:limit]


def is_scanner_running():
    return _scanner_thread is not None and _scanner_thread.is_alive()


def start_scanner():
    """Start the background news scanner thread."""
    global _scanner_thread
    if is_scanner_running():
        logger.info("[NewsScanner] Already running.")
        return

    _stop_event.clear()
    _scanner_thread = threading.Thread(
        target=_scanner_loop,
        daemon=True,
        name="news-scanner"
    )
    _scanner_thread.start()
    logger.info("[NewsScanner] Started (interval: %ds, min_impact: %d)",
                SCAN_INTERVAL_SECONDS, MIN_IMPACT_SCORE)


def stop_scanner():
    """Stop the background news scanner."""
    global _scanner_thread
    _stop_event.set()
    logger.info("[NewsScanner] Stop requested.")
    _scanner_thread = None


# ── Internal ──────────────────────────────────────────────────────────────────

def _headline_id(title):
    """Create a stable dedup key from a headline."""
    clean = (title or "").strip().lower()
    return hashlib.md5(clean.encode()).hexdigest()[:16]


def _scanner_loop():
    """Main loop: poll → score → analyze → store."""
    # Small initial delay so the app finishes starting up
    time.sleep(5)
    logger.info("[NewsScanner] First scan starting...")

    while not _stop_event.is_set():
        try:
            _run_scan_cycle()
        except Exception as e:
            logger.error("[NewsScanner] Cycle error: %s", e, exc_info=True)

        # Wait for next cycle, but check stop_event every second for fast shutdown
        for _ in range(SCAN_INTERVAL_SECONDS):
            if _stop_event.is_set():
                break
            time.sleep(1)

    logger.info("[NewsScanner] Stopped.")


def _run_scan_cycle():
    """Single scan cycle: fetch RSS → filter → analyze → store."""
    from news_service import fetch_all_rss, _score_impact

    # 1. Fetch latest RSS headlines
    articles = fetch_all_rss(limit=60)
    if not articles:
        logger.debug("[NewsScanner] No articles fetched.")
        return

    # 2. Find new, high-impact headlines
    new_high_impact = []
    for art in articles:
        hid = _headline_id(art.get('title', ''))
        if hid in _seen_ids:
            continue

        # Score impact
        score = _score_impact({
            'title': art.get('title', ''),
            'summary': art.get('summary', ''),
        })

        if score >= MIN_IMPACT_SCORE:
            new_high_impact.append({
                'title': art['title'],
                'source': art.get('source', 'RSS'),
                'url': art.get('url', ''),
                'published': art.get('published'),
                'impact_score': score,
                'hid': hid,
            })

        # Mark as seen regardless of score (so we don't rescore next cycle)
        _seen_ids.add(hid)

    if not new_high_impact:
        logger.debug("[NewsScanner] No new high-impact headlines this cycle (%d articles scanned).", len(articles))
        return

    # Sort by impact score descending, take top N
    new_high_impact.sort(key=lambda x: -x['impact_score'])
    to_analyze = new_high_impact[:MAX_HEADLINES_PER_CYCLE]

    logger.info("[NewsScanner] Found %d new high-impact headline(s), analyzing top %d.",
                len(new_high_impact), len(to_analyze))

    # 3. Run each through the signal engine
    from ai_service import analyze_breaking_news_signal

    for item in to_analyze:
        headline = item['title']
        logger.info("[NewsScanner] Analyzing: %s", headline[:80])

        try:
            signals = analyze_breaking_news_signal(headline)

            if signals:
                entry = {
                    'headline': headline,
                    'source': item['source'],
                    'url': item['url'],
                    'published': item.get('published'),
                    'impact_score': item['impact_score'],
                    'signals': signals,
                    'scanned_at': datetime.now(timezone.utc).isoformat(),
                    'is_live': True,
                }

                with _lock:
                    _live_signals.appendleft(entry)

                logger.info("[NewsScanner] ✓ Generated %d signal(s) for: %s",
                            len(signals), headline[:60])
            else:
                logger.info("[NewsScanner] No signals generated for: %s", headline[:60])

        except Exception as e:
            logger.error("[NewsScanner] Signal generation failed for '%s': %s",
                         headline[:60], e)

        # Small delay between Claude calls
        time.sleep(1)
