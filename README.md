# Live Stock Picks & Market Intelligence

Real-time dashboard: **best stocks to buy today**, **market news**, and **actionable advice** (e.g. after inflation data: jump in, stay out, or stay selective — and why).  
**All results are in English.**

## How to open the website

**Quick way (Mac/Linux):**
```bash
cd /Users/roncohen/bot/webapp
chmod +x run_website.sh
./run_website.sh
```
Then open **http://127.0.0.1:5000** in your browser (the script may open it for you).

**Manual way:**
1. Install Flask once: `pip3 install flask` (or `pip install flask`)
2. From the **bot** folder: `cd webapp` then `python3 app.py`
3. In your browser go to: **http://127.0.0.1:5000** or **http://localhost:5000**
4. To stop the server: press **Ctrl+C** in the terminal

See **HOW_TO_OPEN.md** in this folder for more detail.

## Features

- **Best stocks today** – Same-day picks from the Institutional Analyzer (loads from latest report or runs analysis on "Refresh stocks").
- **What to do now** – After key economic events (CPI, Fed, jobs, etc.), the app shows:
  - **Jump in** – Favorable conditions (e.g. inflation cooling).
  - **Stay out** – Unfavorable (e.g. hot inflation, hawkish Fed).
  - **Stay selective** – Mixed; focus on quality and size risk.
- **Market news** – Headlines that can move the market (sample data if no API key; set `FINNHUB_API_KEY` or `NEWS_API_KEY` for live news).

## Data sources (recommended)

- **POLYGON_API_KEY** – [Polygon.io](https://polygon.io): **market data** — Reference Data (complete list of all tickers), Last Trade / Snapshot for **real-time prices**. Used for search and quotes.
- **FMP_API_KEY** – [Financial Modeling Prep](https://site.financialmodelingprep.com): **institutional data only** — Institutional Stock Ownership, Major Holders (13F), analyst price target, news. Required for valid institutional accumulation/holding data and Institutional Breakout filter.

Without Polygon: search and quote fall back to FMP then yfinance. Without FMP: institutional data uses fallback (less accurate).

## APIs

- `GET /api/stocks` – Best stocks (cached; `?refresh=1` to run analyzer).
- `GET /api/news` – News + advice (high-impact filter).
- `GET /api/search?q=...` – Symbol search (Polygon Reference → FMP → Finnhub).
- `GET /api/quote/<symbol>` – Real-time quote (Polygon → FMP → yfinance).
- `GET /api/hot-stocks` – High-momentum stocks (prices from Polygon when available).
- `GET /api/institutional-breakout` – High momentum + **net positive institutional inflow** (13F); net-sell names excluded. Prices from Polygon.
- `GET /api/stock/<symbol>/full` – Full stock: quote (Polygon/FMP), **institutional from FMP only**, analyst, bottom line, insider, sentiment.
- `GET /stock/<symbol>` – Stock Detail page (HTML).

All Hebrew in the project has been translated to English (main, reporter, trends, bot).
