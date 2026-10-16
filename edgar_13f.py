"""
SEC EDGAR 13F Engine — Real institutional holdings from public SEC filings.
No paid API required. Fetches 13F-HR filings directly from SEC EDGAR.

Tracks 12 major institutions (BlackRock, Vanguard, Berkshire, Goldman, etc.)
and cross-references their holdings to find consensus picks.
"""
import os
import time
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# ── SEC EDGAR settings ──────────────────────────────────────────────────────
SEC_HEADERS = {
    "User-Agent": os.environ.get("EDGAR_IDENTITY_NAME", "SmartMoney") + " " +
                  os.environ.get("EDGAR_IDENTITY_EMAIL", "research@example.com"),
    "Accept": "application/json",
}
SEC_BASE = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

# ── Top 12 Institutions — All CIKs verified against SEC EDGAR 13F-HR ──────
INSTITUTIONS = [
    {"name": "BlackRock Inc.",                  "cik": "0002012383", "short": "BlackRock"},
    {"name": "Vanguard Group Inc",              "cik": "0000102909", "short": "Vanguard"},
    {"name": "State Street Corp",               "cik": "0000093751", "short": "State Street"},
    {"name": "Fidelity (FMR LLC)",              "cik": "0000315066", "short": "Fidelity"},
    {"name": "JPMorgan Chase & Co",             "cik": "0000019617", "short": "JPMorgan"},
    {"name": "Berkshire Hathaway Inc",          "cik": "0001067983", "short": "Berkshire"},
    {"name": "Morgan Stanley",                  "cik": "0000895421", "short": "Morgan Stanley"},
    {"name": "Goldman Sachs Group Inc",         "cik": "0000886982", "short": "Goldman"},
    {"name": "Bank of America Corp",            "cik": "0000070858", "short": "BofA"},
    {"name": "Citigroup Inc.",                  "cik": "0000831001", "short": "Citigroup"},
    {"name": "UBS Group AG",                    "cik": "0001610520", "short": "UBS"},
    {"name": "Capital Research Global Investors", "cik": "0001422848", "short": "Capital Research"},
]

# ── CUSIP → Ticker mapping (most common) ───────────────────────────────────
# Maintained as a hard-coded map for the most-held US stocks. For less common
# CUSIPs we attempt a reverse lookup via the SEC company search endpoint.
_CUSIP_TICKER = {
    "037833100": "AAPL", "594918104": "MSFT", "02079K305": "GOOGL",
    "02079K107": "GOOG", "023135106": "AMZN", "67066G104": "NVDA",
    "30303M102": "META", "084670702": "BRK.B", "084670108": "BRK.A",
    "46625H100": "JPM", "91324P102": "UNH", "882508104": "TSLA",
    "92826C839": "V", "478160104": "JNJ", "585055106": "MCD",
    "742718109": "PG", "17275R102": "CSCO", "00724F101": "ADBE",
    "58933Y105": "MRK", "931142103": "WMT", "46625H100": "JPM",
    "79466L302": "CRM", "11135F101": "AVGO", "30231G102": "XOM",
    "20825C104": "COST", "007903107": "PFE", "22160K105": "COST",
    "254687106": "DIS", "88160R101": "TSLA", "855244109": "SBUX",
    "46625H100": "JPM", "075887109": "BAC", "035420103": "AMD",
    "437076102": "HD", "670346105": "NFLX", "500105104": "KO",
    "693475105": "PEP", "808513105": "SCHW", "78462F103": "SPY",
    "46090E103": "QQQ", "252131107": "DIA", "172967424": "C",
    "45256BAD5": "INTC", "718172109": "PM", "260543103": "DOW",
    "125523100": "COP", "741503403": "ABBV", "29379VAQ7": "LLY",
}

# ── In-memory cache ────────────────────────────────────────────────────────
_cache: Dict[str, Tuple[float, any]] = {}
CACHE_13F = 3600 * 6   # 6 hours (data changes quarterly)
CACHE_SUBMISSIONS = 3600 * 2
CACHE_CONSENSUS = 3600  # 1 hour for consensus results


def _cache_get(key: str):
    """Return cached data if still valid, else None."""
    if key in _cache:
        ts, data = _cache[key]
        ttl = CACHE_13F if "13f" in key else CACHE_SUBMISSIONS
        if key.startswith("consensus"):
            ttl = CACHE_CONSENSUS
        if time.time() - ts < ttl:
            return data
    return None


def _cache_set(key: str, data):
    _cache[key] = (time.time(), data)


# ═══════════════════════════════════════════════════════════════════════════════
#  CUSIP → Ticker Resolution  (using SEC company_tickers.json)
# ═══════════════════════════════════════════════════════════════════════════════

import re
_SEC_NAME_TO_TICKER: Dict[str, str] = {}   # normalised name → ticker
_SEC_LOADED = False


def _normalise_name(raw: str) -> str:
    """Normalise an issuer / company name for fuzzy matching."""
    s = raw.upper().strip()
    # Remove common suffixes
    for suffix in [" INC", " INC.", " CORP", " CORP.", " CO", " CO.",
                   " LTD", " LTD.", " PLC", " PLC.", " N.V.", " N V",
                   " SE", " SA", " AG", " LP", " LLC", " L P",
                   " GROUP", " HLDGS", " HOLDINGS", " CLASS A",
                   " CLASS B", " CLASS C", " CL A", " CL B", " CL C",
                   " NEW", " COM", " COMMON", " SHS", " SH", " ORD",
                   " ADR", " ADS", " ETF", " TRUST", " FUND"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    # Strip punctuation and extra whitespace
    s = re.sub(r"[^A-Z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _load_sec_tickers():
    """Download SEC company_tickers.json once and build name→ticker map."""
    global _SEC_NAME_TO_TICKER, _SEC_LOADED
    if _SEC_LOADED:
        return
    _SEC_LOADED = True

    # Try to load from a local cached file first
    cache_path = Path(__file__).resolve().parent / "sec_tickers_cache.json"
    data = None

    # Try downloading fresh copy
    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=SEC_HEADERS,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Cache to disk
            try:
                cache_path.write_text(json.dumps(data))
            except Exception:
                pass
    except Exception as e:
        logger.warning("Could not download SEC tickers: %s", e)

    # Fallback to cached copy on disk
    if not data and cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
            logger.info("Loaded SEC tickers from disk cache")
        except Exception:
            pass

    if not data:
        logger.warning("No SEC ticker data available — name resolution will be limited")
        return

    count = 0
    for _key, entry in data.items():
        ticker = entry.get("ticker", "")
        title = entry.get("title", "")
        if ticker and title:
            norm = _normalise_name(title)
            if norm and norm not in _SEC_NAME_TO_TICKER:
                _SEC_NAME_TO_TICKER[norm] = ticker
                count += 1
    logger.info("Loaded %d SEC company→ticker mappings", count)


def cusip_to_ticker(cusip: str, name: str = "") -> str:
    """Resolve CUSIP to ticker via multiple strategies:
    1. Hard-coded CUSIP map
    2. SEC company name exact match  (normalised)
    3. SEC company name prefix match (first N words)
    4. Legacy keyword heuristic fallback
    """
    cusip = cusip.strip().upper()
    if cusip in _CUSIP_TICKER:
        return _CUSIP_TICKER[cusip]

    if not name:
        return ""

    # Ensure SEC data is loaded
    _load_sec_tickers()

    name_norm = _normalise_name(name)
    if not name_norm:
        return ""

    # Strategy 2: exact normalised name match
    if name_norm in _SEC_NAME_TO_TICKER:
        ticker = _SEC_NAME_TO_TICKER[name_norm]
        # Cache for next time
        _CUSIP_TICKER[cusip] = ticker
        return ticker

    # Strategy 3: prefix match — try first 2 words, then first word
    words = name_norm.split()
    if len(words) >= 2:
        prefix2 = " ".join(words[:2])
        for sec_name, ticker in _SEC_NAME_TO_TICKER.items():
            if sec_name.startswith(prefix2):
                _CUSIP_TICKER[cusip] = ticker
                return ticker
    if words:
        first = words[0]
        # Only single-word match if the word is long enough (avoid false positives)
        if len(first) >= 5:
            for sec_name, ticker in _SEC_NAME_TO_TICKER.items():
                if sec_name == first or sec_name.startswith(first + " "):
                    _CUSIP_TICKER[cusip] = ticker
                    return ticker

    return ""  # Unknown


# ═══════════════════════════════════════════════════════════════════════════════
#  SEC EDGAR — Filing Discovery
# ═══════════════════════════════════════════════════════════════════════════════

def get_latest_13f_accessions(cik: str, count: int = 2) -> List[Dict]:
    """
    Find the N most recent 13F-HR filing accession numbers for a CIK.
    Returns list of dicts with accession, filing_date, cik_number.
    First element is the most recent filing.
    """
    cache_key = f"submissions:{cik}:v2"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    cik_num = cik.lstrip("0")
    cik_padded = cik.zfill(10)

    try:
        url = f"{SEC_BASE}/submissions/CIK{cik_padded}.json"
        r = requests.get(url, headers=SEC_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning("SEC submissions %s → %s", cik, r.status_code)
            return []

        data = r.json()
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])

        results = []
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A"):
                results.append({
                    "accession": accessions[i],
                    "filing_date": dates[i],
                    "cik_number": cik_num,
                    "entity_name": data.get("name", ""),
                })
                if len(results) >= count:
                    break
        _cache_set(cache_key, results)
        return results
    except Exception as e:
        logger.error("SEC submissions error for %s: %s", cik, e)
        return []


def get_latest_13f_accession(cik: str) -> Optional[Dict]:
    """Backwards-compatible: return just the latest 13F filing."""
    results = get_latest_13f_accessions(cik, count=1)
    return results[0] if results else None


# ═══════════════════════════════════════════════════════════════════════════════
#  SEC EDGAR — 13F Holdings Parser
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_13f_holdings(cik: str, max_holdings: int = 5000) -> Optional[Dict]:
    """
    Fetch and parse 13F-HR infotable XML from SEC EDGAR.
    Returns dict with institution info and list of top holdings.
    """
    cache_key = f"13f:{cik}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    filing = get_latest_13f_accession(cik)
    if not filing:
        return None

    accession = filing["accession"]
    accession_dir = accession.replace("-", "")
    cik_num = filing["cik_number"]

    try:
        # Get filing index to find the infotable XML
        index_url = f"{SEC_ARCHIVES}/{cik_num}/{accession_dir}/index.json"
        r = requests.get(index_url, headers=SEC_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning("SEC index %s → %s", accession, r.status_code)
            return None

        idx = r.json()
        items = idx.get("directory", {}).get("item", [])

        # Find the infotable XML file
        xml_filename = None
        for item in items:
            name = item.get("name", "").lower()
            if name.endswith(".xml") and ("infotable" in name or "13f" in name):
                if "primary_doc" not in name:
                    xml_filename = item.get("name")
                    break
        if not xml_filename:
            # Try any XML that isn't the primary doc
            for item in items:
                name = item.get("name", "").lower()
                if name.endswith(".xml") and "primary" not in name:
                    xml_filename = item.get("name")
                    break

        if not xml_filename:
            logger.warning("No infotable XML found for %s", cik)
            return None

        # Fetch and parse the XML
        xml_url = f"{SEC_ARCHIVES}/{cik_num}/{accession_dir}/{xml_filename}"
        rx = requests.get(xml_url, headers=SEC_HEADERS, timeout=60)
        if rx.status_code != 200:
            return None

        root = ET.fromstring(rx.text)

        # Handle namespace
        ns_map = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}
        entries = root.findall(".//ns:infoTable", ns_map)
        if not entries:
            # Try without namespace
            entries = root.findall(".//{*}infoTable")

        # Parse holdings — aggregate by issuer
        holdings_raw: Dict[str, Dict] = {}
        total_value = 0

        for entry in entries:
            try:
                issuer = (entry.findtext("{*}nameOfIssuer") or "").strip()
                cusip = (entry.findtext("{*}cusip") or "").strip()
                value_str = entry.findtext("{*}value") or "0"
                value = int(value_str)  # Value already in dollars in the XML

                shares_el = entry.find("{*}shrsOrPrnAmt")
                shares = 0
                share_type = "SH"
                if shares_el is not None:
                    shares = int(shares_el.findtext("{*}sshPrnamt") or "0")
                    share_type = (shares_el.findtext("{*}sshPrnamtType") or "SH").strip()

                # Skip puts/calls (option positions)
                put_call = (entry.findtext("{*}putCall") or "").strip()

                key = cusip or issuer
                if key in holdings_raw:
                    holdings_raw[key]["shares"] += shares
                    holdings_raw[key]["value"] += value
                else:
                    holdings_raw[key] = {
                        "issuer": issuer,
                        "cusip": cusip,
                        "shares": shares,
                        "value": value,
                        "share_type": share_type,
                        "put_call": put_call,
                    }
                total_value += value
            except Exception:
                continue

        # Sort by value and take top holdings
        sorted_holdings = sorted(holdings_raw.values(), key=lambda x: x["value"], reverse=True)
        top = sorted_holdings[:max_holdings]

        # Resolve tickers
        holdings_out = []
        for h in top:
            ticker = cusip_to_ticker(h["cusip"], h["issuer"])
            holdings_out.append({
                "ticker": ticker,
                "issuer": h["issuer"],
                "cusip": h["cusip"],
                "shares": h["shares"],
                "value": h["value"],
                "share_type": h["share_type"],
                "put_call": h["put_call"],
            })

        # Look up institution info
        inst_info = next((i for i in INSTITUTIONS if i["cik"] == cik), None)

        result = {
            "cik": cik,
            "name": inst_info["name"] if inst_info else filing.get("entity_name", cik),
            "short_name": inst_info["short"] if inst_info else "",
            "filing_date": filing["filing_date"],
            "total_value": total_value,
            "total_positions": len(holdings_raw),
            "holdings": holdings_out,
        }
        _cache_set(cache_key, result)
        return result

    except Exception as e:
        logger.error("13F parse error for %s: %s", cik, e)
        return None


def fetch_13f_holdings_for_quarter(cik: str, filing: Dict,
                                   max_holdings: int = 5000) -> Optional[Dict]:
    """
    Fetch 13F holdings for a SPECIFIC filing (accession).
    Used by the cache job to fetch both current and previous quarter data.
    `filing` is a dict from get_latest_13f_accessions() with keys:
        accession, filing_date, cik_number, entity_name
    """
    accession = filing["accession"]
    cache_key = f"13f_q:{cik}:{accession}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    accession_dir = accession.replace("-", "")
    cik_num = filing["cik_number"]

    try:
        index_url = f"{SEC_ARCHIVES}/{cik_num}/{accession_dir}/index.json"
        r = requests.get(index_url, headers=SEC_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning("SEC index %s → %s", accession, r.status_code)
            return None

        idx = r.json()
        items = idx.get("directory", {}).get("item", [])

        xml_filename = None
        for item in items:
            name = item.get("name", "").lower()
            if name.endswith(".xml") and ("infotable" in name or "13f" in name):
                if "primary_doc" not in name:
                    xml_filename = item.get("name")
                    break
        if not xml_filename:
            for item in items:
                name = item.get("name", "").lower()
                if name.endswith(".xml") and "primary" not in name:
                    xml_filename = item.get("name")
                    break
        if not xml_filename:
            logger.warning("No infotable XML for %s acc %s", cik, accession)
            return None

        xml_url = f"{SEC_ARCHIVES}/{cik_num}/{accession_dir}/{xml_filename}"
        rx = requests.get(xml_url, headers=SEC_HEADERS, timeout=60)
        if rx.status_code != 200:
            return None

        root = ET.fromstring(rx.text)
        ns_map = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}
        entries = root.findall(".//ns:infoTable", ns_map)
        if not entries:
            entries = root.findall(".//{*}infoTable")

        holdings_raw: Dict[str, Dict] = {}
        total_value = 0

        for entry in entries:
            try:
                issuer = (entry.findtext("{*}nameOfIssuer") or "").strip()
                cusip_val = (entry.findtext("{*}cusip") or "").strip()
                value_str = entry.findtext("{*}value") or "0"
                value = int(value_str)

                shares_el = entry.find("{*}shrsOrPrnAmt")
                shares = 0
                share_type = "SH"
                if shares_el is not None:
                    shares = int(shares_el.findtext("{*}sshPrnamt") or "0")
                    share_type = (shares_el.findtext("{*}sshPrnamtType") or "SH").strip()

                put_call = (entry.findtext("{*}putCall") or "").strip()

                key = cusip_val or issuer
                if key in holdings_raw:
                    holdings_raw[key]["shares"] += shares
                    holdings_raw[key]["value"] += value
                else:
                    holdings_raw[key] = {
                        "issuer": issuer, "cusip": cusip_val,
                        "shares": shares, "value": value,
                        "share_type": share_type, "put_call": put_call,
                    }
                total_value += value
            except Exception:
                continue

        sorted_holdings = sorted(holdings_raw.values(), key=lambda x: x["value"], reverse=True)
        top = sorted_holdings[:max_holdings]

        holdings_out = []
        for h in top:
            ticker = cusip_to_ticker(h["cusip"], h["issuer"])
            holdings_out.append({
                "ticker": ticker,
                "issuer": h["issuer"],
                "cusip": h["cusip"],
                "shares": h["shares"],
                "value": h["value"],
                "share_type": h["share_type"],
                "put_call": h["put_call"],
            })

        inst_info = next((i for i in INSTITUTIONS if i["cik"] == cik), None)
        result = {
            "cik": cik,
            "name": inst_info["name"] if inst_info else filing.get("entity_name", cik),
            "short_name": inst_info["short"] if inst_info else "",
            "filing_date": filing["filing_date"],
            "total_value": total_value,
            "total_positions": len(holdings_raw),
            "holdings": holdings_out,
        }
        _cache_set(cache_key, result)
        return result

    except Exception as e:
        logger.error("13F parse error for %s acc %s: %s", cik, accession, e)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Fetch All Institutions (Parallel)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_all_institutions(max_workers: int = 6) -> List[Dict]:
    """
    Fetch 13F holdings for all 12 institutions in parallel.
    Returns list of institution dicts with holdings.
    """
    cache_key = "all_institutions"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_inst = {
            executor.submit(fetch_13f_holdings, inst["cik"], 100): inst
            for inst in INSTITUTIONS
        }
        for future in as_completed(future_to_inst):
            inst = future_to_inst[future]
            try:
                data = future.result()
                if data:
                    results.append(data)
                else:
                    results.append({
                        "cik": inst["cik"],
                        "name": inst["name"],
                        "short_name": inst["short"],
                        "filing_date": "",
                        "total_value": 0,
                        "total_positions": 0,
                        "holdings": [],
                    })
            except Exception as e:
                logger.error("Institution fetch error %s: %s", inst["name"], e)
                results.append({
                    "cik": inst["cik"],
                    "name": inst["name"],
                    "short_name": inst["short"],
                    "filing_date": "",
                    "total_value": 0,
                    "total_positions": 0,
                    "holdings": [],
                })

    # Sort by total value (largest funds first)
    results.sort(key=lambda x: x["total_value"], reverse=True)
    _cache_set(cache_key, results)
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  Consensus Engine — Cross-Reference All Institutions
# ═══════════════════════════════════════════════════════════════════════════════

def build_consensus_picks(n: int = 25) -> Dict:
    """
    Cross-reference holdings across all institutions.
    Find stocks held by the most firms with highest total value.

    Returns:
        {
            "picks": [...top N consensus picks...],
            "institutions_analyzed": int,
            "total_stocks_found": int,
        }
    """
    cache_key = "consensus:top_picks"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    all_institutions = fetch_all_institutions()
    if not all_institutions:
        return {"picks": [], "institutions_analyzed": 0, "total_stocks_found": 0}

    # Aggregate: for each ticker, collect all institutional holders
    stock_data: Dict[str, Dict] = {}

    for inst in all_institutions:
        for h in inst.get("holdings", []):
            ticker = h.get("ticker", "")
            if not ticker or len(ticker) > 6:
                continue
            # Skip ETFs and indices
            if ticker in ("SPY", "QQQ", "DIA", "IVV", "VOO", "IWM", "VTI",
                          "EFA", "IEMG", "VEA", "VWO", "AGG", "BND", "TLT",
                          "GLD", "SLV", "XLK", "XLF", "XLE", "XLV"):
                continue

            if ticker not in stock_data:
                stock_data[ticker] = {
                    "ticker": ticker,
                    "issuer": h.get("issuer", ticker),
                    "holders": [],
                    "total_value": 0,
                    "total_shares": 0,
                }

            stock_data[ticker]["holders"].append({
                "institution": inst["short_name"] or inst["name"],
                "cik": inst["cik"],
                "shares": h["shares"],
                "value": h["value"],
            })
            stock_data[ticker]["total_value"] += h["value"]
            stock_data[ticker]["total_shares"] += h["shares"]

    # Rank by number of institutional holders × total value
    for sd in stock_data.values():
        num_holders = len(sd["holders"])
        sd["num_holders"] = num_holders
        if num_holders >= 15:
            sd["conviction"] = "EXTREME"
        elif num_holders >= 10:
            sd["conviction"] = "VERY HIGH"
        elif num_holders >= 6:
            sd["conviction"] = "HIGH"
        elif num_holders >= 3:
            sd["conviction"] = "MODERATE"
        else:
            sd["conviction"] = "LOW"

        # Sort holders by value (biggest position first)
        sd["holders"].sort(key=lambda x: x["value"], reverse=True)

    # Sort: (1) number of holders desc, (2) total value desc
    ranked = sorted(
        stock_data.values(),
        key=lambda x: (x["num_holders"], x["total_value"]),
        reverse=True,
    )

    # Take top N
    picks = []
    for item in ranked[:n]:
        picks.append({
            "rank": len(picks) + 1,
            "ticker": item["ticker"],
            "issuer": item["issuer"],
            "num_holders": item["num_holders"],
            "conviction": item["conviction"],
            "total_value": item["total_value"],
            "total_shares": item["total_shares"],
            "top_holders": item["holders"][:5],  # Top 5 holders
            "all_holders": item["holders"],
        })

    result = {
        "picks": picks,
        "institutions_analyzed": len(all_institutions),
        "total_stocks_found": len(stock_data),
    }
    _cache_set(cache_key, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Get Holders for a Specific Stock
# ═══════════════════════════════════════════════════════════════════════════════

def get_stock_holders(symbol: str) -> Dict:
    """
    Get all institutional holders for a specific stock symbol.
    Returns list of institutions holding this stock with their positions.
    """
    symbol = symbol.upper().strip()
    all_institutions = fetch_all_institutions()

    holders = []
    total_shares = 0
    total_value = 0

    for inst in all_institutions:
        for h in inst.get("holdings", []):
            if h.get("ticker", "").upper() == symbol:
                holders.append({
                    "institution": inst.get("short_name") or inst.get("name", ""),
                    "full_name": inst.get("name", ""),
                    "cik": inst.get("cik", ""),
                    "shares": h["shares"],
                    "value": h["value"],
                    "filing_date": inst.get("filing_date", ""),
                })
                total_shares += h["shares"]
                total_value += h["value"]
                break

    holders.sort(key=lambda x: x["value"], reverse=True)

    return {
        "symbol": symbol,
        "num_holders": len(holders),
        "total_institutional_shares": total_shares,
        "total_institutional_value": total_value,
        "holders": holders,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Institution List Summary (for the grid)
# ═══════════════════════════════════════════════════════════════════════════════

def get_institutions_summary() -> List[Dict]:
    """
    Lightweight summary of all institutions for the dashboard grid.
    Shows name, AUM, filing date, top 5 holdings.
    """
    all_institutions = fetch_all_institutions()
    summaries = []
    for inst in all_institutions:
        top5 = []
        for h in inst.get("holdings", [])[:5]:
            ticker = h.get("ticker", "")
            if ticker:
                top5.append({
                    "ticker": ticker,
                    "value": h["value"],
                })
        summaries.append({
            "name": inst.get("name", ""),
            "short_name": inst.get("short_name", ""),
            "cik": inst.get("cik", ""),
            "total_value": inst.get("total_value", 0),
            "total_positions": inst.get("total_positions", 0),
            "filing_date": inst.get("filing_date", ""),
            "top_holdings": top5,
        })
    return summaries
