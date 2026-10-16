const chaptersData = [
    // ═══════════════════════════════════════════════════════════════
    //  PART I — FOUNDATIONS (Chapters 1–4)
    // ═══════════════════════════════════════════════════════════════
    {
        id: 1,
        title: "What is the Stock Market?",
        content: `
            <h2>What is a stock?</h2>
            <p>A stock (also called a "share" or "equity") is a fractional unit of ownership in a publicly traded corporation. When you purchase one share of Apple (AAPL), you legally own a proportional slice of Apple Inc. — its assets, its earnings, and its future growth.</p>

            <div class="real-example">
                <div class="real-example-title">🍎 Real Example: Apple Inc.</div>
                <p>Apple has approximately 15.4 billion shares outstanding. If you buy 100 shares at $185 each ($18,500 total investment), you own:</p>
                <p><strong>100 / 15,400,000,000 = 0.00000065%</strong> of the entire company.</p>
                <p>That sounds microscopic — but that 0.00000065% entitles you to vote on corporate matters, receive dividends, and participate in every dollar of price appreciation.</p>
            </div>

            <h2>The Initial Public Offering (IPO)</h2>
            <p>Before a company trades publicly, it is <strong>private</strong> — owned by founders, employees, and venture capital firms. An IPO is the process of listing shares on a public exchange for the first time.</p>
            <p><strong>Why go public?</strong></p>
            <ul>
                <li><strong>Raise capital</strong> — Instead of borrowing $10B from banks, sell 100M shares at $100 each</li>
                <li><strong>Liquidity</strong> — Early investors and employees can finally sell their shares</li>
                <li><strong>Prestige & credibility</strong> — Public companies attract talent and customers</li>
            </ul>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: Google's IPO (2004)</div>
                <p>Google went public on August 19, 2004 at $85 per share — a modest price for what would become one of the most dominant companies in history. The company raised $1.67 billion. Adjusted for stock splits, that $85 share is equivalent to roughly $1.06 today. If you had invested $10,000 at the IPO, your position would be worth approximately <strong>$400,000+</strong> today.</p>
                <p>Contrast this with <strong>Facebook's IPO (2012)</strong> — the stock debuted at $38, immediately crashed to $17.55 within months, and the media declared it a disaster. Investors who held through the pain saw it eventually reach $380+ (pre-Meta rebrand). <em>Lesson: IPO timing is treacherous, but long-term fundamentals win.</em></p>
            </div>

            <h2>The Two Major U.S. Exchanges</h2>
            <table class="lesson-table">
                <tr><th>Exchange</th><th>Founded</th><th>Style</th><th>Notable Listings</th></tr>
                <tr><td><strong>NYSE</strong></td><td>1792</td><td>Physical trading floor + electronic</td><td>Berkshire Hathaway, JPMorgan, Coca-Cola, Walmart</td></tr>
                <tr><td><strong>NASDAQ</strong></td><td>1971</td><td>Fully electronic, tech-heavy</td><td>Apple, Microsoft, Google, Amazon, Tesla, NVIDIA</td></tr>
            </table>
            <p>Together, these two exchanges list over 6,000 companies representing more than <strong>$50 trillion</strong> in total market capitalization — the largest pool of investable capital on Earth.</p>

            <h2>How Do You Make Money?</h2>
            <p>There are exactly two mechanisms by which stockholders generate returns:</p>
            <ol>
                <li><strong>Capital Appreciation</strong> — You buy at $100, the price rises to $160, you sell for a $60/share profit (60% return). This is driven by earnings growth, market sentiment, and macroeconomic conditions.</li>
                <li><strong>Dividends</strong> — The company distributes a portion of its profits directly to shareholders as cash. Coca-Cola, for example, pays approximately $1.94 per share annually. Own 1,000 shares and you receive $1,940/year deposited into your brokerage account — regardless of whether the stock price moves.</li>
            </ol>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 How Wall Street Actually Thinks About This</div>
                <p>Professional portfolio managers decompose expected returns into <strong>three components</strong>:</p>
                <ul>
                    <li><strong>Earnings growth</strong> — Is the company growing profits at 10%, 20%, 50% annually?</li>
                    <li><strong>Multiple expansion</strong> — Are investors willing to pay MORE per dollar of profit? (P/E ratio rising)</li>
                    <li><strong>Dividend yield</strong> — Cash returned to shareholders annually</li>
                </ul>
                <p>The total expected return = Earnings Growth + Multiple Change + Dividend Yield. This is the institutional framework that governs trillions of dollars in allocation decisions.</p>
            </div>

            <h2>Market Hours & Key Time Zones</h2>
            <table class="lesson-table">
                <tr><th>Session</th><th>Hours (Eastern)</th><th>Notes</th></tr>
                <tr><td>Pre-Market</td><td>4:00 AM – 9:30 AM</td><td>Low volume, wide spreads, earnings reactions</td></tr>
                <tr><td><strong>Regular Trading</strong></td><td><strong>9:30 AM – 4:00 PM</strong></td><td>Full liquidity, institutional participation</td></tr>
                <tr><td>After-Hours</td><td>4:00 PM – 8:00 PM</td><td>Earnings releases, reduced liquidity</td></tr>
            </table>

            <div class="danger-box">
                <div class="danger-box-title">⚠️ Critical Warning</div>
                <p>Pre-market and after-hours trading carries significantly higher risk: wider bid-ask spreads, lower volume, and the potential for extreme price swings on thin liquidity. Most institutional traders avoid executing large orders outside regular hours unless reacting to material news.</p>
            </div>
        `,
        quiz: [
            { question: "What does buying a share of stock legally represent?", options: ["A loan you give to the company", "A fractional unit of ownership in the corporation", "A guaranteed annual return"], correct: 1 },
            { question: "What are the two ways stockholders generate returns?", options: ["Interest and fees", "Capital appreciation and dividends", "Revenue and operating income"], correct: 1 },
            { question: "What is an IPO?", options: ["A type of stock order", "The process of a private company listing shares on a public exchange for the first time", "A quarterly earnings report"], correct: 1 }
        ]
    },
    {
        id: 2,
        title: "How to Read a Stock Quote",
        content: `
            <p>Every stock quote is a compressed data packet encoding critical information about a company's current market state. Understanding each field transforms noise into actionable intelligence.</p>

            <pre>
AAPL — Apple Inc.
─────────────────────────────────────────
Price:        $185.92      ← Current market price per share
Change:       +$3.47       ← Dollar move from previous close
Change %:     +1.90%       ← Percentage move today
Open:         $182.45      ← Price at market open (9:30 AM ET)
High:         $186.80      ← Intraday peak
Low:          $181.90      ← Intraday trough
Volume:       58,200,000   ← Shares traded today
Avg Volume:   62,000,000   ← 30-day average daily volume
Market Cap:   $2.86T       ← Total company valuation
P/E Ratio:    30.6         ← Price-to-Earnings multiple
EPS (TTM):    $6.07        ← Trailing 12-month earnings/share
Fwd P/E:      28.1         ← Based on NEXT year's estimated EPS
Div Yield:    0.53%        ← Annual dividend as % of price
Beta:         1.24         ← Volatility relative to S&P 500
52W High:     $199.62      ← Annual peak
52W Low:      $164.08      ← Annual trough
            </pre>

            <!-- LIVE WIDGET GOES HERE -->

            <h2>Deep Dive: P/E Ratio — The Most Watched Metric</h2>
            <div class="formula-box">P/E Ratio = Share Price ÷ Earnings Per Share (EPS)</div>
            <p>The P/E ratio answers one question: <strong>"How many dollars are investors willing to pay for $1 of this company's annual profit?"</strong></p>
            <p>Example: AAPL at $185.92 with EPS of $6.07 → P/E = 30.6. Investors pay $30.60 for every $1 of Apple's earnings.</p>

            <table class="lesson-table">
                <tr><th>P/E Range</th><th>Interpretation</th><th>Typical Sectors</th></tr>
                <tr><td>&lt; 10</td><td>Deep value / distressed / cyclical trough</td><td>Banks, energy, autos during downturns</td></tr>
                <tr><td>10 – 20</td><td>Fair value for mature, stable businesses</td><td>Consumer staples, utilities, industrials</td></tr>
                <tr><td>20 – 35</td><td>Growth premium — investors expect above-average earnings growth</td><td>Large-cap tech, healthcare</td></tr>
                <tr><td>35 – 60+</td><td>High-growth expectations baked in — any miss will be punished</td><td>SaaS, AI, biotech, hypergrowth</td></tr>
                <tr><td>Negative / N/A</td><td>Company is unprofitable (losing money)</td><td>Pre-revenue startups, turnarounds</td></tr>
            </table>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 Trailing vs Forward P/E</div>
                <p><strong>Trailing P/E</strong> uses the last 12 months of actual earnings — it tells you what happened.</p>
                <p><strong>Forward P/E</strong> uses analyst estimates for the NEXT 12 months — it tells you what the market expects. Professional investors almost exclusively use Forward P/E because stocks are priced on future earnings, not past ones.</p>
                <p><em>When you see a stock with a high Trailing P/E but a much lower Forward P/E, it means analysts expect massive earnings growth ahead. This is precisely what happened with NVIDIA in 2023 — trailing P/E was 200+ but forward P/E was ~30 because AI revenue was exploding.</em></p>
            </div>

            <h2>Deep Dive: Beta — Volatility DNA</h2>
            <p>Beta quantifies how violently a stock swings relative to the overall market (S&P 500 = Beta 1.0).</p>
            <table class="lesson-table">
                <tr><th>Beta</th><th>Meaning</th><th>Examples</th></tr>
                <tr><td>0.3 – 0.7</td><td>Low volatility, defensive</td><td>Johnson & Johnson (0.5), Procter & Gamble (0.4)</td></tr>
                <tr><td>0.8 – 1.2</td><td>Moves roughly with the market</td><td>Apple (1.2), Microsoft (0.9)</td></tr>
                <tr><td>1.3 – 2.0</td><td>Amplified moves — higher risk, higher reward</td><td>Tesla (2.0), AMD (1.7)</td></tr>
                <tr><td>2.0+</td><td>Extremely volatile, speculative</td><td>Meme stocks, small-cap biotech</td></tr>
            </table>
            <blockquote>If the S&P 500 drops 10% and your stock has a Beta of 1.8, expect roughly an 18% decline. Conversely, in a 10% rally, expect an 18% gain. Beta is a double-edged sword.</blockquote>

            <h2>Deep Dive: Market Capitalization Tiers</h2>
            <table class="lesson-table">
                <tr><th>Tier</th><th>Market Cap</th><th>Characteristics</th><th>Examples</th></tr>
                <tr><td><strong>Mega Cap</strong></td><td>$200B+</td><td>Global dominance, deepest liquidity, lowest risk</td><td>Apple, Microsoft, Google, Amazon</td></tr>
                <tr><td><strong>Large Cap</strong></td><td>$10B–$200B</td><td>Industry leaders, institutional favorites</td><td>Nike, Starbucks, AMD, Goldman Sachs</td></tr>
                <tr><td><strong>Mid Cap</strong></td><td>$2B–$10B</td><td>Growth potential + established business</td><td>Crocs, Five Below, Zillow</td></tr>
                <tr><td><strong>Small Cap</strong></td><td>$300M–$2B</td><td>Higher growth potential, higher risk, lower liquidity</td><td>Regional banks, niche tech</td></tr>
                <tr><td><strong>Micro Cap</strong></td><td>&lt;$300M</td><td>Speculative, thin volume, potential manipulation</td><td>Penny stocks, pre-revenue biotech</td></tr>
            </table>
        `,
        quiz: [
            { question: "What does the P/E Ratio fundamentally tell you?", options: ["The company's total revenue", "How many dollars investors pay for $1 of the company's annual profit", "The dividend yield"], correct: 1 },
            { question: "Why do professional investors prefer Forward P/E over Trailing P/E?", options: ["Trailing P/E is illegal to use", "Stocks are priced on future earnings expectations, not past results", "Forward P/E is always lower"], correct: 1 },
            { question: "A stock with Beta 1.8 — if the market drops 10%, what approximate decline should you expect?", options: ["10%", "18%", "5%"], correct: 1 }
        ]
    },
    {
        id: 3,
        title: "Order Types & Execution",
        content: `
            <p>Understanding order types is the difference between executing a precise surgical trade and accidentally overpaying by 3%. Every professional trader masters these mechanics before deploying a single dollar.</p>

            <h2>Market Order</h2>
            <p><strong>Definition:</strong> Buy or sell immediately at the best available price right now.</p>
            <ul>
                <li><strong>Pros:</strong> Guaranteed execution, instant fill</li>
                <li><strong>Cons:</strong> No price guarantee — you might pay more than expected (slippage)</li>
                <li><strong>Use when:</strong> Speed matters more than price (breaking news, earnings reactions)</li>
            </ul>

            <h2>Limit Order</h2>
            <p><strong>Definition:</strong> Buy or sell ONLY at your specified price or better.</p>
            <ul>
                <li><strong>Buy Limit:</strong> "Buy AAPL only if it drops to $175 or lower"</li>
                <li><strong>Sell Limit:</strong> "Sell AAPL only if it rises to $200 or higher"</li>
                <li><strong>Pros:</strong> Price control, no slippage</li>
                <li><strong>Cons:</strong> May never fill if the price doesn't reach your level</li>
            </ul>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 How Wall Street Actually Executes</div>
                <p>Institutional traders almost <strong>never</strong> use market orders for large positions. A $50M market order would crash through the order book, moving the price against them. Instead, they use:</p>
                <ul>
                    <li><strong>VWAP orders</strong> — Execute gradually throughout the day, targeting the Volume-Weighted Average Price</li>
                    <li><strong>TWAP orders</strong> — Time-Weighted Average Price, spreading evenly across a time window</li>
                    <li><strong>Iceberg orders</strong> — Show only a small portion of the total order, hiding the true size</li>
                    <li><strong>Dark pool execution</strong> — Trade on private venues where the order is invisible to public markets</li>
                </ul>
            </div>

            <h2>Stop Order (Stop-Loss)</h2>
            <p><strong>Definition:</strong> Becomes a market order when the stock hits your trigger price.</p>
            <div class="real-example">
                <div class="real-example-title">🎯 Example</div>
                <p>You buy NVDA at $800. You set a stop-loss at $720 (10% below).</p>
                <p>If NVDA drops to $720, your stop triggers and sells at market — protecting you from a potential 30-40% crash. Your maximum loss is capped at ~$80/share.</p>
            </div>

            <h2>Stop-Limit Order</h2>
            <p>Like a stop order, but converts to a <em>limit</em> order instead of market. Gives you price control but risks not filling in a fast crash.</p>

            <h2>Trailing Stop</h2>
            <p><strong>Definition:</strong> A dynamic stop-loss that moves UP with the stock price but never moves DOWN.</p>
            <div class="real-example">
                <div class="real-example-title">🎯 Trailing Stop Example</div>
                <p>You own TSLA at $200. Set a 10% trailing stop.</p>
                <p>TSLA rises to $300 → your stop automatically adjusts to $270 (10% below the peak).</p>
                <p>TSLA then drops to $270 → you're sold at $270 for a $70/share profit.</p>
                <p><strong>You captured most of the upside while protecting against reversal.</strong></p>
            </div>

            <h2>The Bid-Ask Spread</h2>
            <p>Every stock has two prices at all times:</p>
            <table class="lesson-table">
                <tr><th>Component</th><th>Definition</th><th>Example (AAPL)</th></tr>
                <tr><td><strong>Bid</strong></td><td>Highest price a buyer is willing to pay RIGHT NOW</td><td>$185.90</td></tr>
                <tr><td><strong>Ask</strong></td><td>Lowest price a seller is willing to accept RIGHT NOW</td><td>$185.93</td></tr>
                <tr><td><strong>Spread</strong></td><td>The gap = your immediate cost of entry</td><td>$0.03 (0.016%)</td></tr>
            </table>
            <p>For mega-cap stocks like Apple, the spread is pennies. For micro-cap penny stocks, the spread can be 5-10% — meaning you lose 5% the instant you buy.</p>

            <div class="danger-box">
                <div class="danger-box-title">⚠️ Slippage Warning</div>
                <p>In volatile or low-liquidity conditions, market orders can experience <strong>slippage</strong> — you get filled at a much worse price than displayed. During the 2020 COVID crash, some stocks had spreads of $2-5 on normally tight names. Always use limit orders in volatile markets.</p>
            </div>
        `,
        quiz: [
            { question: "Why do institutional traders avoid market orders for large positions?", options: ["Market orders are illegal for institutions", "Large market orders would crash through the order book, moving the price against them", "Market orders take 3 days to settle"], correct: 1 },
            { question: "What does a trailing stop do?", options: ["It moves down when the stock drops", "It dynamically adjusts upward with the stock price but never moves down, locking in gains", "It converts to a limit order at expiration"], correct: 1 },
            { question: "What is 'slippage'?", options: ["When your broker charges a fee", "Getting filled at a worse price than expected due to market conditions", "When a stock is delisted"], correct: 1 }
        ]
    },
    {
        id: 4,
        title: "Market Structure & Participants",
        content: `
            <p>The stock market is not a single entity — it is a complex ecosystem of interconnected participants, each playing a distinct role. Understanding who moves markets and why is the foundation of institutional thinking.</p>

            <h2>The Key Market Participants</h2>
            <table class="lesson-table">
                <tr><th>Participant</th><th>Capital</th><th>Typical Horizon</th><th>Impact</th></tr>
                <tr><td><strong>Retail Investors</strong></td><td>$1K – $1M</td><td>Days to years</td><td>Individually negligible; collectively significant in momentum</td></tr>
                <tr><td><strong>Hedge Funds</strong></td><td>$100M – $50B+</td><td>Days to months</td><td>Aggressive, sophisticated, can move mid-cap stocks</td></tr>
                <tr><td><strong>Mutual Funds / ETFs</strong></td><td>$1B – $1T+</td><td>Months to years</td><td>Massive, passive flows that create structural demand</td></tr>
                <tr><td><strong>Pension Funds</strong></td><td>$50B – $500B+</td><td>Years to decades</td><td>Ultra long-term, slow-moving, prioritize stability</td></tr>
                <tr><td><strong>Market Makers</strong></td><td>Firm capital</td><td>Seconds to minutes</td><td>Provide liquidity, profit from bid-ask spreads</td></tr>
                <tr><td><strong>High-Frequency Traders</strong></td><td>Firm capital</td><td>Microseconds</td><td>~50% of daily volume, exploit tiny price inefficiencies</td></tr>
            </table>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 The Institutional Food Chain</div>
                <p>Here's the uncomfortable truth: <strong>retail investors are the last to know.</strong></p>
                <p>Information flows in a hierarchy: CEOs → Board → Analysts → Institutional Sales → Hedge Funds → Mutual Funds → Financial Media → Retail. By the time you read a stock tip on social media, institutions have already positioned themselves weeks or months earlier.</p>
                <p><em>This is precisely why tracking 13F filings (institutional holdings) is so powerful — you get to see where the smart money positioned itself.</em></p>
            </div>

            <h2>Market Makers — The Hidden Backbone</h2>
            <p>Market makers are firms (Citadel Securities, Virtu Financial, Jane Street) that continuously quote both buy AND sell prices for every stock. They:</p>
            <ul>
                <li>Guarantee that there is always someone to trade with (liquidity)</li>
                <li>Profit from the tiny bid-ask spread millions of times per day</li>
                <li>Bear the risk of holding inventory when markets turn volatile</li>
            </ul>

            <h2>The Clearing Process (T+1 Settlement)</h2>
            <p>When you click "Buy" on your phone, the actual transfer of shares and cash happens <strong>one business day later (T+1)</strong>. This is handled by the DTCC (Depository Trust & Clearing Corporation), which processes over $2.5 quadrillion in securities per year.</p>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: The Flash Crash of May 6, 2010</div>
                <p>On May 6, 2010, the Dow Jones plummeted <strong>998.5 points (9.2%) in just 36 minutes</strong> — then recovered almost entirely within 20 minutes. Some individual stocks crashed to literally $0.01 per share before bouncing back.</p>
                <p><strong>What happened:</strong> A single large institutional sell order ($4.1B in S&P 500 futures) triggered cascading algorithmic selling. High-frequency traders withdrew liquidity, market makers pulled their quotes, and a vacuum of buyers created a free-fall.</p>
                <p><strong>Lesson:</strong> Modern markets are fragile ecosystems. Circuit breakers were subsequently strengthened — today, trading halts automatically if the S&P 500 drops 7% (Level 1), 13% (Level 2), or 20% (Level 3) in a single session.</p>
            </div>

            <h2>Circuit Breakers — The Emergency Brakes</h2>
            <table class="lesson-table">
                <tr><th>Level</th><th>Trigger</th><th>Action</th></tr>
                <tr><td>Level 1</td><td>S&P 500 drops 7%</td><td>15-minute trading halt</td></tr>
                <tr><td>Level 2</td><td>S&P 500 drops 13%</td><td>15-minute trading halt</td></tr>
                <tr><td>Level 3</td><td>S&P 500 drops 20%</td><td>Trading halted for remainder of day</td></tr>
            </table>
            <p>These were triggered four times during the March 2020 COVID crash — an unprecedented cluster of halts that underscored the severity of the pandemic panic.</p>

            <h2>Payment for Order Flow (PFOF)</h2>
            <p>"If you're not paying for the product, you ARE the product." Commission-free brokers like Robinhood route your orders to market makers (primarily Citadel Securities), who pay for the privilege of executing your trades. The market maker profits from the spread, and you may receive slightly worse execution than direct exchange access.</p>
        `,
        quiz: [
            { question: "What percentage of daily trading volume do High-Frequency Traders account for?", options: ["About 5%", "About 50%", "About 95%"], correct: 1 },
            { question: "What triggers a Level 1 circuit breaker?", options: ["A single stock dropping 7%", "The S&P 500 dropping 7% in a session", "Trading volume exceeding 1 billion shares"], correct: 1 },
            { question: "Why is tracking institutional 13F filings valuable for retail investors?", options: ["To copy their exact trades in real-time", "To see where sophisticated investors positioned themselves with massive capital", "To find penny stocks they are pumping"], correct: 1 }
        ]
    },
    {
        id: 5,
        title: "Fundamental Analysis: Financial Statements",
        content: `
            <p>Fundamental analysis is the rigorous examination of a company's financial health, competitive position, and growth trajectory. It answers the ultimate question: <strong>"Is this business worth owning at this price?"</strong></p>

            <h2>The Three Core Financial Statements</h2>
            <p>Every publicly traded company files these with the SEC every quarter (10-Q) and annually (10-K):</p>
            <ol>
                <li><strong>Income Statement</strong> — How much money did the company make or lose?</li>
                <li><strong>Balance Sheet</strong> — What does the company own vs. what does it owe?</li>
                <li><strong>Cash Flow Statement</strong> — Where did real cash actually flow?</li>
            </ol>

            <h2>1. The Income Statement — Profitability Engine</h2>
            <pre>
APPLE INC. — FY2024 INCOME STATEMENT (Simplified)
══════════════════════════════════════════════════
Revenue (Net Sales):       $383,285,000,000
Cost of Sales (COGS):     -$214,137,000,000
                          ─────────────────
Gross Profit:              $169,148,000,000   (44.1% margin)
Operating Expenses:        -$56,165,000,000
                          ─────────────────
Operating Income:          $112,983,000,000   (29.5% margin)
Interest & Other:           -$382,000,000
Income Tax:                -$29,749,000,000
                          ─────────────────
Net Income:                $93,736,000,000    (24.5% margin)
Earnings Per Share (EPS):  $6.07
            </pre>

            <h3>Key Metrics to Extract</h3>
            <table class="lesson-table">
                <tr><th>Metric</th><th>Formula</th><th>What It Tells You</th><th>Apple FY2024</th></tr>
                <tr><td>Gross Margin</td><td>Gross Profit / Revenue</td><td>Core production efficiency</td><td>44.1%</td></tr>
                <tr><td>Operating Margin</td><td>Operating Income / Revenue</td><td>Business profitability after all ops costs</td><td>29.5%</td></tr>
                <tr><td>Net Margin</td><td>Net Income / Revenue</td><td>Bottom-line profit per dollar of sales</td><td>24.5%</td></tr>
                <tr><td>Revenue Growth</td><td>(Current - Prior) / Prior</td><td>Is the top line expanding?</td><td>+2.0% YoY</td></tr>
            </table>

            <h2>2. The Balance Sheet — Financial Health X-Ray</h2>
            <pre>
ASSETS (What they own)              LIABILITIES (What they owe)
═══════════════════════             ═══════════════════════════
Cash & Securities:  $65B            Current Debt:        $15B
Accounts Receivable: $29B          Long-Term Debt:      $98B
Inventory:          $6B             Accounts Payable:    $69B
Total Current:      $143B           Total Liabilities:   $290B
Property/Equipment: $44B
Other Assets:       $165B           EQUITY (Assets - Liabilities)
───────────────────                 ═══════════════════════════
Total Assets:       $352B           Total Equity:        $62B
            </pre>

            <div class="formula-box">Debt-to-Equity Ratio = Total Debt / Total Equity<br>Apple: $113B / $62B = 1.82 → Moderate leverage</div>

            <h2>3. Cash Flow Statement — The Truth Serum</h2>
            <p>Revenue can be manipulated through accounting tricks. Cash cannot. The cash flow statement reveals the <strong>actual cash</strong> entering and leaving the business.</p>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 Why Cash Flow > Profit</div>
                <p>A company can report "profit" on its income statement while actually <strong>burning cash</strong>. How? Revenue recognition tricks, capitalizing expenses, and creative accounting.</p>
                <p><strong>Free Cash Flow (FCF)</strong> is the ultimate truth metric:</p>
                <p><code>FCF = Operating Cash Flow - Capital Expenditures</code></p>
                <p>If FCF is strongly positive, the company generates real, spendable cash. If negative, the company is consuming more cash than it generates — and will eventually need to raise capital (diluting you) or take on debt.</p>
                <p><em>Warren Buffett famously said: "In the long run, earnings have to equal cash flow. If they don't, something is wrong."</em></p>
            </div>

            <h2>GAAP vs Non-GAAP Earnings</h2>
            <p><strong>GAAP</strong> (Generally Accepted Accounting Principles) = The official, audited numbers filed with the SEC.</p>
            <p><strong>Non-GAAP</strong> = "Adjusted" numbers where the company strips out charges they consider one-time or non-recurring.</p>

            <div class="danger-box">
                <div class="danger-box-title">⚠️ The Non-GAAP Trap</div>
                <p>Companies love to highlight Non-GAAP earnings because they look better. They exclude stock-based compensation (a real cost!), restructuring charges, and acquisition costs. Always ask: <strong>"What have they excluded, and why?"</strong> If a company excludes the same 'one-time' charge every year, it's not one-time — it's a recurring cost they're trying to hide.</p>
            </div>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: Enron (2001)</div>
                <p>Enron reported billions in revenue and profits while secretly using off-balance-sheet entities to hide $63 billion in debt. The stock went from $90 to $0 in months. 20,000 employees lost their jobs and life savings. The lesson: <strong>always verify the balance sheet and cash flow statement — profit alone tells you nothing.</strong></p>
            </div>
        `,
        quiz: [
            { question: "Why is Free Cash Flow (FCF) considered the 'truth metric'?", options: ["Because it's the largest number", "Because cash cannot be manipulated like accounting profits can", "Because it includes stock-based compensation"], correct: 1 },
            { question: "What does a Debt-to-Equity ratio of 3.5 indicate?", options: ["Very low debt, very safe", "The company has $3.50 of debt for every $1 of equity — highly leveraged", "The stock will triple in value"], correct: 1 },
            { question: "What is the danger of relying solely on Non-GAAP earnings?", options: ["They are illegal", "Companies can exclude real recurring costs to make earnings look artificially better", "Non-GAAP numbers are always lower than GAAP"], correct: 1 }
        ]
    },
    // ═══════════════════════════════════════════════════════════════
    //  PART II — ANALYSIS (Chapters 5–9) [continued]
    // ═══════════════════════════════════════════════════════════════
    {
        id: 6,
        title: "Valuation Methods",
        content: `
            <p>Valuation is both art and science. It answers the most critical question in investing: <strong>"What is this company actually worth, independent of its current stock price?"</strong></p>

            <h2>Method 1: Comparable Company Analysis ("Comps")</h2>
            <p>Compare a company's valuation multiples against its closest industry peers. This is the most widely used method on Wall Street because it's fast and market-based.</p>
            <table class="lesson-table">
                <tr><th>Company</th><th>Market Cap</th><th>Revenue</th><th>P/E</th><th>EV/EBITDA</th><th>P/S</th></tr>
                <tr><td>CrowdStrike</td><td>$75B</td><td>$3.4B</td><td>85x</td><td>60x</td><td>22x</td></tr>
                <tr><td>Palo Alto</td><td>$115B</td><td>$7.0B</td><td>50x</td><td>40x</td><td>16x</td></tr>
                <tr><td>Fortinet</td><td>$60B</td><td>$5.6B</td><td>40x</td><td>30x</td><td>11x</td></tr>
                <tr><td><strong>Sector Median</strong></td><td>—</td><td>—</td><td><strong>50x</strong></td><td><strong>40x</strong></td><td><strong>16x</strong></td></tr>
            </table>
            <p>If CrowdStrike trades at 85x P/E vs a sector median of 50x, it's at a 70% premium. Is its growth rate 70% faster? If yes, the premium is justified. If not, it may be overvalued.</p>

            <h2>Method 2: Discounted Cash Flow (DCF)</h2>
            <p>The DCF is the gold standard of intrinsic valuation. It projects a company's future free cash flows and discounts them back to today's value using a discount rate (WACC).</p>
            <div class="formula-box">
Intrinsic Value = Σ (FCF_t / (1 + WACC)^t) + Terminal Value / (1 + WACC)^n
            </div>
            <p><strong>Step-by-step process:</strong></p>
            <ol>
                <li>Project Free Cash Flow for 5-10 years into the future</li>
                <li>Estimate a Terminal Value (the company's value beyond the projection period)</li>
                <li>Determine the WACC (Weighted Average Cost of Capital) — typically 8-12%</li>
                <li>Discount all future cash flows to present value</li>
                <li>Sum them up = Intrinsic enterprise value</li>
                <li>Subtract debt, add cash = Equity value. Divide by shares outstanding = Fair value per share</li>
            </ol>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 The DCF in Practice</div>
                <p>Every investment bank analyst builds DCF models in Excel. The dirty secret: <strong>the output is only as good as the assumptions.</strong> Change the growth rate by 2% or the WACC by 1%, and the fair value swings 30-50%. This is why professional investors use DCF as ONE input alongside comps, not as gospel truth.</p>
            </div>

            <h2>Key Valuation Multiples</h2>
            <table class="lesson-table">
                <tr><th>Multiple</th><th>Formula</th><th>Best For</th><th>Watch Out</th></tr>
                <tr><td><strong>P/E</strong></td><td>Price / EPS</td><td>Profitable companies</td><td>Useless for unprofitable firms</td></tr>
                <tr><td><strong>EV/EBITDA</strong></td><td>Enterprise Value / EBITDA</td><td>Comparing across capital structures</td><td>Ignores capex differences</td></tr>
                <tr><td><strong>P/S</strong></td><td>Price / Revenue</td><td>High-growth, pre-profit companies</td><td>Revenue ≠ profitability</td></tr>
                <tr><td><strong>PEG</strong></td><td>P/E / Growth Rate</td><td>Growth-adjusted value</td><td>PEG < 1 = undervalued relative to growth</td></tr>
                <tr><td><strong>P/FCF</strong></td><td>Price / Free Cash Flow</td><td>Cash-generating businesses</td><td>Most honest multiple</td></tr>
                <tr><td><strong>P/B</strong></td><td>Price / Book Value</td><td>Asset-heavy (banks, REITs)</td><td>Irrelevant for tech/IP companies</td></tr>
            </table>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: NVIDIA's Valuation Paradox (2023-2024)</div>
                <p>In early 2023, NVIDIA traded at a trailing P/E of <strong>200+</strong> — seemingly absurd. Many analysts called it overvalued. But the forward P/E based on AI-driven revenue was only ~30x. Revenue then exploded from $27B to $61B in one year. The stock went from $150 to $900+.</p>
                <p><strong>Lesson:</strong> Static backward-looking valuation metrics can be deeply misleading for companies at an inflection point. Always look at the forward growth trajectory.</p>
            </div>
        `,
        quiz: [
            { question: "What is the primary weakness of a DCF model?", options: ["It's too simple", "The output is highly sensitive to input assumptions like growth rate and WACC", "It only works for bank stocks"], correct: 1 },
            { question: "If a stock has a PEG ratio below 1.0, what does that suggest?", options: ["It is overvalued", "It may be undervalued relative to its earnings growth rate", "The company is losing money"], correct: 1 },
            { question: "Why is EV/EBITDA preferred over P/E for comparing companies?", options: ["It's easier to calculate", "It normalizes for different capital structures (debt vs equity)", "It always gives a lower number"], correct: 1 }
        ]
    },
    {
        id: 7,
        title: "Understanding Charts & Candlesticks",
        content: `
            <h2>Candlestick Anatomy</h2>
            <p>Each candlestick encodes four prices for a single time period (1 minute, 1 hour, 1 day, 1 week):</p>
            <pre>
     ╷         ← Upper Wick (High)
    ┌┤
    │█│        ← Body: filled space between Open and Close
    └┤
     ╵         ← Lower Wick (Low)

🟢 Green/Hollow: Close > Open (price went UP)
🔴 Red/Filled:   Close < Open (price went DOWN)
            </pre>

            <h2>Essential Candlestick Patterns</h2>
            <table class="lesson-table">
                <tr><th>Pattern</th><th>Type</th><th>Signal</th><th>Reliability</th></tr>
                <tr><td><strong>Hammer</strong></td><td>Bullish reversal</td><td>Small body, long lower wick at bottom of downtrend</td><td>High when confirmed by next candle</td></tr>
                <tr><td><strong>Shooting Star</strong></td><td>Bearish reversal</td><td>Small body, long upper wick at top of uptrend</td><td>High</td></tr>
                <tr><td><strong>Doji</strong></td><td>Indecision</td><td>Open ≈ Close, market can't decide direction</td><td>Medium — needs context</td></tr>
                <tr><td><strong>Engulfing (Bullish)</strong></td><td>Bullish reversal</td><td>Green candle body completely engulfs previous red body</td><td>Very high with volume</td></tr>
                <tr><td><strong>Engulfing (Bearish)</strong></td><td>Bearish reversal</td><td>Red candle body completely engulfs previous green body</td><td>Very high with volume</td></tr>
                <tr><td><strong>Morning Star</strong></td><td>Bullish reversal</td><td>3-candle pattern: big red → small body → big green</td><td>Very high</td></tr>
                <tr><td><strong>Evening Star</strong></td><td>Bearish reversal</td><td>3-candle pattern: big green → small body → big red</td><td>Very high</td></tr>
                <tr><td><strong>Three White Soldiers</strong></td><td>Bullish</td><td>Three consecutive large green candles with higher closes</td><td>High</td></tr>
            </table>

            <h2>Support & Resistance — The Battle Lines</h2>
            <p><strong>Support</strong> = A price floor where buying pressure consistently overcomes selling pressure. The stock "bounces" off this level.</p>
            <p><strong>Resistance</strong> = A price ceiling where selling pressure overcomes buying. The stock gets "rejected" repeatedly.</p>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 The Role Reversal Principle</div>
                <p>When a resistance level is finally broken with strong volume, it becomes the new support — and vice versa. This is one of the most reliable principles in technical analysis.</p>
                <p><em>Example: AAPL struggled at $200 resistance three times over 6 months. When it finally broke $200 on heavy volume, $200 became strong support. The stock then rallied to $230+.</em></p>
            </div>

            <h2>Volume — The Confirming Indicator</h2>
            <table class="lesson-table">
                <tr><th>Scenario</th><th>What It Means</th><th>Confidence</th></tr>
                <tr><td>Price UP + Volume UP</td><td>Strong institutional buying. Genuine move.</td><td>🟢 High confidence</td></tr>
                <tr><td>Price UP + Volume DOWN</td><td>Weak, unconvincing rally. Likely to reverse.</td><td>🟡 Low confidence</td></tr>
                <tr><td>Price DOWN + Volume UP</td><td>Strong institutional selling. Genuine decline.</td><td>🔴 High confidence</td></tr>
                <tr><td>Price DOWN + Volume DOWN</td><td>Weak selling, temporary pullback.</td><td>🟡 Low confidence</td></tr>
            </table>
            <blockquote><strong>The Cardinal Rule:</strong> Never trust a price move that isn't confirmed by volume. A breakout on low volume is a trap.</blockquote>

            <!-- LIVE WIDGET GOES HERE -->
        `,
        quiz: [
            { question: "What does a 'Hammer' candlestick pattern indicate?", options: ["Continuation of a downtrend", "A potential bullish reversal at the bottom of a downtrend", "The stock will be delisted"], correct: 1 },
            { question: "When resistance is broken with strong volume, what typically happens?", options: ["It disappears permanently", "It becomes the new support level (role reversal)", "The stock crashes"], correct: 1 },
            { question: "A stock breaks to new highs on very LOW volume. Should you trust it?", options: ["Yes, breakouts always continue", "No — low volume breakouts lack institutional conviction and often reverse", "Volume is irrelevant"], correct: 1 }
        ]
    },
    {
        id: 8,
        title: "Technical Indicators",
        content: `
            <p>Technical indicators are mathematical calculations applied to price and volume data. They help identify momentum, trend direction, overbought/oversold conditions, and potential reversal points.</p>

            <h2>RSI — Relative Strength Index</h2>
            <p>RSI measures momentum on a 0-100 scale by comparing the magnitude of recent gains to recent losses.</p>
            <div class="formula-box">RSI = 100 - (100 / (1 + RS)), where RS = Average Gain / Average Loss over 14 periods</div>
            <table class="lesson-table">
                <tr><th>RSI Value</th><th>Condition</th><th>Typical Action</th></tr>
                <tr><td>&gt; 70</td><td>Overbought — stock may be overextended</td><td>Consider taking partial profits or waiting before buying</td></tr>
                <tr><td>40 – 60</td><td>Neutral — no extreme momentum</td><td>Look at other indicators for direction</td></tr>
                <tr><td>&lt; 30</td><td>Oversold — stock may be due for a bounce</td><td>Research for potential entry if fundamentals are strong</td></tr>
            </table>

            <h2>MACD — Moving Average Convergence Divergence</h2>
            <p>MACD reveals momentum shifts by showing the relationship between two moving averages.</p>
            <ul>
                <li><strong>MACD Line</strong> = 12-period EMA minus 26-period EMA</li>
                <li><strong>Signal Line</strong> = 9-period EMA of the MACD Line</li>
                <li><strong>Histogram</strong> = MACD Line minus Signal Line (visual momentum)</li>
            </ul>
            <p><strong>Signals:</strong></p>
            <ul>
                <li>MACD crosses ABOVE Signal Line → <strong>Bullish</strong> (momentum turning positive)</li>
                <li>MACD crosses BELOW Signal Line → <strong>Bearish</strong> (momentum turning negative)</li>
                <li>MACD Divergence from price → <strong>Strongest signal</strong> (price makes new high but MACD doesn't = weakening momentum)</li>
            </ul>

            <h2>Bollinger Bands</h2>
            <p>A volatility envelope around a 20-period moving average, set at ±2 standard deviations.</p>
            <ul>
                <li>Price touches <strong>upper band</strong> → potentially overbought</li>
                <li>Price touches <strong>lower band</strong> → potentially oversold</li>
                <li><strong>Band Squeeze</strong> → bands contract tightly = extremely low volatility → a massive breakout is imminent</li>
            </ul>

            <h2>Moving Averages</h2>
            <table class="lesson-table">
                <tr><th>MA Period</th><th>Use Case</th><th>Significance</th></tr>
                <tr><td><strong>10-day</strong></td><td>Very short-term trend</td><td>Swing traders watch this closely</td></tr>
                <tr><td><strong>20-day</strong></td><td>Short-term trend</td><td>Bollinger Bands center line</td></tr>
                <tr><td><strong>50-day</strong></td><td>Medium-term trend</td><td>Key institutional level — funds buy/sell here</td></tr>
                <tr><td><strong>200-day</strong></td><td>Long-term trend</td><td>THE most important line. Above = bullish. Below = bearish.</td></tr>
            </table>
            <p><strong>Golden Cross:</strong> 50-day MA crosses ABOVE 200-day MA = major long-term bullish signal</p>
            <p><strong>Death Cross:</strong> 50-day MA crosses BELOW 200-day MA = major long-term bearish signal</p>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 How Institutions Use Indicators</div>
                <p>Professional traders never use a single indicator in isolation. The institutional approach is <strong>confluence</strong> — waiting for multiple independent signals to align. For example:</p>
                <ul>
                    <li>RSI drops below 30 (oversold) ✓</li>
                    <li>Price touches Bollinger lower band ✓</li>
                    <li>MACD histogram shows slowing downward momentum ✓</li>
                    <li>Price is at a known support level ✓</li>
                </ul>
                <p>Four signals aligning = high-probability long entry. One signal alone = noise.</p>
            </div>
        `,
        quiz: [
            { question: "An RSI reading of 25 on a fundamentally strong stock suggests what?", options: ["The stock is overbought and should be sold", "The stock is oversold and may be a buying opportunity if fundamentals support it", "The stock's volume is too low to trade"], correct: 1 },
            { question: "What does a 'Bollinger Band Squeeze' indicate?", options: ["The stock is about to be delisted", "Extremely low volatility, often preceding a major price breakout", "The company announced a stock split"], correct: 1 },
            { question: "What is the institutional approach to using technical indicators?", options: ["Use only one indicator at a time", "Wait for confluence — multiple independent signals aligning", "Ignore indicators entirely and trade on news"], correct: 1 }
        ]
    },
    {
        id: 9,
        title: "Chart Patterns",
        content: `
            <p>Chart patterns are geometric formations created by price action that have statistically predictable outcomes. They are the visual language of market psychology — encoding the battle between buyers and sellers into recognizable shapes.</p>

            <h2>Bullish Continuation Patterns</h2>

            <h3>Cup and Handle</h3>
            <p>A rounded bottom (the "cup") followed by a small downward drift (the "handle"), then a breakout above the cup's rim on high volume.</p>
            <ul>
                <li><strong>Formation time:</strong> 1-6 months typically</li>
                <li><strong>Target:</strong> Depth of the cup added to the breakout point</li>
                <li><strong>Reliability:</strong> One of the highest-probability patterns when volume confirms</li>
            </ul>

            <h3>Bull Flag / Pennant</h3>
            <p>A sharp upward move (the "pole") is followed by a brief, downward-drifting consolidation (the "flag"). The breakout continues in the original upward direction.</p>

            <h3>Ascending Triangle</h3>
            <p>Flat resistance ceiling with rising support. Each pullback makes a higher low, showing increasing buyer aggression. Eventually breaks upward.</p>

            <h2>Bearish Reversal Patterns</h2>

            <h3>Head and Shoulders</h3>
            <p>Three peaks: left shoulder, a higher head, right shoulder. The "neckline" connects the two troughs. When price breaks below the neckline, it's a major sell signal.</p>
            <div class="real-example">
                <div class="real-example-title">🎯 Head & Shoulders Target</div>
                <p>Measure the distance from the head to the neckline. Subtract that from the neckline breakdown point. That is your price target.</p>
                <p><em>Example: Head at $200, neckline at $180, depth = $20. If neckline breaks, target = $180 - $20 = $160.</em></p>
            </div>

            <h3>Double Top</h3>
            <p>Price reaches the same resistance level twice and fails both times, forming an "M" shape. A break below the middle trough confirms a bearish reversal.</p>

            <h3>Double Bottom</h3>
            <p>The bullish inverse — price hits the same support twice and bounces, forming a "W" shape. Break above the middle peak confirms reversal upward.</p>

            <h2>The Breakout — Most Profitable Pattern</h2>
            <p>A stock consolidates in a tight range for weeks or months, compressing like a spring. When it finally breaks above resistance on massive volume, it often produces explosive moves.</p>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 Breakout Confirmation Checklist</div>
                <ul>
                    <li>✅ Price closes above resistance (not just a wick)</li>
                    <li>✅ Volume is 2-3x the average daily volume</li>
                    <li>✅ The breakout holds for at least 2 consecutive closes</li>
                    <li>✅ RSI is NOT already overbought (above 80)</li>
                    <li>❌ A breakout on low volume = likely false breakout (bull trap)</li>
                </ul>
            </div>

            <div class="danger-box">
                <div class="danger-box-title">⚠️ Pattern Failure</div>
                <p>No pattern works 100% of the time. Professional traders always pair a chart pattern with a stop-loss. If you enter on a Cup & Handle breakout, place your stop below the handle's low. If it fails, you exit with a small loss. If it works, you ride a massive move. This asymmetric risk-reward is the foundation of professional trading.</p>
            </div>
        `,
        quiz: [
            { question: "How do you calculate the price target for a Head and Shoulders pattern?", options: ["Double the head price", "Measure head-to-neckline distance and subtract from neckline breakdown point", "Divide the head price by the shoulder price"], correct: 1 },
            { question: "What confirms a genuine breakout vs a false breakout?", options: ["The stock must gap up 10%", "Volume should be 2-3x average and price should hold above resistance for multiple closes", "The company must announce earnings"], correct: 1 },
            { question: "Why should you always pair a chart pattern trade with a stop-loss?", options: ["Because brokers require it", "No pattern works 100% — a stop-loss limits downside while preserving asymmetric upside potential", "Stop-losses increase your profits"], correct: 1 }
        ]
    },

    // ═══════════════════════════════════════════════════════════════
    //  PART III — INSTITUTIONAL INTELLIGENCE (Chapters 10–13)
    // ═══════════════════════════════════════════════════════════════
    {
        id: 10,
        title: "Institutional Money & 13F Filings",
        content: `
            <p>This chapter covers the single most powerful behavioral edge available to retail investors: <strong>legally tracking where the world's smartest money is being deployed.</strong></p>

            <h2>Who Are Institutional Investors?</h2>
            <table class="lesson-table">
                <tr><th>Type</th><th>Examples</th><th>AUM</th><th>Style</th></tr>
                <tr><td><strong>Hedge Funds</strong></td><td>Citadel, Bridgewater, Renaissance, Point72</td><td>$1B–$150B</td><td>Aggressive, concentrated, complex strategies</td></tr>
                <tr><td><strong>Asset Managers</strong></td><td>BlackRock, Vanguard, Fidelity, State Street</td><td>$1T–$10T</td><td>Passive + active, long-term, diversified</td></tr>
                <tr><td><strong>Pension Funds</strong></td><td>CalPERS, Norway Sovereign Wealth Fund</td><td>$200B–$1.7T</td><td>Ultra conservative, decades-long horizon</td></tr>
                <tr><td><strong>Investment Banks</strong></td><td>Goldman Sachs, JPMorgan, Morgan Stanley</td><td>Proprietary</td><td>Client-driven + prop trading</td></tr>
            </table>
            <p>Collectively, institutions control approximately <strong>80% of all stock market trading volume.</strong> When they move, the market moves.</p>

            <h2>What Is a 13F Filing?</h2>
            <p>By U.S. federal law (Securities Exchange Act Section 13(f)), any entity managing more than <strong>$100 million</strong> in qualified securities must file a quarterly 13F report with the SEC. This report mandates complete transparency of their U.S. equity holdings — every single stock, the number of shares, and the market value.</p>

            <h2>The 13F Timeline</h2>
            <table class="lesson-table">
                <tr><th>Quarter End</th><th>Filing Deadline</th><th>Public Release</th></tr>
                <tr><td>March 31 (Q1)</td><td>May 15</td><td>~Mid-May</td></tr>
                <tr><td>June 30 (Q2)</td><td>August 14</td><td>~Mid-August</td></tr>
                <tr><td>September 30 (Q3)</td><td>November 14</td><td>~Mid-November</td></tr>
                <tr><td>December 31 (Q4)</td><td>February 14</td><td>~Mid-February</td></tr>
            </table>

            <!-- LIVE 13F WIDGET -->

            <h2>The "Consensus" Signal</h2>
            <p>When multiple independent elite institutions all increase their position in the same stock during the same quarter — without coordinating — that is called <strong>consensus accumulation</strong>. It is one of the most powerful signals in finance.</p>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 The Divergence Signal (Extremely Powerful)</div>
                <p>Watch for this pattern: institutional buying is INCREASING quarter-over-quarter, but the stock price is currently FALLING or flat.</p>
                <p>This means: professional money is quietly accumulating shares at a discount while emotional retail investors panic-sell. Institutions have 50-person research teams, $100M data budgets, and direct access to management. When they buy into weakness, they've done the math.</p>
                <p><em>This divergence pattern frequently precedes 30-100%+ price recoveries within 6-12 months.</em></p>
            </div>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: Berkshire Hathaway's Apple Position</div>
                <p>In 2016, Warren Buffett began buying Apple stock when the market was skeptical about its growth. 13F filings showed Berkshire steadily accumulating shares quarter after quarter. By 2018, Apple was Berkshire's largest holding at ~$40B. Today, that position is worth over <strong>$170 billion</strong> — the single most profitable stock investment in history.</p>
                <p>Investors who tracked Berkshire's 13F filings and followed the accumulation pattern could have entered in the $100-140/share range. Apple now trades at $185+.</p>
            </div>

            <h2>Limitations of 13F Data</h2>
            <ul>
                <li><strong>45-day lag</strong> — Data is always 1.5 months old by the time it's public</li>
                <li><strong>Long-only</strong> — 13F shows only long positions, not short positions or options</li>
                <li><strong>Snapshot</strong> — Shows end-of-quarter holdings, not intra-quarter trading activity</li>
            </ul>
            <p>Despite these limitations, 13F data remains the most transparent window into institutional behavior available to individual investors.</p>
        `,
        quiz: [
            { question: "What triggers the legal requirement to file a 13F with the SEC?", options: ["Being a registered broker", "Managing more than $100 million in qualified securities", "Trading more than 1 million shares per day"], correct: 1 },
            { question: "What does a 'divergence signal' mean in the context of 13F data?", options: ["Institutions are selling while the stock rises", "Institutional buying increases while the stock price falls — a potential opportunity", "The SEC is investigating the company"], correct: 1 },
            { question: "What is the main limitation of 13F filings?", options: ["They are only filed annually", "They have a ~45-day lag and only show end-of-quarter long positions", "They only cover options, not stocks"], correct: 1 }
        ]
    },
    {
        id: 11,
        title: "Insider Trading & Form 4",
        content: `
            <p>Corporate insiders — CEOs, CFOs, directors, and major shareholders — possess the most intimate knowledge about a company's future. U.S. securities law requires them to disclose their personal stock transactions via <strong>SEC Form 4</strong>, filed within two business days of the trade.</p>

            <h2>Legal vs Illegal Insider Trading</h2>
            <table class="lesson-table">
                <tr><th>Type</th><th>Description</th><th>Status</th></tr>
                <tr><td><strong>Legal</strong></td><td>CEO buys shares on the open market, files Form 4 within 48 hours</td><td>✅ Fully legal and public</td></tr>
                <tr><td><strong>Illegal</strong></td><td>Trading on material non-public information (MNPI) before it's announced</td><td>❌ Federal crime — prison + fines</td></tr>
            </table>

            <h2>Reading Form 4 — What Matters</h2>
            <table class="lesson-table">
                <tr><th>Transaction</th><th>Signal Strength</th><th>Why</th></tr>
                <tr><td><strong>Open Market Purchase</strong></td><td>🟢 Extremely bullish</td><td>Insider is spending their own cash — they believe the stock is undervalued</td></tr>
                <tr><td>Option Exercise + Hold</td><td>🟢 Mildly bullish</td><td>They exercised options but kept the shares — confident in upside</td></tr>
                <tr><td>Option Exercise + Sell</td><td>⚪ Neutral</td><td>Often automated for taxes — doesn't signal conviction</td></tr>
                <tr><td>Open Market Sale</td><td>🟡 Context dependent</td><td>Could be taxes, diversification, home purchase — analyze size and pattern</td></tr>
                <tr><td><strong>Cluster Selling</strong></td><td>🔴 Bearish signal</td><td>Multiple insiders ALL selling aggressively = they know something is coming</td></tr>
            </table>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 The "Cluster Buy" — Strongest Signal in Finance</div>
                <p>When 3+ insiders independently purchase shares on the open market within a 30-day window, it is called a <strong>cluster buy</strong>. Academic research by professors at the University of Michigan and Wharton consistently shows that cluster buys outperform the market by 7-15% over the following 12 months.</p>
                <p><em>Why? Multiple insiders don't coordinate purchases. When they all independently conclude the stock is cheap at the same time, their collective conviction is extraordinarily powerful.</em></p>
            </div>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: JPMorgan CEO Jamie Dimon (2016)</div>
                <p>In February 2016, during a global banking crisis, JPMorgan stock dropped to $53. CEO Jamie Dimon personally purchased <strong>$26.6 million</strong> worth of JPM stock — one of the largest insider purchases in history. This sent a thunderous signal to the market. Within 12 months, JPM stock rose to $91, a <strong>72% gain</strong>.</p>
                <p>When the CEO of the largest U.S. bank bets $26 million of his own money, he's telling you something.</p>
            </div>
        `,
        quiz: [
            { question: "What type of insider transaction is considered the strongest bullish signal?", options: ["Automatic stock option exercise", "Open market purchase with personal cash", "Gifting shares to charity"], correct: 1 },
            { question: "What is a 'cluster buy' and why is it significant?", options: ["A single large purchase by the CEO", "Multiple insiders independently buying within a 30-day window — showing collective conviction", "Buying shares in multiple companies at once"], correct: 1 },
            { question: "Should you automatically be alarmed when an insider sells stock?", options: ["Yes, always sell immediately", "No — individual insider sells can be for taxes, diversification, or personal reasons; look for the pattern and context", "Only if it's the CEO"], correct: 1 }
        ]
    },
    {
        id: 12,
        title: "Earnings Season",
        content: `
            <p>Four times a year, every public company opens its financial books and reports quarterly results. These events — known as <strong>earnings releases</strong> — are the single largest catalysts for stock price movement.</p>

            <h2>The Earnings Calendar</h2>
            <table class="lesson-table">
                <tr><th>Period</th><th>Reports</th><th>Peak Weeks</th></tr>
                <tr><td>Q4 Results</td><td>January – February</td><td>Late January (big banks kick off)</td></tr>
                <tr><td>Q1 Results</td><td>April – May</td><td>Late April</td></tr>
                <tr><td>Q2 Results</td><td>July – August</td><td>Late July</td></tr>
                <tr><td>Q3 Results</td><td>October – November</td><td>Late October</td></tr>
            </table>

            <h2>The Anatomy of an Earnings Report</h2>
            <ul>
                <li><strong>Revenue</strong> — Did the company sell more than analysts expected?</li>
                <li><strong>EPS (Earnings Per Share)</strong> — Did they earn more per share than the consensus estimate?</li>
                <li><strong>Guidance</strong> — What does management FORECAST for next quarter/year? (Often more important than current results)</li>
                <li><strong>Key Metrics</strong> — Subscriber count, same-store sales, DAU/MAU, backlog, margins, etc.</li>
            </ul>

            <h2>Beat, Meet, or Miss</h2>
            <table class="lesson-table">
                <tr><th>Outcome</th><th>Typical Reaction</th><th>Nuance</th></tr>
                <tr><td>Beat + Raise Guidance</td><td>🟢 Strong rally (3-15%+)</td><td>The most bullish outcome — accelerating fundamentals</td></tr>
                <tr><td>Beat + Maintain Guidance</td><td>🟢 Moderate rally (1-5%)</td><td>Good, but market may want more</td></tr>
                <tr><td>Beat + Lower Guidance</td><td>🔴 Often sells off</td><td>Past was good, but future is darkening — market prices the future</td></tr>
                <tr><td>Miss + Lower Guidance</td><td>🔴 Severe sell-off (5-25%+)</td><td>Double negative — the worst combination</td></tr>
            </table>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 Whisper Numbers</div>
                <p>The "consensus estimate" you see on Yahoo Finance is the average of published analyst estimates. But institutions trade against <strong>whisper numbers</strong> — the unpublished, higher expectation that the buy-side truly expects. A company can "beat" the consensus by 5% and still drop 10% because it missed the whisper number.</p>
                <p><em>This is why you sometimes see a stock crash 15% after "beating estimates." The real bar was higher than published.</em></p>
            </div>

            <h2>Post-Earnings Drift</h2>
            <p>Academic research shows that stocks that beat earnings tend to <strong>continue drifting higher</strong> for 60-90 days after the report, and vice versa for misses. This phenomenon is called <strong>Post-Earnings Announcement Drift (PEAD)</strong> and is one of the most persistent anomalies in finance.</p>

            <div class="danger-box">
                <div class="danger-box-title">⚠️ The Earnings Gamble</div>
                <p>Holding through earnings is inherently risky. A stock can move 10-20% in either direction overnight — and you cannot exit during after-hours effectively. Professional advice: if you have a large concentrated position, consider trimming before earnings and re-entering after the volatility settles.</p>
            </div>
        `,
        quiz: [
            { question: "Why might a stock drop after 'beating' earnings estimates?", options: ["Because investors don't care about earnings", "Because the real institutional expectation (whisper number) was higher than the published consensus", "Because beating estimates is always bad"], correct: 1 },
            { question: "Which earnings outcome is the most bullish?", options: ["Beat EPS but lower guidance", "Beat EPS AND raise forward guidance", "Meet estimates exactly"], correct: 1 },
            { question: "What is Post-Earnings Announcement Drift?", options: ["Stocks that beat tend to continue drifting higher for 60-90 days, and vice versa", "The SEC delays in processing earnings filings", "A type of candlestick pattern"], correct: 0 }
        ]
    },
    {
        id: 13,
        title: "Sector Rotation & Business Cycles",
        content: `
            <p>The stock market does not move as a monolith. Different sectors lead and lag at different points in the economic cycle. Understanding this rotation is how institutional portfolio managers stay ahead.</p>

            <h2>The Four Phases of the Business Cycle</h2>
            <table class="lesson-table">
                <tr><th>Phase</th><th>Economy</th><th>Leading Sectors</th><th>Lagging Sectors</th></tr>
                <tr><td><strong>Early Expansion</strong></td><td>Recovery from recession, low rates, rising confidence</td><td>Technology, Consumer Discretionary, Industrials</td><td>Utilities, Consumer Staples</td></tr>
                <tr><td><strong>Mid Expansion</strong></td><td>Strong growth, rising corporate profits</td><td>Industrials, Materials, Financials</td><td>Healthcare, Utilities</td></tr>
                <tr><td><strong>Late Expansion</strong></td><td>Overheating, rising inflation, rate hikes</td><td>Energy, Materials, Healthcare</td><td>Technology, Consumer Discretionary</td></tr>
                <tr><td><strong>Recession</strong></td><td>Contracting GDP, rising unemployment</td><td>Utilities, Consumer Staples, Healthcare</td><td>Financials, Industrials, Tech</td></tr>
            </table>

            <h2>The Yield Curve — Economy's Crystal Ball</h2>
            <p>The yield curve plots interest rates across different maturities (2-year vs 10-year Treasury bonds).</p>
            <ul>
                <li><strong>Normal curve</strong> (upward sloping): Economy is healthy — long-term rates higher than short-term</li>
                <li><strong>Flat curve</strong>: Uncertainty — slowing growth expected</li>
                <li><strong>Inverted curve</strong>: Short-term rates higher than long-term — <strong>historically predicts recession within 12-18 months</strong></li>
            </ul>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: The 2020 Sector Rotation</div>
                <p>When COVID hit in March 2020, defensive sectors (utilities, staples) initially outperformed. But as the Fed slashed rates to zero and injected $5 trillion in stimulus, a massive rotation into technology and consumer discretionary stocks began. The NASDAQ surged 98% from the March low while utilities gained only 25%.</p>
                <p>Then in late 2021, as inflation surged and the Fed signaled rate hikes, the rotation reversed: energy (XLE) surged 65% in 2022 while tech (QQQ) crashed 33%. Investors who understood the cycle positioned accordingly.</p>
            </div>

            <h2>Leading Economic Indicators</h2>
            <table class="lesson-table">
                <tr><th>Indicator</th><th>What It Measures</th><th>Why It Matters</th></tr>
                <tr><td>ISM Manufacturing PMI</td><td>Factory activity (>50 = expansion)</td><td>Early signal of economic health</td></tr>
                <tr><td>Consumer Confidence</td><td>Household spending optimism</td><td>Consumer spending = 70% of GDP</td></tr>
                <tr><td>Initial Jobless Claims</td><td>Weekly new unemployment filings</td><td>Real-time labor market health</td></tr>
                <tr><td>Housing Starts</td><td>New home construction</td><td>Leading indicator of economic activity</td></tr>
                <tr><td>CPI / PCE</td><td>Inflation rate</td><td>Determines Fed policy (rates)</td></tr>
            </table>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 The Fed Is Everything</div>
                <p>"Don't fight the Fed" is the most important adage on Wall Street. When the Federal Reserve <strong>cuts rates</strong>, it injects liquidity into the system — historically bullish for stocks, especially growth/tech. When the Fed <strong>raises rates</strong>, it withdraws liquidity — bearish for high-valuation growth stocks.</p>
                <p>The interest rate cycle is the single most powerful macro force driving sector rotation and overall market direction.</p>
            </div>
        `,
        quiz: [
            { question: "During a recession, which sectors typically outperform?", options: ["Technology and Consumer Discretionary", "Utilities, Consumer Staples, and Healthcare (defensive sectors)", "Energy and Materials"], correct: 1 },
            { question: "What does a yield curve inversion historically predict?", options: ["A stock market boom", "A recession within approximately 12-18 months", "Rising commodity prices"], correct: 1 },
            { question: "Why is 'Don't fight the Fed' considered the most important market adage?", options: ["The Fed directly buys stocks", "Fed interest rate policy is the single most powerful force driving liquidity, valuations, and market direction", "The Fed publishes stock recommendations"], correct: 1 }
        ]
    },
    // ═══════════════════════════════════════════════════════════════
    //  PART IV — PORTFOLIO MANAGEMENT (Chapters 14–17)
    // ═══════════════════════════════════════════════════════════════
    {
        id: 14,
        title: "Portfolio Construction",
        content: `
            <p>Building a portfolio is not randomly picking stocks you like. It is an engineering discipline: constructing a basket of assets that maximizes expected return for a given level of risk.</p>

            <h2>Modern Portfolio Theory (MPT)</h2>
            <p>Pioneered by Harry Markowitz in 1952 (Nobel Prize in Economics), MPT proves mathematically that diversification reduces risk without proportionally reducing returns. The key insight: <strong>the risk of a portfolio depends not just on individual stock risk, but on how stocks move relative to each other (correlation).</strong></p>

            <div class="formula-box">Portfolio Risk ≠ Average of Individual Risks<br>Portfolio Risk = f(individual volatilities, correlations between all pairs)</div>

            <p>Two stocks that move in opposite directions (negative correlation) create a smoother portfolio than two that move together.</p>

            <h2>The Efficient Frontier</h2>
            <p>For any given level of risk, there exists an optimal combination of assets that maximizes return. Plot all possible portfolios on a risk-return graph, and the upper boundary is the <strong>Efficient Frontier</strong> — the set of optimal portfolios. Any portfolio below this line is suboptimal.</p>

            <h2>Position Sizing — The Kelly Criterion</h2>
            <div class="formula-box">Kelly % = W - [(1 - W) / R]<br>Where: W = Win probability, R = Win/Loss ratio</div>
            <p>Example: If you win 60% of trades and your average win is 1.5x your average loss:</p>
            <p><code>Kelly = 0.60 - (0.40 / 1.5) = 0.60 - 0.27 = 33%</code></p>
            <p>Kelly suggests risking 33% of your capital. In practice, professionals use <strong>Half-Kelly or Quarter-Kelly</strong> (8-16%) to reduce volatility.</p>

            <h2>Portfolio Allocation by Risk Profile</h2>
            <table class="lesson-table">
                <tr><th>Category</th><th>Conservative</th><th>Moderate</th><th>Aggressive</th></tr>
                <tr><td>Large-Cap Stocks</td><td>30%</td><td>40%</td><td>35%</td></tr>
                <tr><td>Growth / Mid-Cap</td><td>10%</td><td>20%</td><td>35%</td></tr>
                <tr><td>International</td><td>10%</td><td>10%</td><td>15%</td></tr>
                <tr><td>Bonds</td><td>35%</td><td>20%</td><td>5%</td></tr>
                <tr><td>Cash / Alternatives</td><td>15%</td><td>10%</td><td>10%</td></tr>
            </table>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 Core-Satellite Strategy</div>
                <p>Used by virtually every major asset manager:</p>
                <ul>
                    <li><strong>Core (60-70%)</strong>: Low-cost index ETFs (S&P 500, Total Market) — stable, diversified, low fees</li>
                    <li><strong>Satellite (30-40%)</strong>: Concentrated individual stock picks, sector bets, thematic plays — where you aim to outperform</li>
                </ul>
                <p>This structure ensures your overall portfolio tracks the market while your best ideas can generate alpha.</p>
            </div>

            <div style="text-align:center; padding: 2rem 0">
                <a href="/category/allocator" class="action-link-btn" target="_blank">Try the Smart $10,000 Portfolio Allocator →</a>
            </div>
        `,
        quiz: [
            { question: "What is the key insight of Modern Portfolio Theory?", options: ["Always buy the cheapest stocks", "Portfolio risk depends on correlations between assets, not just individual risks — diversification works", "Only invest in one stock at a time"], correct: 1 },
            { question: "What is the 'Core-Satellite' strategy?", options: ["A space investment fund", "A 60-70% core of index ETFs for stability plus 30-40% concentrated picks for alpha", "Buying only satellite companies"], correct: 1 },
            { question: "Why do professionals use Half-Kelly instead of Full Kelly sizing?", options: ["Full Kelly is illegal", "Full Kelly is mathematically optimal but too volatile in practice — halving reduces risk", "Half-Kelly generates more profit"], correct: 1 }
        ]
    },
    {
        id: 15,
        title: "Risk Management",
        content: `
            <h2>Rule #1 of Investing: Protect Capital</h2>
            <blockquote>"Rule No. 1: Never lose money. Rule No. 2: Never forget Rule No. 1." — Warren Buffett</blockquote>
            <p>You cannot recover from a blown-up account. Protecting capital is not optional — it is the foundation upon which all returns are built.</p>

            <h2>The Mathematics of Loss Recovery</h2>
            <table class="lesson-table">
                <tr><th>Loss</th><th>Gain Required to Break Even</th><th>Difficulty</th></tr>
                <tr><td>-10%</td><td>+11.1%</td><td>Easy — normal volatility</td></tr>
                <tr><td>-25%</td><td>+33.3%</td><td>Achievable in 1-2 years</td></tr>
                <tr><td>-50%</td><td>+100%</td><td>Very difficult — requires a double</td></tr>
                <tr><td>-75%</td><td>+300%</td><td>Nearly impossible for most investors</td></tr>
                <tr><td>-90%</td><td>+900%</td><td>Catastrophic — your portfolio is functionally destroyed</td></tr>
            </table>
            <p>This asymmetry is why risk management matters more than stock picking. A single 50% loss wipes out years of 10% annual gains.</p>

            <h2>The Three Types of Risk</h2>
            <ol>
                <li><strong>Market (Systematic) Risk</strong> — The entire market crashes. Cannot be diversified away. Defense: cash buffers, hedging, defensive positions</li>
                <li><strong>Company (Idiosyncratic) Risk</strong> — A single stock implodes. CAN be diversified away. Defense: hold 8-15 stocks across sectors, limit position sizes</li>
                <li><strong>Liquidity Risk</strong> — You can't sell when you need to. Defense: only trade liquid stocks with >500K daily volume</li>
            </ol>

            <h2>Stop-Loss Strategies</h2>
            <table class="lesson-table">
                <tr><th>Type</th><th>Setup</th><th>Best For</th></tr>
                <tr><td><strong>Fixed %</strong></td><td>Sell if stock drops 7-10% from entry</td><td>Simple, disciplined exit</td></tr>
                <tr><td><strong>Support-based</strong></td><td>Place stop just below a known support level</td><td>Technically informed, fewer whipsaws</td></tr>
                <tr><td><strong>Trailing Stop</strong></td><td>Moves up with the stock, locks in gains</td><td>Riding winners, protecting profits</td></tr>
                <tr><td><strong>Time Stop</strong></td><td>Exit if trade hasn't worked within X weeks</td><td>Avoiding dead money</td></tr>
            </table>

            <h2>Risk-Reward Ratio</h2>
            <div class="formula-box">Risk:Reward = (Entry - Stop Loss) : (Target - Entry)<br>Always target a minimum R:R of 1:2 (risk $1 to make $2)</div>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 Professional Risk Framework</div>
                <ul>
                    <li><strong>Per-trade risk:</strong> Never risk more than 1-2% of total portfolio on any single trade</li>
                    <li><strong>Max portfolio heat:</strong> Total open risk should not exceed 6-8% of portfolio value</li>
                    <li><strong>Correlation check:</strong> Don't have 5 positions that all move the same way — that's one big bet, not five</li>
                    <li><strong>Cash buffer:</strong> Always maintain 5-15% cash for opportunities and defense</li>
                </ul>
            </div>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: The 2008 Financial Crisis</div>
                <p>From October 2007 to March 2009, the S&P 500 fell <strong>56.8%</strong>. Investors who had no risk management and sat through the entire decline needed a <strong>131% gain</strong> just to break even — which took until 2013 (4+ years).</p>
                <p>Investors who maintained stop-losses and raised cash in 2008 were able to reinvest near the bottom in 2009, turning the crisis into the buying opportunity of a generation.</p>
            </div>
        `,
        quiz: [
            { question: "If your portfolio drops 50%, what gain do you need to break even?", options: ["50%", "75%", "100% — you need to double"], correct: 2 },
            { question: "What is the recommended maximum per-trade risk for professionals?", options: ["10-20% of total portfolio", "1-2% of total portfolio per position", "50% of available cash"], correct: 1 },
            { question: "Why is a 1:2 risk-reward ratio considered the minimum?", options: ["Because brokers require it", "Because you can be wrong on half your trades and still be profitable", "Because 1:2 is the SEC standard"], correct: 1 }
        ]
    },
    {
        id: 16,
        title: "ETFs, Bonds & Alternative Assets",
        content: `
            <p>A sophisticated portfolio extends beyond individual stocks. Understanding ETFs, fixed income, and alternative assets is essential for building institutional-grade diversification.</p>

            <h2>Exchange-Traded Funds (ETFs)</h2>
            <p>An ETF is a basket of securities (stocks, bonds, commodities) that trades on an exchange like a single stock. They combine the diversification of mutual funds with the liquidity of stocks.</p>
            <table class="lesson-table">
                <tr><th>ETF</th><th>Tracks</th><th>Expense Ratio</th><th>Use Case</th></tr>
                <tr><td><strong>SPY / VOO</strong></td><td>S&P 500</td><td>0.03-0.09%</td><td>Core U.S. large-cap exposure</td></tr>
                <tr><td><strong>QQQ</strong></td><td>NASDAQ-100</td><td>0.20%</td><td>Tech/growth overweight</td></tr>
                <tr><td><strong>VTI</strong></td><td>Total U.S. Stock Market</td><td>0.03%</td><td>Broadest U.S. equity exposure</td></tr>
                <tr><td><strong>VXUS</strong></td><td>International ex-U.S.</td><td>0.07%</td><td>Global diversification</td></tr>
                <tr><td><strong>BND / AGG</strong></td><td>Total U.S. Bond Market</td><td>0.03-0.04%</td><td>Fixed income stability</td></tr>
                <tr><td><strong>GLD / IAU</strong></td><td>Gold</td><td>0.25-0.40%</td><td>Inflation hedge, crisis safe haven</td></tr>
                <tr><td><strong>XLE / XLF / XLK</strong></td><td>Sector-specific</td><td>0.09%</td><td>Tactical sector rotation bets</td></tr>
            </table>

            <h2>Bonds — The Stability Layer</h2>
            <p>Bonds are IOUs: you lend money to a government or corporation, they pay you fixed interest (the "coupon"), and return your principal at maturity.</p>
            <table class="lesson-table">
                <tr><th>Bond Type</th><th>Issuer</th><th>Risk</th><th>Typical Yield</th></tr>
                <tr><td><strong>Treasury Bonds</strong></td><td>U.S. Government</td><td>Virtually zero (backed by full faith & credit)</td><td>4-5%</td></tr>
                <tr><td><strong>Corporate (IG)</strong></td><td>Blue-chip corporations</td><td>Low — investment grade rated BBB or above</td><td>5-6%</td></tr>
                <tr><td><strong>High Yield ("Junk")</strong></td><td>Riskier corporations</td><td>Higher — rated BB or below</td><td>7-10%</td></tr>
                <tr><td><strong>Municipal</strong></td><td>State/local governments</td><td>Low, but varies</td><td>3-4% (tax-free!)</td></tr>
            </table>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 The Bond-Stock Relationship</div>
                <p>Historically, bonds and stocks move in <strong>opposite directions</strong> (negative correlation). When stocks crash, investors flee to the safety of Treasury bonds, pushing bond prices up. This negative correlation is why a 60% stock / 40% bond portfolio has been the institutional standard for decades.</p>
                <p><em>However, in 2022, BOTH stocks and bonds crashed simultaneously — a rare and painful failure of this correlation. This occurred because the Fed was aggressively raising rates, which hurts both asset classes.</em></p>
            </div>

            <h2>Alternative Assets</h2>
            <ul>
                <li><strong>REITs (Real Estate Investment Trusts)</strong> — Own real estate portfolios through stocks. Required to distribute 90% of income as dividends. Examples: Realty Income (O), Prologis (PLD)</li>
                <li><strong>Commodities</strong> — Gold, oil, natural gas, copper. Hedge against inflation and geopolitical risk</li>
                <li><strong>Cryptocurrency</strong> — Bitcoin, Ethereum. Extremely volatile, uncorrelated to traditional assets. Treat as speculative satellite position (1-5% max)</li>
            </ul>
        `,
        quiz: [
            { question: "What is the primary advantage of an ETF over buying individual stocks?", options: ["ETFs always go up", "Instant diversification across many securities with a single purchase and low fees", "ETFs don't have any risk"], correct: 1 },
            { question: "Why have bonds traditionally been paired with stocks in portfolios?", options: ["Because they always have higher returns", "Their historically negative correlation means when stocks fall, bonds often rise — reducing portfolio volatility", "Because the SEC requires it"], correct: 1 },
            { question: "What makes REITs unique among investments?", options: ["They can only be bought by institutions", "They must distribute 90% of taxable income as dividends, creating reliable income", "They are not traded on exchanges"], correct: 1 }
        ]
    },
    {
        id: 17,
        title: "Dividends & Income Investing",
        content: `
            <p>Dividend investing is the strategy of building a portfolio of companies that pay regular, growing cash distributions to shareholders. It is the foundation of <strong>income investing</strong> — generating a passive income stream from your portfolio.</p>

            <h2>Key Dividend Metrics</h2>
            <table class="lesson-table">
                <tr><th>Metric</th><th>Formula</th><th>What It Tells You</th></tr>
                <tr><td><strong>Dividend Yield</strong></td><td>Annual Dividend / Stock Price</td><td>Cash return as % of investment</td></tr>
                <tr><td><strong>Payout Ratio</strong></td><td>Dividends / Net Income</td><td>What % of profits is paid out (lower is safer)</td></tr>
                <tr><td><strong>Dividend Growth Rate</strong></td><td>YoY increase in dividend</td><td>Is the company growing its dividend over time?</td></tr>
                <tr><td><strong>Years of Consecutive Increases</strong></td><td>Track record</td><td>Reliability and commitment to shareholders</td></tr>
            </table>

            <h2>Dividend Aristocrats</h2>
            <p>A "Dividend Aristocrat" is an S&P 500 company that has <strong>increased its dividend for at least 25 consecutive years</strong>. These are the most reliable income generators in the market:</p>
            <table class="lesson-table">
                <tr><th>Company</th><th>Ticker</th><th>Consecutive Increases</th><th>Current Yield</th></tr>
                <tr><td>Johnson & Johnson</td><td>JNJ</td><td>62 years</td><td>~3.0%</td></tr>
                <tr><td>Coca-Cola</td><td>KO</td><td>62 years</td><td>~3.1%</td></tr>
                <tr><td>Procter & Gamble</td><td>PG</td><td>68 years</td><td>~2.4%</td></tr>
                <tr><td>3M</td><td>MMM</td><td>65 years</td><td>~5.5%</td></tr>
                <tr><td>Realty Income</td><td>O</td><td>30 years</td><td>~5.4%</td></tr>
            </table>

            <h2>The Power of Dividend Compounding (DRIP)</h2>
            <p>A <strong>DRIP (Dividend Reinvestment Plan)</strong> automatically uses your dividend payments to buy more shares. This creates a compounding engine:</p>
            <div class="real-example">
                <div class="real-example-title">📊 Compounding Example: $10,000 in a 3% Yielding Stock</div>
                <p><strong>Without DRIP:</strong> You receive $300/year in cash. After 30 years: $9,000 in total dividends received.</p>
                <p><strong>With DRIP (reinvesting):</strong> Assuming 3% yield and 7% annual price growth, your $10,000 becomes approximately <strong>$102,000</strong> after 30 years. The reinvested dividends alone contributed ~$25,000 of that growth.</p>
            </div>

            <h2>Important Dates for Dividend Investors</h2>
            <table class="lesson-table">
                <tr><th>Date</th><th>What It Means</th></tr>
                <tr><td><strong>Declaration Date</strong></td><td>Company announces the dividend amount and dates</td></tr>
                <tr><td><strong>Ex-Dividend Date</strong></td><td>You must own the stock BEFORE this date to receive the dividend</td></tr>
                <tr><td><strong>Record Date</strong></td><td>Company checks who owns shares (1 day after ex-date)</td></tr>
                <tr><td><strong>Payment Date</strong></td><td>Cash actually deposited into your brokerage account</td></tr>
            </table>

            <div class="danger-box">
                <div class="danger-box-title">⚠️ The Dividend Trap</div>
                <p>An unusually high yield (8%+) can signal that the stock price has crashed because the company is in trouble — and the dividend is likely to be cut. Always check the payout ratio. If it's above 80-90%, the dividend may not be sustainable. AT&T was a famous "safe" dividend stock yielding 7%+ until it slashed its dividend by 47% in 2022.</p>
            </div>
        `,
        quiz: [
            { question: "What is a 'Dividend Aristocrat'?", options: ["Any stock that pays a dividend", "An S&P 500 company that has increased its dividend for 25+ consecutive years", "A company with the highest yield"], correct: 1 },
            { question: "What is a DRIP and why is it powerful?", options: ["A type of stock order", "Automatic dividend reinvestment that creates compound growth over time", "A way to avoid taxes on dividends"], correct: 1 },
            { question: "Why might an extremely high dividend yield (8%+) be a warning sign?", options: ["High yields are always good", "It often means the stock price has crashed because the company is in trouble, and the dividend may be cut", "The SEC restricts yields above 8%"], correct: 1 }
        ]
    },
    // ═══════════════════════════════════════════════════════════════
    //  PART V — ADVANCED STRATEGIES (Chapters 18–20)
    // ═══════════════════════════════════════════════════════════════
    {
        id: 18,
        title: "Options Fundamentals",
        content: `
            <p>Options are financial derivatives that give the holder the <strong>right, but not the obligation</strong>, to buy or sell 100 shares of a stock at a specific price (strike) by a specific date (expiration).</p>

            <h2>The Two Types of Options</h2>
            <table class="lesson-table">
                <tr><th>Type</th><th>Right</th><th>Buyer Expects</th><th>Max Loss (Buyer)</th></tr>
                <tr><td><strong>Call Option</strong></td><td>Right to BUY 100 shares at the strike price</td><td>Stock goes UP above strike</td><td>Premium paid</td></tr>
                <tr><td><strong>Put Option</strong></td><td>Right to SELL 100 shares at the strike price</td><td>Stock goes DOWN below strike</td><td>Premium paid</td></tr>
            </table>

            <h2>The Options Chain Decoded</h2>
            <pre>
AAPL — $185 | Expiration: March 15
──────────────────────────────────
Strike    Call Bid  Call Ask   Put Bid  Put Ask
$175      $11.50   $11.80     $1.20    $1.40     ← In-the-money call
$180      $7.20    $7.50      $2.00    $2.25
$185      $3.80    $4.10      $3.60    $3.90     ← At-the-money
$190      $1.50    $1.75      $6.30    $6.60
$195      $0.45    $0.65      $10.20   $10.50    ← Out-of-the-money call
            </pre>

            <h2>The Greeks — Options DNA</h2>
            <table class="lesson-table">
                <tr><th>Greek</th><th>Measures</th><th>What It Means</th></tr>
                <tr><td><strong>Delta (Δ)</strong></td><td>Price sensitivity to stock movement</td><td>Delta 0.50 = option moves $0.50 for every $1 stock move</td></tr>
                <tr><td><strong>Gamma (Γ)</strong></td><td>Rate of change of Delta</td><td>How fast Delta accelerates — highest at-the-money</td></tr>
                <tr><td><strong>Theta (Θ)</strong></td><td>Time decay per day</td><td>Options lose value every day — Theta is the enemy of option buyers</td></tr>
                <tr><td><strong>Vega (ν)</strong></td><td>Sensitivity to volatility changes</td><td>Higher IV = higher option prices. Vega tells you how much</td></tr>
            </table>

            <h2>Essential Strategies</h2>
            <h3>Covered Call (Income Strategy)</h3>
            <p>Own 100 shares of a stock, sell a call option against them. You collect the premium as income. If the stock stays below the strike, you keep the premium AND your shares.</p>

            <h3>Protective Put (Insurance)</h3>
            <p>Own shares and buy a put option as downside protection. Like paying an insurance premium — if the stock crashes, the put increases in value, offsetting your stock losses.</p>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 The Institutional Secret: Selling Premium</div>
                <p>Professional options traders overwhelmingly <strong>sell</strong> options rather than buy them. Why? Because Theta (time decay) works in the seller's favor — options lose value every single day. Approximately 60-80% of options expire worthless, meaning sellers collect premium the majority of the time.</p>
                <p><em>However, selling naked options carries unlimited risk. Professionals always use defined-risk spreads to cap their exposure.</em></p>
            </div>

            <div class="danger-box">
                <div class="danger-box-title">⚠️ Options Are NOT for Beginners</div>
                <p>Options amplify both gains AND losses. A stock dropping 5% might cause your option to lose 50-100% of its value. Never trade options with money you cannot afford to lose, and always start with simple strategies (covered calls, protective puts) before attempting complex multi-leg trades.</p>
            </div>
        `,
        quiz: [
            { question: "What does buying a Call option give you the right to do?", options: ["Sell 100 shares at the strike price", "Buy 100 shares at the strike price before expiration", "Receive dividends from the underlying stock"], correct: 1 },
            { question: "Why is Theta considered the 'enemy' of option buyers?", options: ["Because it increases the option price daily", "Because options lose value every day due to time decay, working against buyers who need the stock to move", "Because Theta only affects put options"], correct: 1 },
            { question: "What is the purpose of a Covered Call strategy?", options: ["To bet on a stock crash", "To generate income by selling call options against shares you already own", "To hedge against currency risk"], correct: 1 }
        ]
    },
    {
        id: 19,
        title: "Behavioral Finance & Trading Psychology",
        content: `
            <p>The biggest risk in your portfolio isn't the market — it's <strong>you</strong>. Behavioral finance studies how cognitive biases and emotions systematically cause investors to make irrational decisions. Understanding these biases is the first step to neutralizing them.</p>

            <h2>The Core Cognitive Biases</h2>
            <table class="lesson-table">
                <tr><th>Bias</th><th>What It Is</th><th>How It Destroys Returns</th><th>How to Fix It</th></tr>
                <tr><td><strong>FOMO</strong></td><td>Fear of Missing Out</td><td>Chasing a stock that's already up 200%</td><td>Have a written plan. If you didn't research it before the run, skip it.</td></tr>
                <tr><td><strong>Loss Aversion</strong></td><td>Losses hurt 2x more than equivalent gains feel good</td><td>Holding losers too long, selling winners too early</td><td>Pre-set stop-losses. Remove emotion from exit decisions.</td></tr>
                <tr><td><strong>Anchoring</strong></td><td>Fixating on a reference point (e.g., your purchase price)</td><td>"I'll sell when it gets back to my entry price"</td><td>The market doesn't care about your entry. Evaluate the stock as if you were buying it today.</td></tr>
                <tr><td><strong>Recency Bias</strong></td><td>Overweighting recent events</td><td>Assuming the last 3 months will continue forever</td><td>Study long-term historical patterns. Recessions end. Bull markets don't last forever.</td></tr>
                <tr><td><strong>Confirmation Bias</strong></td><td>Seeking information that confirms your existing view</td><td>Ignoring red flags because you "love" the stock</td><td>Actively seek the bear case. Read opposing analysis.</td></tr>
                <tr><td><strong>Sunk Cost Fallacy</strong></td><td>Continuing because you've already invested time/money</td><td>Adding to a losing position to "average down" without new thesis</td><td>Ask: "If I had cash, would I buy this stock at this price today?" If no, sell.</td></tr>
                <tr><td><strong>Overconfidence</strong></td><td>Believing you're smarter than the market</td><td>Over-concentrating, ignoring risk management</td><td>Track your actual win rate. Most overestimate by 20-30%.</td></tr>
            </table>

            <h2>The Trading Journal — Your Edge</h2>
            <p>Every professional trader maintains a journal. For each trade, document:</p>
            <ul>
                <li><strong>Entry thesis:</strong> WHY you are buying this specific stock at this specific price</li>
                <li><strong>Entry/Exit prices, stop-loss, target</strong></li>
                <li><strong>Emotional state:</strong> Were you calm, anxious, excited, revenge-trading?</li>
                <li><strong>Outcome:</strong> Win/loss, did you follow your plan?</li>
                <li><strong>Lesson learned:</strong> What would you do differently?</li>
            </ul>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 Emotional Control Framework</div>
                <p>Top hedge fund managers use a structured emotional protocol:</p>
                <ul>
                    <li><strong>Pre-trade checklist</strong> — Every entry must meet 5+ criteria before execution</li>
                    <li><strong>Position sizing by conviction</strong> — High conviction = larger position, not leverage</li>
                    <li><strong>The 48-hour rule</strong> — After a big loss, wait 48 hours before making any new trade</li>
                    <li><strong>Max daily loss limit</strong> — If you lose more than X in one day, close all screens and walk away</li>
                </ul>
                <p><em>The best traders are not the ones who never lose — they are the ones who lose small and let winners run.</em></p>
            </div>

            <div class="case-study-box">
                <div class="case-study-box-title">📜 Case Study: GameStop Short Squeeze (2021)</div>
                <p>In January 2021, GameStop (GME) went from $17 to $483 in less than 3 weeks, driven by retail FOMO on Reddit's WallStreetBets and a massive short squeeze. Millions of new investors piled in at the peak.</p>
                <p>Within days, it crashed back to $40. Those who bought at $300+ lost 85%+ in a week. The lesson: FOMO, herd mentality, and the absence of a risk management plan turned a historic event into catastrophic losses for many retail traders.</p>
            </div>
        `,
        quiz: [
            { question: "What is 'Loss Aversion' and why is it dangerous?", options: ["Avoiding all risk entirely", "The psychological tendency to feel losses 2x more intensely than gains, causing you to hold losers too long and sell winners too early", "A type of stop-loss order"], correct: 1 },
            { question: "What is the purpose of a trading journal?", options: ["To calculate taxes", "To systematically document and learn from every trade, identifying patterns in both strategy and emotional decision-making", "To track stock prices"], correct: 1 },
            { question: "What is the '48-hour rule' used by professional traders?", options: ["Wait 48 hours before any trade", "After a significant loss, wait 48 hours before making any new trades to prevent emotional revenge trading", "Close all positions every 48 hours"], correct: 1 }
        ]
    },
    {
        id: 20,
        title: "Building Your Edge",
        content: `
            <h2>Congratulations — You've Completed the Curriculum</h2>
            <p>You now possess the knowledge that 95% of retail investors never acquire. But knowledge alone is not enough — you need a <strong>systematic, repeatable process</strong> that converts this knowledge into consistent returns.</p>

            <h2>The Professional Stock Evaluation Process</h2>
            <ol>
                <li><strong>Ideation</strong> — Find candidates via institutional flow tracking, 13F analysis, earnings surprises, sector rotation signals, or the SmartMoney dashboard</li>
                <li><strong>Fundamental Screen</strong> — Revenue growth, margins, FCF, manageable debt, competitive moat</li>
                <li><strong>Valuation Check</strong> — Compare P/E, EV/EBITDA, PEG against sector peers. Is it reasonably priced?</li>
                <li><strong>Technical Setup</strong> — Above 200MA, RSI not overbought, near support, strong volume profile</li>
                <li><strong>Catalyst Identification</strong> — What specific event will drive the stock higher? Earnings, product launch, sector tailwinds?</li>
                <li><strong>Risk Geometry</strong> — Define entry, target, and stop-loss BEFORE buying. Minimum 1:2 risk-reward</li>
                <li><strong>Position Sizing</strong> — Risk 1-2% of portfolio maximum. Size based on conviction level</li>
                <li><strong>Execute & Monitor</strong> — Enter with discipline. Review weekly. Adjust stop-losses as the trade progresses</li>
            </ol>

            <h2>The SmartMoney Toolkit — Where to Start</h2>
            <table class="lesson-table">
                <tr><th>Feature</th><th>What It Does</th><th>Chapter Link</th></tr>
                <tr><td>Institutional Flow Dashboard</td><td>Tracks 13F filings, institutional accumulation, and divergence signals</td><td>Ch 10</td></tr>
                <tr><td>Stock Deep Analysis</td><td>Sector-relative valuation, insider activity, technical confirmation</td><td>Ch 5, 6, 8</td></tr>
                <tr><td>News AI Analysis</td><td>AI-powered news sentiment scoring — buy/sell/hold signals from breaking news</td><td>Ch 12</td></tr>
                <tr><td>Smart Portfolio Allocator</td><td>Conviction-weighted portfolio construction with risk profiling</td><td>Ch 14, 15</td></tr>
                <tr><td>Watchlist Intelligence</td><td>Real-time sentiment scores and price monitoring for your selected stocks</td><td>Ch 8, 10</td></tr>
            </table>

            <h2>The Habits of Successful Investors</h2>
            <ul>
                <li><strong>Read voraciously</strong> — Annual reports, earnings transcripts, macro research. 10 pages/day compounds to 3,650 pages/year</li>
                <li><strong>Journal every trade</strong> — Document your thesis, emotions, and outcome. Review monthly for patterns</li>
                <li><strong>Think in probabilities</strong> — No trade is certain. Frame every decision as "What is the expected value?"</li>
                <li><strong>Be patient</strong> — The best trades often take months to unfold. Sitting in cash IS a position</li>
                <li><strong>Never stop learning</strong> — Markets evolve. The strategies that worked in 2010 may not work in 2025. Adapt constantly</li>
            </ul>

            <div class="wall-street-box">
                <div class="wall-street-box-title">🏦 Final Message from the Trading Desk</div>
                <p>The capital markets are the greatest wealth-building machine in human history. The S&P 500 has returned approximately 10% per year over the last century — through world wars, pandemics, financial crises, and technological revolutions.</p>
                <p>Your edge is not a secret indicator or a hot stock tip. Your edge is <strong>discipline, patience, continuous learning, and rigorous risk management.</strong></p>
                <p><em>"The stock market is a device for transferring money from the impatient to the patient." — Warren Buffett</em></p>
            </div>

            <div style="text-align:center; padding: 3rem 0; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; margin: 2rem 0; background: linear-gradient(135deg, rgba(0,210,255,0.05), rgba(58,123,213,0.05));">
                <h2 style="margin-bottom: 0.5rem;">🎓 You're Ready</h2>
                <p style="color:var(--text-muted); margin-bottom: 20px;">Apply everything you've learned using the SmartMoney Terminal.</p>
                <a href="/" class="action-link-btn" style="font-size: 1.1rem; padding: 0.75rem 2rem;">Return to SmartMoney Dashboard →</a>
            </div>
        `,
        quiz: []
    }
];
