/* ═══════════════════════════════════════════════════════════════════════════
   Smart Money Terminal — Dashboard Controller
   ═══════════════════════════════════════════════════════════════════════════ */

// ── Utilities ──────────────────────────────────────────────────────────────

function fmtMoney(val) {
  if (!val && val !== 0) return "—";
  const abs = Math.abs(val);
  if (abs >= 1e12) return "$" + (val / 1e12).toFixed(1) + "T";
  if (abs >= 1e9) return "$" + (val / 1e9).toFixed(1) + "B";
  if (abs >= 1e6) return "$" + (val / 1e6).toFixed(1) + "M";
  if (abs >= 1e3) return "$" + (val / 1e3).toFixed(0) + "K";
  return "$" + val.toFixed(2);
}

function fmtPrice(val) {
  if (!val && val !== 0) return "—";
  return "$" + Number(val).toFixed(2);
}

function fmtPct(val) {
  if (val == null) return "";
  const sign = val >= 0 ? "+" : "";
  return sign + Number(val).toFixed(2) + "%";
}

function fmtShares(val) {
  if (!val) return "—";
  if (val >= 1e6) return (val / 1e6).toFixed(1) + "M";
  if (val >= 1e3) return (val / 1e3).toFixed(0) + "K";
  return val.toLocaleString();
}

function changeClass(val) {
  return val >= 0 ? "up" : "down";
}


// ── API Fetch ──────────────────────────────────────────────────────────────

async function apiFetch(path) {
  try {
    const r = await fetch(path);
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (e) {
    console.error("API error:", path, e);
    return null;
  }
}


// ═══════════════════════════════════════════════════════════════════════════
//  BREAKING NEWS TICKER
// ═══════════════════════════════════════════════════════════════════════════

async function loadBreakingNews() {
  const data = await apiFetch("/api/breaking-news");
  if (!data || !data.news || !data.news.length) return;

  const items = data.news;
  const el = document.getElementById("ticker-content");
  if (!el) return;

  // AI Morning Brief Check (run concurrently)
  loadMorningBrief();

  // Build ticker HTML — duplicate for seamless loop
  let html = "";
  for (let pass = 0; pass < 2; pass++) {
    for (const item of items) {
      let alertHtml = "";
      if (item.alert === "SELL!!!") {
        alertHtml = '<span class="ticker-alert sell">SELL!!!</span>';
      } else if (item.alert === "CAUTION") {
        alertHtml = '<span class="ticker-alert caution">CAUTION</span>';
      } else if (item.alert === "BULLISH") {
        alertHtml = '<span class="ticker-alert bullish">BULLISH</span>';
      }
      html += `<span class="ticker-item">${alertHtml}<a href="${item.url || '#'}" target="_blank" rel="noopener">${escHtml(item.title)}</a></span><span class="ticker-sep">•</span>`;
    }
  }
  el.innerHTML = html;
}

function escHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}


// ═══════════════════════════════════════════════════════════════════════════
//  AI MORNING BRIEF
// ═══════════════════════════════════════════════════════════════════════════

async function loadMorningBrief() {
  const card = document.getElementById("aiMorningBriefCard");
  const content = document.getElementById("aiBriefContent");
  if (!card || !content) return;

  card.style.display = "block";
  content.innerHTML = `<div style="display:flex; align-items:center; gap:0.5rem; color:var(--text-dim);"><div class="loading-spinner" style="width:16px;height:16px;border-width:2px;border-color:#8B5CF6 transparent transparent transparent;"></div> Generating your personalized brief...</div>`;

  try {
    const res = await fetch("/api/ai/morning-brief");
    if (!res.ok) throw new Error("Failed to load brief");
    const data = await res.json();

    if (data.brief) {
      content.innerHTML = data.brief.replace(/\n\n/g, '<br><br>');
    } else {
      card.style.display = "none";
    }
  } catch (e) {
    console.warn("Morning brief failed:", e);
    card.style.display = "none";
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  ALPHA SCREENER — Next Big Stock
// ═══════════════════════════════════════════════════════════════════════════

async function loadAlphaScreener() {
  const el = document.getElementById("alpha-screener-body");
  const updatedEl = document.getElementById("alpha-updated");
  if (!el) return;

  const data = await apiFetch("/api/alpha-screener");
  if (!data || !data.picks || !data.picks.length) {
    el.innerHTML = '<div class="loading-shimmer">Screener is warming up — first scan takes a few minutes...</div>';
    // Retry in 30s
    setTimeout(loadAlphaScreener, 30000);
    return;
  }

  if (updatedEl && data.updated_at) {
    const d = new Date(data.updated_at);
    updatedEl.textContent = `Updated ${d.toLocaleTimeString()}`;
  }

  const paramLabels = {
    market_cap: "Market Cap",
    revenue_growth: "Revenue Growth",
    institutional: "Inst. Accumulation",
    insider_buying: "Insider Buying",
    volume_breakout: "Volume Breakout",
    price_vs_52w: "52-Week Position",
    analyst_momentum: "Analyst Upgrades",
    debt_equity: "Low Debt",
    operating_margin: "Op. Margin",
    pe_ratio: "Valuation",
    price_breakout: "Price Breakout",
    upside_potential: "Upside Potential",
  };

  const cards = data.picks.map((p, i) => {
    const scoreBarWidth = Math.min(p.composite_score, 100);
    const scoreColor = scoreBarWidth >= 70 ? '#10B981' : scoreBarWidth >= 50 ? '#F59E0B' : '#EF4444';
    const changeCls = (p.change_percent || 0) >= 0 ? 'up' : 'down';
    const mcapStr = p.market_cap ? fmtMoney(p.market_cap) : '—';

    // Top 3 parameters
    let paramBars = '';
    if (p.scores) {
      const sorted = Object.entries(p.scores)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4);
      paramBars = sorted.map(([key, val]) => {
        const pct = val * 10;
        const label = paramLabels[key] || key;
        const barColor = pct >= 70 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#6B7280';
        return `
          <div class="alpha-param">
            <span class="alpha-param-label">${label}</span>
            <div class="alpha-param-bar"><div class="alpha-param-fill" style="width:${pct}%;background:${barColor}"></div></div>
            <span class="alpha-param-val">${val}/10</span>
          </div>`;
      }).join('');
    }

    return `
      <div class="alpha-stock-card" onclick="window.location='/stock/${p.symbol}'">
        <div class="alpha-rank">${i + 1}</div>
        <div class="alpha-main">
          <div class="alpha-header">
            <div>
              <span class="alpha-symbol">${p.symbol}</span>
              <span class="alpha-name">${escHtml(p.name || '')}</span>
            </div>
            <div class="alpha-price-block">
              <span class="alpha-price">${fmtPrice(p.price)}</span>
              <span class="alpha-change ${changeCls}">${fmtPct(p.change_percent)}</span>
            </div>
          </div>
          <div class="alpha-meta">
            <span class="alpha-sector-badge">${escHtml(p.sector || '')}</span>
            <span class="alpha-mcap">${mcapStr} mcap</span>
            ${p.upside_pct != null ? `<span class="alpha-upside ${p.upside_pct >= 0 ? 'positive' : 'negative'}">▲ ${Math.abs(p.upside_pct).toFixed(0)}% analyst upside</span>` : ''}
            ${p.num_institutions ? `<span class="alpha-inst">${p.num_institutions} institutions</span>` : ''}
            ${p.insider_buys ? `<span class="alpha-insider">🟢 ${p.insider_buys} insider buys</span>` : ''}
          </div>
          <div class="alpha-score-row">
            <div class="alpha-score-bar-bg">
              <div class="alpha-score-bar-fill" style="width:${scoreBarWidth}%;background:linear-gradient(90deg,${scoreColor}88,${scoreColor})"></div>
            </div>
            <span class="alpha-score-val">${p.composite_score.toFixed(0)}</span>
          </div>
          <div class="alpha-thesis">${escHtml(p.thesis || '')}</div>
          <div class="alpha-params">${paramBars}</div>
        </div>
      </div>`;
  }).join('');

  el.innerHTML = `<div class="alpha-grid">${cards}</div>`;
}


// ═══════════════════════════════════════════════════════════════════════════
//  MARKET BAR (SPY, QQQ, DIA) — Live refresh
// ═══════════════════════════════════════════════════════════════════════════

const _prevMarketPrices = {};  // Track previous prices for flash animations

async function loadMarketBar() {
  const data = await apiFetch("/api/market-indices");
  if (!data || !data.indices) return;

  const el = document.getElementById("market-bar");
  if (!el) return;

  // First load — build structure
  if (!el.querySelector('.market-item')) {
    el.innerHTML = data.indices.map(idx => `
      <div class="market-item" id="mi-${idx.symbol}" onclick="window.location='/stock/${idx.symbol}'" style="cursor:pointer;">
        <span class="mi-sym">${idx.symbol}</span>
        <span class="mi-price" id="mi-price-${idx.symbol}">${fmtPrice(idx.price)}</span>
        <span class="mi-change ${changeClass(idx.change_percent)}" id="mi-change-${idx.symbol}">${fmtPct(idx.change_percent)}</span>
      </div>
    `).join("");
    // Store initial prices
    data.indices.forEach(idx => { _prevMarketPrices[idx.symbol] = idx.price; });
    return;
  }

  // Subsequent loads — update in-place with animations
  data.indices.forEach(idx => {
    const priceEl = document.getElementById(`mi-price-${idx.symbol}`);
    const changeEl = document.getElementById(`mi-change-${idx.symbol}`);
    if (!priceEl || !changeEl) return;

    const prevPrice = _prevMarketPrices[idx.symbol];
    const newPrice = idx.price;

    // Update price text
    priceEl.textContent = fmtPrice(newPrice);

    // Flash animation if price changed
    if (prevPrice != null && newPrice != null && prevPrice !== newPrice) {
      priceEl.classList.remove('flash-up', 'flash-down');
      void priceEl.offsetWidth; // Force reflow to restart animation
      priceEl.classList.add(newPrice > prevPrice ? 'flash-up' : 'flash-down');
    }

    // Update change percent with pulse
    const newChangeTxt = fmtPct(idx.change_percent);
    if (changeEl.textContent !== newChangeTxt) {
      changeEl.textContent = newChangeTxt;
      changeEl.className = `mi-change ${changeClass(idx.change_percent)}`;
      changeEl.classList.add('pulse');
      setTimeout(() => changeEl.classList.remove('pulse'), 400);
    }

    _prevMarketPrices[idx.symbol] = newPrice;
  });
}


// ═══════════════════════════════════════════════════════════════════════════
//  CONSENSUS TOP 25
// ═══════════════════════════════════════════════════════════════════════════

async function loadConsensusPicks() {
  const el = document.getElementById("consensus-picks");
  if (!el) return;
  const data = await apiFetch("/api/top-picks");
  if (!data || !data.picks || !data.picks.length) {
    el.innerHTML = '<div class="loading-shimmer">No consensus data available yet. SEC EDGAR filings are loading...</div>';
    return;
  }

  const rows = data.picks.map(p => {
    const rankClass = p.rank <= 3 ? " top3" : "";
    const convClass = p.conviction.toLowerCase().replace(" ", "-");
    // QoQ institutional change (from 13F data) — the key metric
    const instChange = p.inst_change_pct;
    let instChangeHtml;
    if (instChange != null && instChange !== 0) {
      const capped = Math.abs(instChange) > 9999 ? "NEW" : fmtPct(instChange);
      const emoji = instChange > 100 ? ' 🚀' : (instChange > 30 ? ' 📈' : '');
      instChangeHtml = `<span class="pick-change ${changeClass(instChange)}">${capped}${emoji}</span>`;
    } else if (p.change_percent != null) {
      instChangeHtml = `<span class="pick-change ${changeClass(p.change_percent)}">${fmtPct(p.change_percent)}</span>`;
    } else {
      instChangeHtml = `<span class="pick-change">—</span>`;
    }
    const upsideHtml = p.upside_pct != null
      ? `<span class="pick-upside ${p.upside_pct >= 0 ? 'positive' : 'negative'}">${p.upside_pct >= 0 ? '▲' : '▼'} ${Math.abs(p.upside_pct).toFixed(1)}%</span>`
      : '<span class="pick-upside">—</span>';
    const holdersNames = (p.top_holders || []).slice(0, 3).map(h => h.institution).join(", ");

    // Daily change % — will be populated by live updater
    const dailyPct = p.daily_change_percent;
    let dailyHtml;
    if (dailyPct != null) {
      dailyHtml = `<span class="pick-daily-change ${changeClass(dailyPct)}">${fmtPct(dailyPct)}</span>`;
    } else {
      dailyHtml = `<span class="pick-daily-change" data-ticker="${p.ticker}">⏳</span>`;
    }

    return `
      <tr onclick="window.location='/stock/${p.ticker}'">
        <td><span class="pick-rank${rankClass}">${p.rank}</span></td>
        <td>
          <div class="pick-symbol">${p.ticker}</div>
          <div class="pick-name">${escHtml(p.name || p.issuer || '')}</div>
        </td>
        <td><span class="pick-price" data-ticker="${p.ticker}">${fmtPrice(p.price)}</span></td>
        <td>${dailyHtml}</td>
        <td>${instChangeHtml}</td>
        <td>
          <span class="pick-holders"><span class="holder-count">${p.num_holders}</span> firms</span>
          <div class="pick-holders-list">${escHtml(holdersNames)}</div>
        </td>
        <td><span class="conviction-badge ${convClass}">${p.conviction}</span></td>
        <td>${upsideHtml}</td>
        <td><span class="pick-value">${fmtMoney(p.total_value)}</span></td>
      </tr>`;
  }).join("");

  el.innerHTML = `
    <table class="picks-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Stock</th>
          <th>Price</th>
          <th>Daily %</th>
          <th>Inst. Change</th>
          <th>Holders</th>
          <th>Conviction</th>
          <th>Upside</th>
          <th>Inst. Value</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  // Kick off live daily % updater for consensus stocks
  _updateConsensusDailyChanges(data.picks.map(p => p.ticker));
}

// Live daily % change updater for consensus picks
let _consensusTickers = [];
let _consensusUpdateTimer = null;

async function _updateConsensusDailyChanges(tickers) {
  _consensusTickers = tickers || _consensusTickers;
  if (!_consensusTickers.length) return;

  try {
    const data = await apiFetch(`/api/batch-quotes?symbols=${_consensusTickers.join(',')}`);
    if (!data || !data.quotes) return;

    for (const q of data.quotes) {
      // Update daily % badge
      const badges = document.querySelectorAll(`.pick-daily-change[data-ticker="${q.symbol}"]`);
      badges.forEach(badge => {
        if (q.change_percent != null) {
          badge.textContent = fmtPct(q.change_percent);
          badge.className = `pick-daily-change ${changeClass(q.change_percent)}`;
          badge.dataset.ticker = q.symbol;
          badge.classList.add('pulse');
          setTimeout(() => badge.classList.remove('pulse'), 400);
        }
      });

      // Also update price in-place
      const priceEls = document.querySelectorAll(`.pick-price[data-ticker="${q.symbol}"]`);
      priceEls.forEach(el => {
        if (q.price != null) el.textContent = fmtPrice(q.price);
      });
    }
  } catch (e) {
    console.warn('Daily change update failed:', e);
  }
}


// ═══════════════════════════════════════════════════════════════════════════
//  INSTITUTION BROWSER
// ═══════════════════════════════════════════════════════════════════════════

async function loadInstitutions() {
  const grid = document.getElementById("institutions-grid");
  if (!grid) return;
  const data = await apiFetch("/api/institutions");
  if (!data || !data.institutions || !data.institutions.length) {
    grid.innerHTML = '<div class="loading-shimmer">No institutional data available.</div>';
    return;
  }

  document.getElementById("inst-count").textContent = `${data.count} firms tracked`;

  grid.innerHTML = data.institutions.map(inst => {
    const tags = (inst.top_holdings || []).map(h =>
      `<span class="inst-holding-tag">${h.ticker}</span>`
    ).join("");

    // QoQ % Change badge
    let changeBadge = '';
    if (inst.change_pct != null) {
      const cls = inst.change_pct >= 0 ? 'positive' : 'negative';
      const sign = inst.change_pct >= 0 ? '+' : '';
      const display = Math.abs(inst.change_pct) > 999 ? 'NEW' : `${sign}${inst.change_pct.toFixed(1)}%`;
      changeBadge = `<span class="inst-change ${cls}">${display}</span>`;
    }

    return `
      <div class="inst-card" onclick="openInstitution('${inst.cik}', '${escHtml(inst.name)}')">
        <div class="inst-name">${escHtml(inst.short_name || inst.name)}</div>
        <div class="inst-aum-row">
          <span class="inst-aum">${fmtMoney(inst.total_value)}</span>
          ${changeBadge}
        </div>
        <div class="inst-meta">
          <span>${inst.total_positions} positions</span>
          <span>Filed ${inst.filing_date || '—'}</span>
        </div>
        <div class="inst-top-holdings">${tags || '<span style="color:var(--text-muted);font-size:10px;">No data</span>'}</div>
      </div>`;
  }).join("");
}


// ═══════════════════════════════════════════════════════════════════════════
//  INSTITUTION DETAIL MODAL
// ═══════════════════════════════════════════════════════════════════════════

// State for current modal
let _modalData = null;   // full holdings array
let _modalSort = { col: 'value', dir: -1 };  // default: value desc
let _modalFilter = '';
let _modalShown = 0;     // rows rendered so far
const BATCH_SIZE = 100;  // rows per batch

function _getFilteredSorted() {
  if (!_modalData) return [];
  let list = _modalData;
  if (_modalFilter) {
    const q = _modalFilter.toLowerCase();
    list = list.filter(h =>
      (h.ticker || '').toLowerCase().includes(q) ||
      (h.issuer || '').toLowerCase().includes(q)
    );
  }
  const col = _modalSort.col;
  const dir = _modalSort.dir;
  list = [...list].sort((a, b) => {
    let va, vb;
    if (col === 'ticker') { va = (a.ticker || '').toLowerCase(); vb = (b.ticker || '').toLowerCase(); return va < vb ? -dir : va > vb ? dir : 0; }
    if (col === 'shares') { va = a.shares || 0; vb = b.shares || 0; }
    else if (col === 'value') { va = a.value || 0; vb = b.value || 0; }
    else if (col === 'change') { va = a.shares_change_pct ?? -Infinity; vb = b.shares_change_pct ?? -Infinity; }
    else { va = a.value || 0; vb = b.value || 0; }
    return (va - vb) * dir;
  });
  return list;
}

function _holdingRow(h, i) {
  let changeHtml;
  if (h.is_new) {
    changeHtml = '<span style="color:var(--cyan);font-weight:700;font-size:11px">NEW BUY</span>';
  } else if (h.shares_change_pct != null) {
    const pct = h.shares_change_pct;
    const cls = pct > 0 ? 'color:var(--green)' : (pct < 0 ? 'color:var(--red)' : 'color:var(--text-muted)');
    const sign = pct > 0 ? '+' : '';
    const val = Math.abs(pct) > 9999 ? '>9999%' : `${sign}${pct.toFixed(1)}%`;
    const weight = pct !== 0 ? '700' : '400';
    changeHtml = `<span style="${cls};font-family:var(--mono);font-weight:${weight};font-size:12px">${val}</span>`;
  } else {
    changeHtml = '<span style="color:var(--text-muted)">—</span>';
  }
  return `
    <tr onclick="window.location='/stock/${h.ticker || ''}'">
      <td style="color:var(--text-muted)">${i + 1}</td>
      <td><strong style="color:var(--accent)">${h.ticker || '—'}</strong></td>
      <td style="color:var(--text-dim);font-size:11px">${escHtml(h.issuer || '')}</td>
      <td style="font-family:var(--mono)">${fmtShares(h.shares)}</td>
      <td style="font-family:var(--mono)">${fmtMoney(h.value)}</td>
      <td>${changeHtml}</td>
    </tr>`;
}

function _renderModalRows(reset) {
  const list = _getFilteredSorted();
  const tbody = document.getElementById('modal-holdings-tbody');
  const counter = document.getElementById('modal-result-count');
  const loadMoreBtn = document.getElementById('modal-load-more');
  if (!tbody) return;

  if (reset) {
    _modalShown = 0;
    tbody.innerHTML = '';
  }
  const start = _modalShown;
  const end = Math.min(start + BATCH_SIZE, list.length);
  let html = '';
  for (let i = start; i < end; i++) {
    html += _holdingRow(list[i], i);
  }
  tbody.insertAdjacentHTML('beforeend', html);
  _modalShown = end;

  if (counter) {
    const total = _modalData ? _modalData.length : 0;
    if (_modalFilter) {
      counter.textContent = `Showing ${Math.min(_modalShown, list.length)} of ${list.length} matches (${total} total)`;
    } else {
      counter.textContent = `Showing ${Math.min(_modalShown, list.length)} of ${total} positions`;
    }
  }
  if (loadMoreBtn) {
    loadMoreBtn.style.display = _modalShown < list.length ? 'block' : 'none';
    loadMoreBtn.textContent = `Load more (${list.length - _modalShown} remaining)`;
  }
}

function _sortModal(col) {
  if (_modalSort.col === col) {
    _modalSort.dir *= -1;  // toggle direction
  } else {
    _modalSort.col = col;
    _modalSort.dir = col === 'ticker' ? 1 : -1;  // alpha asc, numbers desc
  }
  // Update sort indicators
  document.querySelectorAll('.modal-sort-header').forEach(el => {
    el.classList.remove('sort-active', 'sort-asc', 'sort-desc');
    if (el.dataset.col === col) {
      el.classList.add('sort-active', _modalSort.dir === 1 ? 'sort-asc' : 'sort-desc');
    }
  });
  _renderModalRows(true);
}

async function openInstitution(cik, name) {
  const modal = document.getElementById("inst-modal");
  const body = document.getElementById("inst-modal-body");
  modal.style.display = "flex";
  body.innerHTML = '<div class="loading-shimmer">Loading portfolio from SEC EDGAR...</div>';

  const data = await apiFetch(`/api/institution/${cik}?_t=${Date.now()}`);
  if (!data || !data.holdings) {
    body.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-muted)">Portfolio data unavailable for this institution.</div>';
    return;
  }

  _modalData = data.holdings;
  _modalSort = { col: 'value', dir: -1 };
  _modalFilter = '';
  _modalShown = 0;

  const qInfo = data.previous_quarter
    ? `${data.current_quarter} vs ${data.previous_quarter}`
    : data.current_quarter || '';

  body.innerHTML = `
    <div class="modal-header">
      <h3>${escHtml(data.name || name)}</h3>
      <div class="modal-sub">
        AUM: ${fmtMoney(data.total_value)} · ${data.total_positions} positions · Filed ${data.filing_date || '—'}${qInfo ? ` · ${qInfo}` : ''}
      </div>
    </div>
    <div class="modal-controls">
      <input type="text" id="modal-search" placeholder="🔍 Search by ticker or name..." autocomplete="off">
      <span id="modal-result-count" class="modal-count"></span>
    </div>
    <div class="modal-body-content">
      <table class="modal-holdings-table">
        <thead>
          <tr>
            <th>#</th>
            <th class="modal-sort-header" data-col="ticker" onclick="_sortModal('ticker')">Ticker ⇅</th>
            <th>Issuer</th>
            <th class="modal-sort-header" data-col="shares" onclick="_sortModal('shares')">Shares ⇅</th>
            <th class="modal-sort-header sort-active sort-desc" data-col="value" onclick="_sortModal('value')">Value ⇅</th>
            <th class="modal-sort-header" data-col="change" onclick="_sortModal('change')" title="Change in shares held vs previous quarter">Shares Chg ⇅</th>
          </tr>
        </thead>
        <tbody id="modal-holdings-tbody"></tbody>
      </table>
      <button id="modal-load-more" class="load-more-btn" onclick="_renderModalRows(false)">Load more</button>
    </div>`;

  _renderModalRows(true);

  // Wire up search
  const searchEl = document.getElementById('modal-search');
  let searchTimer = null;
  searchEl.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      _modalFilter = searchEl.value.trim();
      _renderModalRows(true);
    }, 200);
  });

  // Infinite scroll within modal
  const scrollContainer = body.querySelector('.modal-body-content');
  if (scrollContainer) {
    scrollContainer.addEventListener('scroll', () => {
      if (scrollContainer.scrollTop + scrollContainer.clientHeight >= scrollContainer.scrollHeight - 100) {
        const list = _getFilteredSorted();
        if (_modalShown < list.length) {
          _renderModalRows(false);
        }
      }
    });
  }
}

function closeModal() {
  document.getElementById("inst-modal").style.display = "none";
  _modalData = null;
  _modalFilter = '';
  _modalShown = 0;
}
document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });


// ═══════════════════════════════════════════════════════════════════════════
//  NEWS FEED
// ═══════════════════════════════════════════════════════════════════════════


// ═══════════════════════════════════════════════════════════════════════════
//  SEARCH
// ═══════════════════════════════════════════════════════════════════════════

let searchTimer = null;
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");

searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  const q = searchInput.value.trim();
  if (q.length < 1) { searchResults.style.display = "none"; return; }
  searchTimer = setTimeout(async () => {
    const data = await apiFetch(`/api/search?q=${encodeURIComponent(q)}`);
    if (!data || !data.results || !data.results.length) {
      searchResults.style.display = "none";
      return;
    }
    searchResults.style.display = "block";
    searchResults.innerHTML = data.results.slice(0, 8).map(r => `
      <div class="search-item" onclick="window.location='/stock/${r.symbol}'">
        <span><span class="si-sym">${r.symbol}</span><span class="si-name">${escHtml(r.name || '')}</span></span>
      </div>
    `).join("");
  }, 250);
});

searchInput.addEventListener("keydown", e => {
  if (e.key === "Enter") {
    const q = searchInput.value.trim().toUpperCase();
    if (q) window.location = `/stock/${q}`;
  }
});

document.addEventListener("click", e => {
  if (!e.target.closest(".search-box")) {
    searchResults.style.display = "none";
  }
});


// ═══════════════════════════════════════════════════════════════════════════
//  WHALE TRACKER (BIG TECH PORTFOLIOS)
// ═══════════════════════════════════════════════════════════════════════════

function openWhaleTracker() {
  document.getElementById("whale-modal").style.display = "flex";
  // Always load NVDA by default when opened if nothing is loaded yet
  const contentArea = document.getElementById("whale-content-area");
  if (contentArea.innerHTML.includes("Selecting Whale Data...")) {
    loadWhaleData('NVDA');
  }
}

function closeWhaleModal() {
  document.getElementById("whale-modal").style.display = "none";
}

async function loadWhaleData(ticker) {
  // Update active tab styling
  document.querySelectorAll('.whale-tab').forEach(tab => {
    if (tab.innerText.toUpperCase().includes(ticker) || (ticker === 'GATES' && tab.innerText.includes('Gates')) || (ticker === 'BRK-B' && tab.innerText.includes('Berkshire'))) {
      tab.classList.add('active');
      tab.style.background = 'rgba(0, 210, 255, 0.1)';
      tab.style.borderColor = 'rgba(0, 210, 255, 0.5)';
      tab.style.color = '#fff';
    } else {
      tab.classList.remove('active');
      tab.style.background = 'transparent';
      tab.style.borderColor = 'rgba(255, 255, 255, 0.1)';
      tab.style.color = '#a0a0b0';
    }
  });

  const contentArea = document.getElementById("whale-content-area");
  contentArea.innerHTML = `<div class="loading-shimmer" style="text-align: center; color: #a0a0b0; padding-top: 100px;">Fetching live portfolio data for ${ticker}...</div>`;

  const data = await apiFetch(`/api/whale-portfolio/${ticker}`);

  if (!data || data.error) {
    contentArea.innerHTML = `<div style="text-align: center; color: var(--red); padding-top: 100px;">Failed to load portfolio data.</div>`;
    return;
  }

  const rows = data.holdings.map((h, i) => {
    const profitCls = h.profit_loss >= 0 ? 'color:var(--green)' : 'color:var(--red)';
    const dayCls = h.day_change >= 0 ? 'color:var(--green)' : 'color:var(--red)';

    return `
      <tr onclick="window.location='/stock/${h.symbol}'" style="cursor: pointer; transition: background 0.2s; border-bottom: 1px solid rgba(255,255,255,0.05);" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
        <td style="padding: 15px 10px; color: var(--text-muted);">${i + 1}</td>
        <td style="padding: 15px 10px;"><strong style="color: var(--accent); font-size: 16px;">${h.symbol}</strong></td>
        <td style="padding: 15px 10px; font-family: var(--mono);">${fmtShares(h.shares)}</td>
        <td style="padding: 15px 10px;">
          <div style="font-family: var(--mono); color: #fff;">${fmtMoney(h.position_value)}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${fmtPct(h.weight_percent)} of Portfolio</div>
        </td>
      </tr>
    `;
  }).join("");

  contentArea.innerHTML = `
    <div style="margin-bottom: 20px;">
      <h3 style="margin: 0 0 5px 0; font-size: 20px; color: #fff;">${escHtml(data.name)} <span style="font-size: 14px; color: #a0a0b0; font-weight: 400;">(${data.ticker})</span></h3>
      <p style="margin: 0; color: #a0a0b0; font-size: 14px;">${escHtml(data.description)}</p>
      <div style="margin-top: 15px; font-size: 13px; color: #a0a0b0;">
        Manager: <span style="color: #fff;">${escHtml(data.manager)}</span> &nbsp;|&nbsp; 
        Est. Portfolio Value: <span style="color: #00d2ff; font-weight: 600; font-family: var(--mono);">${fmtMoney(data.total_value)}</span>
      </div>
    </div>
    
    <table style="width: 100%; border-collapse: collapse; text-align: left;">
      <thead>
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: var(--text-muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">
          <th style="padding: 10px; font-weight: 600;">#</th>
          <th style="padding: 10px; font-weight: 600;">Asset</th>
          <th style="padding: 10px; font-weight: 600;">Shares</th>
          <th style="padding: 10px; font-weight: 600;">Position Size</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `;
}


// ═══════════════════════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════════════════════

(async function init() {
  // Load everything in parallel — fast sections first
  loadMarketBar();
  loadBreakingNews();

  // These hit SEC EDGAR and may be slower
  loadConsensusPicks();
  loadInstitutions();

  // Alpha Screener
  loadAlphaScreener();

  // ── Live refresh intervals ──
  // Market bar: refresh every 3 seconds (DB updates every 15s anyway)
  setInterval(loadMarketBar, 3000);
  // Breaking news: refresh every 2 min
  setInterval(loadBreakingNews, 120000);
  // Consensus daily %: refresh every 10 seconds
  setInterval(() => _updateConsensusDailyChanges(), 10000);

  checkAuth();
})();


// ═══════════════════════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════════════════════

async function checkAuth() {
  const container = document.getElementById("auth-controls");
  if (!container) return;

  try {
    const data = await apiFetch("/api/auth/status");
    if (data && data.logged_in) {
      // Disabled onboarding redirect per user request
      /* if (data.needs_onboarding && window.location.pathname === '/') {
        window.location.href = '/onboarding';
        return;
      } */
      container.innerHTML = `
          <span class="auth-user">Hi, ${escHtml(data.user.name)}</span>
          <button class="auth-btn" onclick="logout()">Logout</button>
        `;
      if (data.preferences && window.location.pathname === '/') {
        personalizeDashboard(data.user.name, data.preferences);
      }
    } else {
      container.innerHTML = `
            <a href="/auth" class="auth-btn login">Login / Sign Up</a>
        `;
    }
  } catch (e) {
    console.error("Auth status check failed", e);
  }
}

function personalizeDashboard(name, prefs) {
  const mainCols = document.querySelector('.col-main');
  if (!mainCols) return;

  // Change greeting
  const header = document.querySelector('.header-left .logo-sub');
  if (header) {
    header.innerHTML = `<span style="color:var(--accent)">Welcome back, ${escHtml(name)}!</span> · Tracking ${prefs.sectors ? prefs.sectors.join(', ') : 'markets'}`;
  }

  // Add Personalized Picks card based on sectors
  let sectorText = (prefs.sectors || []).length > 0 ? encodeURIComponent(prefs.sectors[0]) : 'Technology';

  const pCard = document.createElement('div');
  pCard.className = 'card card-personal';
  pCard.innerHTML = `
        <div class="card-header">
            <h2>🎯 Personalized For You</h2>
            <span class="card-badge">Based on your interest in ${escHtml(prefs.sectors ? prefs.sectors[0] : 'markets')} & ${escHtml(prefs.goals ? prefs.goals[0] : 'growth')}</span>
        </div>
        <div class="card-body">
            <div id="personalized-picks" class="inst-grid">
               <div class="loading-shimmer">Loading top picks for your profile...</div>
            </div>
        </div>
    `;
  mainCols.insertBefore(pCard, mainCols.firstChild);

  // Fetch sector picks for personalization
  apiFetch(`/api/sector-picks?sector=${sectorText}`).then(res => {
    const el = document.getElementById('personalized-picks');
    if (!res || !res.picks || !res.picks.length) {
      el.innerHTML = '<div style="padding:10px;text-align:center;color:var(--text-muted)">No personalized picks available at the moment.</div>';
      return;
    }

    el.innerHTML = res.picks.slice(0, 4).map(p => `
            <div class="inst-card" onclick="window.location='/stock/${p.symbol}'">
                <div class="inst-name">${p.symbol}</div>
                <div class="inst-aum-row">
                    <span class="inst-aum">${fmtPrice(p.price)}</span>
                    <span class="inst-change ${p.upside_pct >= 0 ? 'positive' : 'negative'}">${p.upside_pct > 0 ? '+' : ''}${fmtPct(p.upside_pct)} upside</span>
                </div>
                <div class="inst-top-holdings">${escHtml(p.name)}</div>
            </div>
        `).join('');
  });
}

async function logout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.reload();
  } catch (e) {
    console.error("Logout failed", e);
  }
}
