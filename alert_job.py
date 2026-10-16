import time
import logging
import threading
from datetime import datetime, timezone
from db import get_all_active_alerts, create_notification, deactivate_alert
from fmp_client import quote as fmp_quote

logger = logging.getLogger(__name__)

ALERT_INTERVAL_MINUTES = 5

def _fetch_price(symbol):
    try:
        q = fmp_quote(symbol)
        if q and "price" in q:
            return float(q["price"])
    except Exception as e:
        logger.warning("FMP quote failed for %s: %s", symbol, e)
    return None

def _run_alert_cycle():
    start = time.time()
    alerts = get_all_active_alerts()
    if not alerts:
        return
        
    logger.info("═══ Alert job started: checking %d active alerts ═══", len(alerts))
    triggered_count = 0
    
    # Group by symbol to minimize API calls
    alerts_by_symbol = {}
    for a in alerts:
        sym = a["symbol"]
        if sym not in alerts_by_symbol:
            alerts_by_symbol[sym] = []
        alerts_by_symbol[sym].append(a)
        
    for sym, sym_alerts in alerts_by_symbol.items():
        price = _fetch_price(sym)
        if price is None:
            continue
            
        for alert in sym_alerts:
            condition = alert["condition_type"]
            threshold = alert["threshold"]
            triggered = False
            
            if condition == "price_above" and price >= threshold:
                triggered = True
            elif condition == "price_below" and price <= threshold:
                triggered = True
                
            if triggered:
                msg = f"{sym} has reached your target of ${threshold:,.2f} (Current: ${price:,.2f})"
                create_notification(alert["user_id"], f"Price Alert: {sym}", msg)
                deactivate_alert(alert["id"])
                triggered_count += 1
                logger.info("Alert triggered for user %s: %s", alert["user_id"], msg)
                
        # rate limit
        time.sleep(0.5)
        
    elapsed = time.time() - start
    if triggered_count > 0:
        logger.info("═══ Alert job complete: %d alerts triggered, %.1fs ═══", triggered_count, elapsed)

def _alert_loop():
    # Wait a bit before first run to let app initialize
    time.sleep(10)
    while True:
        try:
            _run_alert_cycle()
        except Exception as e:
            logger.error("Alert loop error: %s", e)
        time.sleep(ALERT_INTERVAL_MINUTES * 60)

def start_background_alerts():
    t = threading.Thread(target=_alert_loop, daemon=True, name="alert-job")
    t.start()
    logger.info("Background alert thread started (interval: %dm)", ALERT_INTERVAL_MINUTES)
    return t
