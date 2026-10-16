"""
SQLite database for caching institutional holdings (13F data).
Stores current + previous quarter holdings so we can compute QoQ change.
Frontend reads ONLY from this DB — never calls external APIs on page load.
"""
import os
import json
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).resolve().parent
DB_PATH = DB_DIR / "smart_money.db"

_local = threading.local()


def _conn() -> sqlite3.Connection:
    """Thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=30)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = _conn()

    # Check if we need to migrate from old schema (PRIMARY KEY on ticker)
    # to new schema (PRIMARY KEY on cusip) to store ALL holdings
    needs_rebuild = False
    try:
        info = conn.execute("PRAGMA table_info(institutional_holdings)").fetchall()
        if info:
            # Check if cusip column has NOT NULL + PK (old schema has ticker as PK)
            col_names = [row["name"] for row in info]
            pk_cols = [row["name"] for row in info if row["pk"] > 0]
            if "ticker" in pk_cols and "cusip" not in pk_cols:
                needs_rebuild = True
    except Exception:
        pass

    if needs_rebuild:
        logger.info("Migrating DB schema: PRIMARY KEY (cik,ticker,quarter_date) -> (cik,cusip,quarter_date)")
        conn.executescript("""
            DROP TABLE IF EXISTS institutional_holdings;
        """)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS institutional_holdings (
            cik           TEXT NOT NULL,
            institution   TEXT NOT NULL,
            short_name    TEXT,
            ticker        TEXT DEFAULT '',
            issuer        TEXT,
            cusip         TEXT NOT NULL DEFAULT '',
            quarter_date  TEXT NOT NULL,
            filing_date   TEXT,
            shares        INTEGER DEFAULT 0,
            value         INTEGER DEFAULT 0,
            PRIMARY KEY (cik, cusip, quarter_date)
        );

        CREATE INDEX IF NOT EXISTS idx_holdings_ticker
            ON institutional_holdings(ticker);
        CREATE INDEX IF NOT EXISTS idx_holdings_quarter
            ON institutional_holdings(quarter_date);
        CREATE INDEX IF NOT EXISTS idx_holdings_cik
            ON institutional_holdings(cik);
        CREATE INDEX IF NOT EXISTS idx_holdings_cusip
            ON institutional_holdings(cusip);
        CREATE INDEX IF NOT EXISTS idx_holdings_lookup
            ON institutional_holdings(cik, ticker, quarter_date);

        CREATE TABLE IF NOT EXISTS cache_results (
            cache_key   TEXT PRIMARY KEY,
            data        TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT UNIQUE NOT NULL,
            password_hash   TEXT NOT NULL,
            first_name      TEXT,
            created_at      TEXT NOT NULL,
            reset_token     TEXT,
            reset_token_expiry TEXT
        );

        CREATE TABLE IF NOT EXISTS watchlists (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            ticker          TEXT NOT NULL,
            added_at        TEXT NOT NULL,
            UNIQUE(user_id, ticker),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id         INTEGER PRIMARY KEY,
            experience      TEXT,
            goals           TEXT,
            sectors         TEXT,
            updated_at      TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            symbol          TEXT NOT NULL,
            condition_type  TEXT NOT NULL, -- 'price_below', 'price_above', 'move_up', 'move_down'
            threshold       REAL NOT NULL,
            is_active       INTEGER DEFAULT 1,
            created_at      TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            title           TEXT NOT NULL,
            message         TEXT NOT NULL,
            is_read         INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS stock_prices (
            ticker          TEXT PRIMARY KEY,
            price           REAL,
            change          REAL,
            change_percent  REAL,
            market_cap      REAL,
            analyst_target  REAL,
            upside_pct      REAL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sector_holdings (
            sector          TEXT,
            ticker          TEXT,
            weight          REAL,
            updated_at      TEXT NOT NULL,
            PRIMARY KEY (sector, ticker)
        );
    """)
    conn.commit()
    logger.info("Database initialized at %s", DB_PATH)


def upsert_holdings(cik: str, institution: str, short_name: str,
                    quarter_date: str, filing_date: str,
                    holdings: List[Dict]):
    """Insert or update holdings for one institution + one quarter."""
    conn = _conn()
    for h in holdings:
        cusip = h.get("cusip", "") or h.get("issuer", "")
        if not cusip:
            continue  # need some identifier
        conn.execute("""
            INSERT INTO institutional_holdings
                (cik, institution, short_name, ticker, issuer, cusip,
                 quarter_date, filing_date, shares, value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cik, cusip, quarter_date) DO UPDATE SET
                institution = excluded.institution,
                short_name = excluded.short_name,
                ticker = excluded.ticker,
                issuer = excluded.issuer,
                filing_date = excluded.filing_date,
                shares = excluded.shares,
                value = excluded.value
        """, (
            cik, institution, short_name, h.get("ticker", ""),
            h.get("issuer", ""), cusip,
            quarter_date, filing_date,
            h.get("shares", 0), h.get("value", 0),
        ))
    conn.commit()


def get_two_latest_quarters() -> List[str]:
    """Return the 2 most recent quarter_date values in the DB."""
    conn = _conn()
    rows = conn.execute("""
        SELECT DISTINCT quarter_date FROM institutional_holdings
        ORDER BY quarter_date DESC LIMIT 2
    """).fetchall()
    return [r["quarter_date"] for r in rows]


def _detect_split_ratio(cur_shares: int, prev_shares: int,
                        cur_value: int, prev_value: int) -> int:
    """
    Detect stock splits by comparing share counts and value-per-share between quarters.
    Returns the split ratio (e.g. 10 for a 10:1 split), or 1 if no split.

    Uses TWO signals:
    1) Share ratio (cur/prev) — should be close to the split factor
    2) Value-per-share ratio (prev/cur) — should also be close to the split factor
    Both must agree for a split to be detected.
    """
    if not (cur_shares > 0 and prev_shares > 0 and cur_value > 0 and prev_value > 0):
        return 1

    shares_ratio = cur_shares / prev_shares  # e.g. ~10 for 10:1 split
    cur_vps = cur_value / cur_shares
    prev_vps = prev_value / prev_shares
    vps_ratio = prev_vps / cur_vps  # e.g. ~10 for 10:1 split (price drops)

    # If shares didn't change much (within 50%), no split
    if shares_ratio < 1.5:
        return 1

    # Find the common split factor that best matches the shares ratio
    common_splits = [2, 3, 4, 5, 7, 10, 15, 20, 25, 50]
    best_split = 1
    best_error = float('inf')
    for s in common_splits:
        error = abs(shares_ratio - s) / s  # relative error from shares ratio
        if error < best_error and error < 0.15:  # shares must be within 15% of split
            best_error = error
            best_split = s

    # Cross-validate: vps_ratio should also be roughly consistent (within 50%)
    # (price can move ±30-40% between quarters, so vps_ratio won't be exact)
    if best_split > 1:
        vps_error = abs(vps_ratio - best_split) / best_split
        if vps_error > 0.50:  # value-per-share doesn't confirm the split
            return 1

    return best_split


def get_consensus_with_change(n: int = 25) -> Dict:
    """
    Cross-reference holdings across institutions for the latest quarter.
    Compute QoQ change using previous quarter data from the DB.
    """
    quarters = get_two_latest_quarters()
    if not quarters:
        return {"picks": [], "institutions_analyzed": 0, "total_stocks_found": 0}

    current_q = quarters[0]
    prev_q = quarters[1] if len(quarters) > 1 else None
    conn = _conn()

    # Find CIKs that have data in BOTH quarters (for fair QoQ comparison)
    comparable_ciks = set()
    if prev_q:
        cik_rows = conn.execute("""
            SELECT cik FROM institutional_holdings
            WHERE quarter_date = ?
            INTERSECT
            SELECT cik FROM institutional_holdings
            WHERE quarter_date = ?
        """, (current_q, prev_q)).fetchall()
        comparable_ciks = {r["cik"] for r in cik_rows}
        logger.info("Consensus QoQ: %d CIKs have data in both %s and %s",
                     len(comparable_ciks), current_q, prev_q)

    # Current quarter: aggregate by ticker
    cur_rows = conn.execute("""
        SELECT ticker, issuer,
               COUNT(DISTINCT cik) as num_holders,
               SUM(shares) as total_shares,
               SUM(value) as total_value,
               GROUP_CONCAT(DISTINCT short_name) as holder_names
        FROM institutional_holdings
        WHERE quarter_date = ? AND ticker != '' AND LENGTH(ticker) <= 6
        GROUP BY ticker
        ORDER BY num_holders DESC, total_value DESC
    """, (current_q,)).fetchall()

    # Previous quarter: aggregate by ticker for change calc
    # ONLY from institutions that also have current quarter data
    prev_data = {}
    if prev_q and comparable_ciks:
        placeholders = ",".join("?" for _ in comparable_ciks)
        prev_rows = conn.execute(f"""
            SELECT ticker, SUM(shares) as total_shares, SUM(value) as total_value
            FROM institutional_holdings
            WHERE quarter_date = ? AND cik IN ({placeholders})
            GROUP BY ticker
        """, (prev_q, *comparable_ciks)).fetchall()
        prev_data = {r["ticker"]: dict(r) for r in prev_rows}

    # Current quarter aggregate from comparable CIKs only (for fair change calc)
    cur_comparable = {}
    if prev_q and comparable_ciks:
        placeholders = ",".join("?" for _ in comparable_ciks)
        comp_rows = conn.execute(f"""
            SELECT ticker, SUM(shares) as total_shares, SUM(value) as total_value
            FROM institutional_holdings
            WHERE quarter_date = ? AND cik IN ({placeholders}) AND ticker != ''
            GROUP BY ticker
        """, (current_q, *comparable_ciks)).fetchall()
        cur_comparable = {r["ticker"]: dict(r) for r in comp_rows}

    # Per-institution change for each ticker (for top holders detail)
    inst_changes = {}
    if prev_q:
        inst_detail = conn.execute("""
            SELECT c.ticker, c.cik, c.short_name, c.shares as cur_shares,
                   c.value as cur_value,
                   COALESCE(p.shares, 0) as prev_shares
            FROM institutional_holdings c
            LEFT JOIN institutional_holdings p
                ON c.cik = p.cik AND c.ticker = p.ticker AND p.quarter_date = ?
            WHERE c.quarter_date = ? AND c.ticker != ''
        """, (prev_q, current_q)).fetchall()
        for row in inst_detail:
            t = row["ticker"]
            if t not in inst_changes:
                inst_changes[t] = []
            prev_sh = row["prev_shares"]
            cur_sh = row["cur_shares"]
            # Detect stock splits: if value/share changed by a clean factor,
            # adjust prev shares so the change reflects real buying/selling
            prev_val_for_split = prev_data.get(t, {}).get("total_value", 0) if prev_data else 0
            cur_val_for_split = 0
            # We need aggregate cur value for this ticker for split detection
            # Use the per-institution values as a proxy
            if prev_sh > 0 and cur_sh > 0 and row["cur_value"] > 0:
                cur_vps = row["cur_value"] / cur_sh
                prev_vps = (prev_val_for_split / prev_data.get(t, {}).get("total_shares", 1)) if prev_data and prev_data.get(t, {}).get("total_shares", 0) > 0 else 0
                if prev_vps > 0 and cur_vps > 0:
                    split_r = _detect_split_ratio(cur_sh, prev_sh, row["cur_value"], int(prev_vps * prev_sh) if prev_sh > 0 else 0)
                else:
                    split_r = 1
            else:
                split_r = 1
            adj_prev_sh = prev_sh * split_r
            ch_pct = ((cur_sh - adj_prev_sh) / adj_prev_sh * 100) if adj_prev_sh > 0 else (99999 if cur_sh > 0 else 0)
            inst_changes[t].append({
                "institution": row["short_name"] or "",
                "cik": row["cik"],
                "shares": cur_sh,
                "value": row["cur_value"],
                "prev_shares": prev_sh,
                "change_pct": round(ch_pct, 2),
            })

    # ETFs to skip
    skip = {"SPY", "QQQ", "DIA", "IVV", "VOO", "IWM", "VTI",
            "EFA", "IEMG", "VEA", "VWO", "AGG", "BND", "TLT",
            "GLD", "SLV", "XLK", "XLF", "XLE", "XLV"}

    picks = []
    for row in cur_rows:
        ticker = row["ticker"]
        if ticker in skip:
            continue
        if len(picks) >= n:
            break

        num_holders = row["num_holders"]
        total_shares = row["total_shares"]
        total_value = row["total_value"]

        # QoQ change (split-adjusted) — use only comparable CIKs for fair comparison
        comp = cur_comparable.get(ticker, {})
        comp_shares = comp.get("total_shares", total_shares)
        comp_value = comp.get("total_value", total_value)
        prev = prev_data.get(ticker)
        if prev and prev["total_shares"] > 0:
            split_ratio = _detect_split_ratio(
                comp_shares, prev["total_shares"],
                comp_value, prev["total_value"]
            )
            adj_prev_shares = prev["total_shares"] * split_ratio
            inst_change_pct = round(
                (comp_shares - adj_prev_shares) / adj_prev_shares * 100, 2
            )
        elif prev is None and total_shares > 0:
            inst_change_pct = 99999.0  # New position
        else:
            inst_change_pct = 0.0

        # Conviction level
        if num_holders >= 15:
            conviction = "EXTREME"
        elif num_holders >= 10:
            conviction = "VERY HIGH"
        elif num_holders >= 6:
            conviction = "HIGH"
        elif num_holders >= 3:
            conviction = "MODERATE"
        else:
            conviction = "LOW"

        # Top holders for this ticker
        holders = inst_changes.get(ticker, [])
        holders.sort(key=lambda x: x["value"], reverse=True)

        holder_names = (row["holder_names"] or "").split(",")

        picks.append({
            "rank": len(picks) + 1,
            "ticker": ticker,
            "issuer": row["issuer"] or ticker,
            "num_holders": num_holders,
            "conviction": conviction,
            "total_value": total_value,
            "total_shares": total_shares,
            "inst_change_pct": inst_change_pct,
            "top_holders": holders[:5],
        })

    # Count distinct institutions
    inst_count = conn.execute("""
        SELECT COUNT(DISTINCT cik) FROM institutional_holdings
        WHERE quarter_date = ?
    """, (current_q,)).fetchone()[0]

    return {
        "picks": picks,
        "institutions_analyzed": inst_count,
        "total_stocks_found": len(cur_rows),
        "current_quarter": current_q,
        "previous_quarter": prev_q,
    }


def get_big_money_movers(min_change_pct: float = 30.0,
                         min_value: int = 10_000_000,
                         limit: int = 25) -> Dict:
    """
    Big Money Movers: stocks where any institution increased position
    by more than min_change_pct% AND the position value > min_value.
    """
    quarters = get_two_latest_quarters()
    if len(quarters) < 2:
        return {"movers": [], "count": 0}

    current_q, prev_q = quarters[0], quarters[1]
    conn = _conn()

    rows = conn.execute("""
        SELECT c.ticker, c.issuer, c.cik, c.short_name as institution,
               c.shares as current_shares, c.value as current_value,
               COALESCE(p.shares, 0) as prev_shares,
               COALESCE(p.value, 0) as prev_value
        FROM institutional_holdings c
        LEFT JOIN institutional_holdings p
            ON c.cik = p.cik AND c.ticker = p.ticker AND p.quarter_date = ?
        WHERE c.quarter_date = ?
          AND c.ticker != ''
          AND c.value > ?
        ORDER BY c.value DESC
    """, (prev_q, current_q, min_value)).fetchall()

    movers = []
    seen = set()

    for row in rows:
        cur_sh = row["current_shares"]
        prev_sh = row["prev_shares"]
        cur_val = row["current_value"]
        prev_val = row["prev_value"]
        # Adjust for stock splits
        split_ratio = _detect_split_ratio(cur_sh, prev_sh, cur_val, prev_val) if prev_sh > 0 else 1
        adj_prev_sh = prev_sh * split_ratio
        if adj_prev_sh > 0:
            change_pct = (cur_sh - adj_prev_sh) / adj_prev_sh * 100
        elif cur_sh > 0:
            change_pct = 99999.0  # New position → treat as massive increase
        else:
            continue

        if change_pct < min_change_pct:
            continue

        ticker = row["ticker"]
        inst = row["institution"] or ""
        key = f"{ticker}:{inst}"
        if key in seen:
            continue
        seen.add(key)

        # Signal strength
        if change_pct >= 1000:
            signal = "🚀 MEGA BUY"
        elif change_pct >= 500:
            signal = "🔥 STRONG BUY"
        elif change_pct >= 100:
            signal = "📈 BIG ACCUMULATION"
        else:
            signal = "⬆️ ACCUMULATING"

        movers.append({
            "ticker": ticker,
            "issuer": row["issuer"] or ticker,
            "institution": inst,
            "current_shares": cur_sh,
            "prev_shares": prev_sh,
            "change_pct": round(change_pct, 2),
            "current_value": row["current_value"],
            "signal": signal,
        })

        if len(movers) >= limit:
            break

    # Sort by change_pct descending
    movers.sort(key=lambda x: x["change_pct"], reverse=True)

    return {
        "movers": movers,
        "count": len(movers),
        "current_quarter": current_q,
        "previous_quarter": prev_q,
    }


def set_cache(key: str, data: dict):
    """Store pre-computed results as JSON."""
    conn = _conn()
    from datetime import datetime, timezone
    conn.execute("""
        INSERT INTO cache_results (cache_key, data, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            data = excluded.data,
            updated_at = excluded.updated_at
    """, (key, json.dumps(data), datetime.now(timezone.utc).isoformat()))
    conn.commit()


def get_cache(key: str) -> Optional[Dict]:
    """Retrieve cached results."""
    conn = _conn()
    row = conn.execute(
        "SELECT data FROM cache_results WHERE cache_key = ?", (key,)
    ).fetchone()
    if row:
        return json.loads(row["data"])
    return None


def get_all_institution_summaries() -> List[Dict]:
    """Lightweight institution summaries from the DB for the dashboard grid."""
    conn = _conn()

    # Get each institution's LATEST quarter (not just the global latest)
    # This ensures institutions that filed for different quarters still appear
    rows = conn.execute("""
        SELECT h.cik, h.institution, h.short_name, h.filing_date,
               SUM(h.value) as total_value,
               COUNT(DISTINCT h.ticker) as total_positions,
               h.quarter_date
        FROM institutional_holdings h
        INNER JOIN (
            SELECT cik, MAX(quarter_date) as max_q
            FROM institutional_holdings
            GROUP BY cik
        ) latest ON h.cik = latest.cik AND h.quarter_date = latest.max_q
        GROUP BY h.cik
        ORDER BY total_value DESC
    """).fetchall()

    # Get previous quarter totals for QoQ change
    # Must select ONLY the second-most-recent quarter per institution,
    # not all non-latest quarters summed together.
    prev_totals = {}
    prev_rows = conn.execute("""
        SELECT h.cik, SUM(h.value) as total_value
        FROM institutional_holdings h
        INNER JOIN (
            SELECT h2.cik, MAX(h2.quarter_date) as prev_q
            FROM institutional_holdings h2
            INNER JOIN (
                SELECT cik, MAX(quarter_date) as max_q
                FROM institutional_holdings
                GROUP BY cik
            ) lx ON h2.cik = lx.cik AND h2.quarter_date < lx.max_q
            GROUP BY h2.cik
        ) prev ON h.cik = prev.cik AND h.quarter_date = prev.prev_q
        GROUP BY h.cik
    """).fetchall()
    for pr in prev_rows:
        prev_totals[pr["cik"]] = pr["total_value"]

    summaries = []
    for r in rows:
        # Top 5 holdings for this institution's latest quarter
        top5 = conn.execute("""
            SELECT ticker, value FROM institutional_holdings
            WHERE cik = ? AND quarter_date = ? AND ticker != ''
            ORDER BY value DESC LIMIT 5
        """, (r["cik"], r["quarter_date"])).fetchall()

        # QoQ change
        prev_val = prev_totals.get(r["cik"])
        if prev_val and prev_val > 0:
            change_pct = round((r["total_value"] - prev_val) / prev_val * 100, 2)
        else:
            change_pct = None

        summaries.append({
            "name": r["institution"],
            "short_name": r["short_name"] or "",
            "cik": r["cik"],
            "total_value": r["total_value"],
            "total_positions": r["total_positions"],
            "filing_date": r["filing_date"] or "",
            "change_pct": change_pct,
            "top_holdings": [{"ticker": t["ticker"], "value": t["value"]} for t in top5],
        })
    return summaries


def has_data() -> bool:
    """Check if the DB has any institutional holdings data."""
    try:
        conn = _conn()
        row = conn.execute("SELECT COUNT(*) FROM institutional_holdings").fetchone()
        return row[0] > 0
    except Exception:
        return False


def get_institution_holdings_with_change(cik: str) -> Optional[Dict]:
    """
    Return full holdings for one institution with QoQ % change per holding.
    Compares each stock's value in the latest vs previous quarter.
    """
    conn = _conn()

    # Find this institution's two most recent quarters
    quarters = conn.execute("""
        SELECT DISTINCT quarter_date FROM institutional_holdings
        WHERE cik = ? ORDER BY quarter_date DESC LIMIT 2
    """, (cik,)).fetchall()
    if not quarters:
        return None

    current_q = quarters[0]["quarter_date"]
    prev_q = quarters[1]["quarter_date"] if len(quarters) > 1 else None

    # Get current quarter holdings
    rows = conn.execute("""
        SELECT ticker, issuer, cusip, shares, value, filing_date, institution, short_name
        FROM institutional_holdings
        WHERE cik = ? AND quarter_date = ?
        ORDER BY value DESC
    """, (cik, current_q)).fetchall()
    if not rows:
        return None

    # Build a map of previous quarter values by cusip (universal ID)
    prev_values = {}
    prev_shares_map = {}
    prev_cusips = set()
    if prev_q:
        prev_rows = conn.execute("""
            SELECT cusip, ticker, value, shares FROM institutional_holdings
            WHERE cik = ? AND quarter_date = ?
        """, (cik, prev_q)).fetchall()
        for pr in prev_rows:
            key = pr["cusip"] or pr["ticker"]
            if key:
                prev_values[key] = pr["value"]
                prev_shares_map[key] = pr["shares"]
                prev_cusips.add(key)

    holdings = []
    total_value = 0
    for r in rows:
        val = r["value"] or 0
        total_value += val
        ticker = r["ticker"] or ""
        cusip = r["cusip"] or ""
        match_key = cusip or ticker

        # Compute QoQ change
        prev_val = prev_values.get(match_key)
        prev_sh = prev_shares_map.get(match_key)
        if prev_val and prev_val > 0:
            value_change_pct = round((val - prev_val) / prev_val * 100, 2)
        elif val > 0 and prev_val is None:
            value_change_pct = None  # New position — will show "NEW"
        else:
            value_change_pct = None

        # Detect stock splits for shares comparison
        split_ratio = 1
        if prev_sh and prev_sh > 0 and r["shares"] and r["shares"] > 0 and prev_val and prev_val > 0 and val > 0:
            split_ratio = _detect_split_ratio(r["shares"], prev_sh, val, prev_val)

        if prev_sh and prev_sh > 0 and r["shares"]:
            adj_prev_sh = prev_sh * split_ratio
            shares_change_pct = round((r["shares"] - adj_prev_sh) / adj_prev_sh * 100, 2)
        else:
            shares_change_pct = None

        is_new = match_key and match_key not in prev_cusips and prev_q is not None

        # Use issuer as display name when ticker is unknown
        display_ticker = ticker if ticker else ""

        holdings.append({
            "ticker": display_ticker,
            "issuer": r["issuer"] or "",
            "shares": r["shares"] or 0,
            "value": val,
            "change_pct": value_change_pct,
            "shares_change_pct": shares_change_pct,
            "is_new": is_new,
        })

    return {
        "name": rows[0]["institution"] if rows else "",
        "short_name": rows[0]["short_name"] if rows else "",
        "cik": cik,
        "total_value": total_value,
        "total_positions": len(holdings),
        "filing_date": rows[0]["filing_date"] if rows else "",
        "current_quarter": current_q,
        "previous_quarter": prev_q,
        "holdings": holdings,
    }


def create_user(email: str, password_hash: str, first_name: str) -> bool:
    """Create a new user. Returns True if successful, False if email exists."""
    conn = _conn()
    try:
        conn.execute("""
            INSERT INTO users (email, password_hash, first_name, created_at)
            VALUES (?, ?, ?, ?)
        """, (email, password_hash, first_name, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_user_by_email(email: str) -> Optional[Dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row:
        return dict(row)
    return None


def set_reset_token(email: str, token: str, expiry: datetime) -> bool:
    conn = _conn()
    cursor = conn.execute("""
        UPDATE users SET reset_token = ?, reset_token_expiry = ?
        WHERE email = ?
    """, (token, expiry.isoformat(), email))
    conn.commit()
    return cursor.rowcount > 0


def get_user_by_reset_token(token: str) -> Optional[Dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM users WHERE reset_token = ?", (token,)).fetchone()
    if row:
        return dict(row)
    return None


def update_password(user_id: int, new_password_hash: str):
    conn = _conn()
    conn.execute("""
        UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL
        WHERE id = ?
    """, (new_password_hash, user_id))
    conn.commit()


def add_alert(user_id: int, symbol: str, condition_type: str, threshold: float) -> bool:
    conn = _conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO alerts (user_id, symbol, condition_type, threshold, is_active, created_at)
        VALUES (?, ?, ?, ?, 1, ?)
    """, (user_id, symbol.upper(), condition_type, threshold, now))
    conn.commit()
    return True


def get_user_alerts(user_id: int) -> List[Dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM alerts WHERE user_id = ? AND is_active = 1", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def get_all_active_alerts() -> List[Dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM alerts WHERE is_active = 1").fetchall()
    return [dict(r) for r in rows]


def deactivate_alert(alert_id: int):
    conn = _conn()
    conn.execute("UPDATE alerts SET is_active = 0 WHERE id = ?", (alert_id,))
    conn.commit()


def create_notification(user_id: int, title: str, message: str):
    conn = _conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO notifications (user_id, title, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, title, message, now))
    conn.commit()


def get_user_notifications(user_id: int, unread_only: bool = True) -> List[Dict]:
    conn = _conn()
    if unread_only:
        rows = conn.execute("SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def mark_notifications_read(user_id: int):
    conn = _conn()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()


def get_user_preferences(user_id: int) -> Optional[Dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        pref = dict(row)
        pref['sectors'] = json.loads(pref['sectors']) if pref.get('sectors') else []
        pref['goals'] = json.loads(pref['goals']) if pref.get('goals') else []
        return pref
    return None


def update_user_preferences(user_id: int, experience: str, goals: List[str], sectors: List[str]) -> bool:
    conn = _conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO user_preferences (user_id, experience, goals, sectors, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            experience = excluded.experience,
            goals = excluded.goals,
            sectors = excluded.sectors,
            updated_at = excluded.updated_at
    """, (user_id, experience, json.dumps(goals), json.dumps(sectors), now))
    conn.commit()
    return True


def add_to_watchlist(user_id: int, ticker: str) -> bool:
    """Add a ticker to a user's watchlist."""
    import time
    conn = _conn()
    for attempt in range(5):
        try:
            conn.execute("""
                INSERT INTO watchlists (user_id, ticker, added_at)
                VALUES (?, ?, ?)
            """, (user_id, ticker.upper(), datetime.now(timezone.utc).isoformat()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already exists
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 4:
                time.sleep(0.5)
            else:
                raise


def remove_from_watchlist(user_id: int, ticker: str) -> bool:
    """Remove a ticker from a user's watchlist."""
    import time
    conn = _conn()
    for attempt in range(5):
        try:
            cursor = conn.execute("""
                DELETE FROM watchlists WHERE user_id = ? AND ticker = ?
            """, (user_id, ticker.upper()))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 4:
                time.sleep(0.5)
            else:
                raise


def clear_watchlist(user_id: int) -> bool:
    """Remove all tickers from a user's watchlist."""
    import time
    conn = _conn()
    for attempt in range(5):
        try:
            cursor = conn.execute("""
                DELETE FROM watchlists WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 4:
                time.sleep(0.5)
            else:
                raise


def get_watchlist(user_id: int) -> List[str]:
    """Get a user's watchlist as a list of tickers, ordered by most recently added."""
    conn = _conn()
    rows = conn.execute("""
        SELECT ticker FROM watchlists
        WHERE user_id = ?
        ORDER BY added_at DESC
    """, (user_id,)).fetchall()
    return [r["ticker"] for r in rows]


# -------------------------------------------------------------------
# Market Data (Decoupling)
# -------------------------------------------------------------------

def upsert_stock_prices(prices: List[Dict]):
    """Batch upsert real-time stock quotes from the background worker."""
    conn = _conn()
    now = datetime.now(timezone.utc).isoformat()
    for p in prices:
        if not p.get("ticker"):
            continue
        try:
            conn.execute("""
                INSERT INTO stock_prices (ticker, price, change, change_percent, market_cap, analyst_target, upside_pct, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    price = excluded.price,
                    change = excluded.change,
                    change_percent = excluded.change_percent,
                    market_cap = excluded.market_cap,
                    analyst_target = COALESCE(excluded.analyst_target, analyst_target),
                    upside_pct = COALESCE(excluded.upside_pct, upside_pct),
                    updated_at = excluded.updated_at
            """, (
                p["ticker"], p.get("price"), p.get("change"),
                p.get("change_percent"), p.get("market_cap"),
                p.get("analyst_target"), p.get("upside_pct"), now
            ))
        except Exception as e:
            logger.error("DB Error upserting %s: %s", p["ticker"], e)
    conn.commit()


def get_stock_prices(tickers: List[str]) -> Dict[str, Dict]:
    """Retrieve the latest cached prices for a list of tickers."""
    if not tickers:
        return {}
    conn = _conn()
    placeholders = ",".join("?" for _ in tickers)
    rows = conn.execute(f"""
        SELECT ticker, price, change, change_percent, market_cap, analyst_target, upside_pct, updated_at
        FROM stock_prices
        WHERE ticker IN ({placeholders})
    """, tuple(tickers)).fetchall()
    return {r["ticker"]: dict(r) for r in rows}


def upsert_sector_holdings(sector: str, holdings: List[Dict]):
    """
    Replace the entire ETF-based sector holdings list with fresh data.
    `holdings` should be a list of dicts: {"ticker": "AAPL", "weight": 12.5}
    """
    conn = _conn()
    now = datetime.now(timezone.utc).isoformat()
    # Delete old holdings for this sector
    conn.execute("DELETE FROM sector_holdings WHERE sector = ?", (sector,))
    
    # Insert new
    for h in holdings:
        if not h.get("ticker"):
            continue
        conn.execute("""
            INSERT INTO sector_holdings (sector, ticker, weight, updated_at)
            VALUES (?, ?, ?, ?)
        """, (sector, h["ticker"], h.get("weight", 0.0), now))
    conn.commit()


def get_sector_holdings(sector: str, limit: int = 15) -> List[Dict]:
    """Get the top ETF-derived holdings for a specific sector, enriched with current prices."""
    conn = _conn()
    rows = conn.execute("""
        SELECT h.ticker, h.weight, p.price, p.change, p.change_percent, p.market_cap, p.analyst_target, p.upside_pct, p.updated_at
        FROM sector_holdings h
        LEFT JOIN stock_prices p ON h.ticker = p.ticker
        WHERE h.sector = ?
        ORDER BY h.weight DESC
        LIMIT ?
    """, (sector, limit)).fetchall()
    return [dict(r) for r in rows]

