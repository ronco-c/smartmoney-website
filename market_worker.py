import os
import time
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_worker")

# Import local modules
from db import init_db, upsert_stock_prices, upsert_sector_holdings
from fmp_client import _get, batch_quote

SECTOR_ETF_MAP = {
    "Artificial Intelligence (AI)": ["BOTZ", "AIQ"],
    "Cybersecurity": ["BUG", "CIBR"],
    "Databases & Cloud": ["IGV", "SKYY"],
    "Retail": ["XRT", "RTH"],
    "Healthcare": ["XLV", "IHI"],
    "Energy": ["XLE", "VDE"],
    "Financial Services": ["XLF", "KRE"],
    "Real Estate": ["VNQ", "SCHH"],
    "Technology": ["XLK", "QQQ"],
    "Automotive": ["CARZ", "DRIV"]
}

# Fallback dict if FMP rate limit gets hit
FALLBACK_SECTORS = {
    "Artificial Intelligence (AI)": ["NVDA", "MSFT", "AMD", "GOOGL", "META", "AMZN", "TSM", "AVGO", "PLTR", "CRWD"],
    "Databases & Cloud": ["AMZN", "MSFT", "GOOGL", "ORCL", "SNOW", "CRM", "SAP", "MDB", "NOW", "DDOG"],
    "Retail": ["WMT", "AMZN", "COST", "HD", "LOW", "TGT", "MCD", "SBUX", "NKE", "TJX"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "DHR", "ABT", "PFE", "AMGN"],
    "Energy": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "HES"],
    "Financial Services": ["JPM", "V", "MA", "BAC", "WFC", "MS", "GS", "BX", "BLK", "C"],
    "Real Estate": ["PLD", "AMT", "EQIX", "SPG", "PSA", "WELL", "O", "DLR", "CSGP", "CCI"],
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ACN", "CSCO", "INTC", "IBM"],
    "Cybersecurity": ["CRWD", "PANW", "FTNT", "ZS", "NET", "CHKP", "OKTA", "CYBR", "CIBR", "HACK"],
    "Automotive": ["TSLA", "TM", "GM", "F", "STLA", "RIVN", "LCID", "HMC", "RACE", "ON"]
}

def sync_etf_holdings():
    """Fetch ETF holdings from FMP and update sector_holdings table."""
    logger.info("Starting ETF holdings sync...")
    for sector, etfs in SECTOR_ETF_MAP.items():
        sector_holdings = {} # ticker -> max_weight
        
        for etf in etfs:
            logger.info("Fetching FMP etf-holder for %s (%s)", etf, sector)
            try:
                data = _get("etf-holder/" + etf)
                if data and isinstance(data, list):
                    for item in data:
                        ticker = item.get("asset")
                        weight = item.get("weightPercentage", 0.0)
                        if ticker and weight > 0:
                            # Keep the highest weight if found in multiple ETFs
                            if ticker not in sector_holdings or weight > sector_holdings[ticker]:
                                sector_holdings[ticker] = weight
            except Exception as e:
                logger.error("Error fetching ETF %s: %s", etf, e)
            
            time.sleep(0.5) # rate limit
            
        if sector_holdings:
            # Keep top 30 by weight
            sorted_holdings = sorted(
                [{"ticker": k, "weight": v} for k, v in sector_holdings.items()],
                key=lambda x: x["weight"], 
                reverse=True
            )[:30]
        else:
            logger.warning("FMP empty for %s. Falling back to static list...", sector)
            # FMP limit reached! Give 30 weights counting down just to pad it.
            fallback_list = FALLBACK_SECTORS.get(sector, [])
            sorted_holdings = [{"ticker": t, "weight": 30.0 - i} for i, t in enumerate(fallback_list)]
        
        if sorted_holdings:
            upsert_sector_holdings(sector, sorted_holdings)
            logger.info("Upserted %d holdings for %s", len(sorted_holdings), sector)

def sync_live_quotes():
    """Fetch live quotes for all active tickers and update stock_prices table."""
    logger.info("Starting live quotes sync...")
    
    # 1. Gather all tickers we care about
    # For now, let's sync all ETF holdings
    from db import _conn
    conn = _conn()
    rows = conn.execute("SELECT DISTINCT ticker FROM sector_holdings").fetchall()
    tickers = {r["ticker"] for r in rows}
    
    # Add top 13F tickers
    comp_rows = conn.execute("SELECT ticker FROM institutional_holdings WHERE ticker != '' ORDER BY value DESC LIMIT 200").fetchall()
    tickers.update({r["ticker"] for r in comp_rows})
    
    # Add watchlists and alerts
    watch_rows = conn.execute("SELECT DISTINCT ticker FROM watchlists").fetchall()
    tickers.update({r["ticker"] for r in watch_rows})
    alert_rows = conn.execute("SELECT DISTINCT symbol as ticker FROM alerts WHERE is_active = 1").fetchall()
    tickers.update({r["ticker"] for r in alert_rows})
    
    # Add major indices
    tickers.update({"SPY", "QQQ", "DIA", "IWM"})
    
    ticker_list = list(tickers)
    logger.info("Syncing quotes for %d unique active UI tickers", len(ticker_list))
    
    # Batch them in small chunks to avoid FMP rate limits
    chunk_size = 10
    total_upserted = 0
    
    for i in range(0, len(ticker_list), chunk_size):
        chunk = ticker_list[i:i + chunk_size]
        try:
            quotes = batch_quote(chunk)
            if quotes:
                upsert_stock_prices(quotes)
                total_upserted += len(quotes)
                logger.info("Upserted batch of %d quotes (FMP) (%d/%d)", len(quotes), i + len(chunk), len(ticker_list))
            else:
                raise Exception("FMP returned empty (likely rate limit 429)")
        except Exception as e:
            logger.warning("FMP batch quotes failed: %s. Falling back to yfinance...", e)
            try:
                import yfinance as yf
                yf_quotes = []
                tickers = yf.Tickers(" ".join(chunk))
                for sym in chunk:
                    try:
                        t = tickers.tickers.get(sym)
                        if not t: continue
                        info = t.fast_info
                        price = float(info.last_price) if hasattr(info, "last_price") else None
                        prev = float(info.previous_close) if hasattr(info, "previous_close") else None
                        if price and prev:
                            change = round(price - prev, 2)
                            change_pct = round((change / prev) * 100, 2)
                            yf_quotes.append({
                                "ticker": sym,
                                "price": round(price, 2),
                                "change": change,
                                "change_percent": change_pct,
                                "market_cap": getattr(info, "market_cap", None)
                            })
                    except Exception:
                        pass
                if yf_quotes:
                    upsert_stock_prices(yf_quotes)
                    total_upserted += len(yf_quotes)
                    logger.info("Upserted batch of %d quotes (yfinance) (%d/%d)", len(yf_quotes), i + len(chunk), len(ticker_list))
            except Exception as yf_e:
                logger.error("yfinance fallback also failed: %s", yf_e)
                
        time.sleep(1) # rate limit between batches

    logger.info("Completed live quotes sync. Total quotes updated: %d", total_upserted)

def sync_analyst_targets():
    """Fetch analyst targets for top tickers and store upside_pct in stock_prices."""
    logger.info("Starting analyst targets sync...")
    from db import _conn
    conn = _conn()
    
    # Get tickers that have prices but no analyst_target
    rows = conn.execute("""
        SELECT ticker FROM stock_prices
        WHERE price IS NOT NULL AND price > 0
        AND (analyst_target IS NULL OR analyst_target = 0)
        ORDER BY RANDOM()
        LIMIT 30
    """).fetchall()
    tickers = [r["ticker"] for r in rows]
    
    if not tickers:
        # Also refresh some existing ones
        rows = conn.execute("""
            SELECT ticker FROM stock_prices
            WHERE price IS NOT NULL AND price > 0
            ORDER BY updated_at ASC
            LIMIT 20
        """).fetchall()
        tickers = [r["ticker"] for r in rows]
    
    from fmp_client import analyst_price_target
    updated = 0
    for sym in tickers:
        try:
            target = analyst_price_target(sym)
            if target and target.get("avg_price_target"):
                avg_target = target["avg_price_target"]
                # Get current price
                price_row = conn.execute("SELECT price FROM stock_prices WHERE ticker = ?", (sym,)).fetchone()
                if price_row and price_row["price"] and price_row["price"] > 0:
                    upside = round(((avg_target - price_row["price"]) / price_row["price"]) * 100, 2)
                    conn.execute("""
                        UPDATE stock_prices SET analyst_target = ?, upside_pct = ? WHERE ticker = ?
                    """, (round(avg_target, 2), upside, sym))
                    updated += 1
        except Exception as e:
            logger.warning("Analyst target failed for %s: %s", sym, e)
        time.sleep(0.3)  # Rate limit
    
    conn.commit()
    logger.info("Analyst targets sync complete: %d updated", updated)


def is_market_hours():
    """Returns True if it is Mon-Fri 14:00-21:30 UTC (US market hours)."""
    now = datetime.now(timezone.utc)
    if now.weekday() > 4:
        return False
    hour = now.hour
    minute = now.minute
    if hour < 14 or (hour == 21 and minute > 30) or hour > 21:
        return False
    return True

def _worker_loop():
    """Background loop: sync quotes every 15s, analyst targets every 5 min, ETF holdings every 6h."""
    analyst_interval = 300  # 5 minutes
    etf_interval = 21600  # 6 hours
    
    last_analyst = 0
    last_etf = 0
    
    while True:
        try:
            now = time.time()
            
            # Always sync live quotes
            sync_live_quotes()
            
            # Analyst targets every 5 min
            if now - last_analyst > analyst_interval:
                try:
                    sync_analyst_targets()
                    last_analyst = now
                except Exception as e:
                    logger.error("Analyst targets sync error: %s", e)
            
            # ETF holdings every 6h
            if now - last_etf > etf_interval:
                try:
                    sync_etf_holdings()
                    last_etf = now
                except Exception as e:
                    logger.error("ETF holdings sync error: %s", e)
                    
        except Exception as e:
            logger.error("Worker loop error: %s", e)
        
        quote_interval = 15 if is_market_hours() else 300
        time.sleep(quote_interval)


def start_background_worker():
    """Start the market data worker as a daemon thread (non-blocking)."""
    init_db()
    t = threading.Thread(target=_worker_loop, daemon=True, name="market-worker")
    t.start()
    logger.info("Market worker background thread started (quotes every 15s)")
    return t


def main():
    logger.info("Initializing database...")
    init_db()
    
    # One-time sync
    sync_etf_holdings()
    sync_live_quotes()
    sync_analyst_targets()
    
    logger.info("Market worker cycle complete.")

if __name__ == "__main__":
    main()
