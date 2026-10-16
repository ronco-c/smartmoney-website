"""
Background cache job — fetches 13F data for all 12 institutions and stores
both current + previous quarter holdings in the SQLite DB.

Runs on app startup, then repeats every CACHE_INTERVAL_HOURS.
The frontend reads ONLY from the DB, so page loads are instant.
"""
import time
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CACHE_INTERVAL_HOURS = 6


def _filing_date_to_quarter(filing_date_str: str) -> str:
    """
    Normalize a filing date (e.g. '2026-02-13') to the quarter it reports on.
    13F filings are due ~45 days after quarter end, so:
      - Filed Jan-Mar  → reports on Q4 of previous year (ending Dec 31)
      - Filed Apr-Jun  → reports on Q1 (ending Mar 31)
      - Filed Jul-Sep  → reports on Q2 (ending Jun 30)
      - Filed Oct-Dec  → reports on Q3 (ending Sep 30)
    """
    try:
        dt = datetime.strptime(filing_date_str[:10], "%Y-%m-%d")
        month = dt.month
        year = dt.year
        if month <= 3:
            return f"{year - 1}-Q4"
        elif month <= 6:
            return f"{year}-Q1"
        elif month <= 9:
            return f"{year}-Q2"
        else:
            return f"{year}-Q3"
    except Exception:
        return filing_date_str


def _run_cache_cycle():
    """Fetch all 13F data and store in DB."""
    from db import init_db, upsert_holdings, set_cache, get_consensus_with_change, get_big_money_movers, get_all_institution_summaries
    from edgar_13f import INSTITUTIONS, get_latest_13f_accessions, fetch_13f_holdings_for_quarter

    init_db()

    start = time.time()
    logger.info("═══ Cache job started at %s ═══", datetime.now(timezone.utc).isoformat())

    success_count = 0
    error_count = 0

    for inst in INSTITUTIONS:
        cik = inst["cik"]
        name = inst["name"]
        short = inst["short"]

        try:
            # Get the 2 most recent 13F filing accessions
            accessions = get_latest_13f_accessions(cik, count=2)
            if not accessions:
                logger.warning("No 13F filings found for %s (%s)", name, cik)
                error_count += 1
                continue

            for idx, acc in enumerate(accessions):
                filing_date = acc.get("filing_date", "unknown")
                quarter_label = _filing_date_to_quarter(filing_date)
                try:
                    holdings_data = fetch_13f_holdings_for_quarter(cik, acc)
                    if holdings_data and holdings_data.get("holdings"):
                        upsert_holdings(
                            cik=cik,
                            institution=name,
                            short_name=short,
                            quarter_date=quarter_label,
                            filing_date=filing_date,
                            holdings=holdings_data["holdings"],
                        )
                        logger.info(
                            "  ✓ %s Q%d (%s → %s): %d holdings stored",
                            short, idx, filing_date, quarter_label,
                            len(holdings_data["holdings"]),
                        )
                    else:
                        logger.warning("  ✗ %s Q%d: no holdings data", short, idx)
                except Exception as e:
                    logger.error("  ✗ %s Q%d error: %s", short, idx, e)

                # Rate limit: SEC EDGAR requests 10 req/s max
                time.sleep(0.5)

            success_count += 1

        except Exception as e:
            logger.error("Cache job error for %s: %s", name, e)
            error_count += 1

        # Throttle between institutions
        time.sleep(0.3)

    # Pre-compute institution summaries, consensus picks, and big money movers
    try:
        summaries = get_all_institution_summaries()
        set_cache("institution_summaries", {"institutions": summaries, "count": len(summaries)})
        logger.info("Pre-computed institution summaries: %d firms", len(summaries))
    except Exception as e:
        logger.error("Institution summaries pre-compute failed: %s", e)

    try:
        consensus = get_consensus_with_change(n=30)
        set_cache("consensus_picks", consensus)
        logger.info("Pre-computed consensus picks: %d stocks", len(consensus.get("picks", [])))
    except Exception as e:
        logger.error("Consensus pre-compute failed: %s", e)

    try:
        movers = get_big_money_movers(min_change_pct=30.0, min_value=10_000_000)
        set_cache("big_money_movers", movers)
        logger.info("Pre-computed big money movers: %d stocks", len(movers.get("movers", [])))
    except Exception as e:
        logger.error("Big money movers pre-compute failed: %s", e)

    elapsed = time.time() - start
    logger.info(
        "═══ Cache job complete: %d success, %d errors, %.1fs ═══",
        success_count, error_count, elapsed,
    )


def _cache_loop():
    """Run the cache cycle, then schedule next run."""
    while True:
        try:
            _run_cache_cycle()
        except Exception as e:
            logger.error("Cache loop error: %s", e)
        # Sleep until next cycle
        time.sleep(CACHE_INTERVAL_HOURS * 3600)


def start_background_cache():
    """Start the background cache thread (daemon, non-blocking)."""
    t = threading.Thread(target=_cache_loop, daemon=True, name="cache-job")
    t.start()
    logger.info("Background cache thread started (interval: %dh)", CACHE_INTERVAL_HOURS)
    return t
