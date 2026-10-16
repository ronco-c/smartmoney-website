# whale_data.py

WHALE_PORTFOLIOS = {
    "NVDA": {
        "name": "Nvidia Corporation",
        "manager": "Jensen Huang",
        "description": "Nvidia's strategic investments in AI, robotics, and biotech companies.",
        "holdings": [
            {"symbol": "ARM", "shares": 1960784, "avg_buy_price": 48.0, "shares_change_pct": 0},
            {"symbol": "RXRX", "shares": 7706363, "avg_buy_price": 7.5, "is_new": True, "shares_change_pct": None},
            {"symbol": "SOUN", "shares": 1730883, "avg_buy_price": 2.1, "shares_change_pct": 15.5},
            {"symbol": "NNOX", "shares": 59632, "avg_buy_price": 6.8, "shares_change_pct": -5.2}
        ]
    },
    "AAPL": {
        "name": "Apple Inc.",
        "manager": "Tim Cook",
        "description": "Apple's corporate ventures and strategic interests, tightly integrated with its ecosystem.",
        "holdings": [
            {"symbol": "ARM", "shares": 2500000, "avg_buy_price": 51.0, "shares_change_pct": 0},
            {"symbol": "GSAT", "shares": 15000000, "avg_buy_price": 1.2, "shares_change_pct": 5.0},
            {"symbol": "GLW", "shares": 8000000, "avg_buy_price": 28.0, "shares_change_pct": 0}
        ]
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "manager": "Sundar Pichai",
        "description": "Alphabet's bets on aerospace, healthcare, and enterprise software.",
        "holdings": [
            {"symbol": "ASTS", "shares": 25000000, "avg_buy_price": 4.5, "shares_change_pct": 0},
            {"symbol": "PL", "shares": 120000000, "avg_buy_price": 3.2, "shares_change_pct": 2.1},
            {"symbol": "RVMD", "shares": 8500000, "avg_buy_price": 18.0, "is_new": True, "shares_change_pct": None},
            {"symbol": "ARM", "shares": 1500000, "avg_buy_price": 60.0, "shares_change_pct": 0},
            {"symbol": "FRSH", "shares": 8000000, "avg_buy_price": 15.0, "shares_change_pct": -10.5},
            {"symbol": "CRWD", "shares": 450000, "avg_buy_price": 120.0, "shares_change_pct": 5.0},
            {"symbol": "DDOG", "shares": 300000, "avg_buy_price": 80.0, "shares_change_pct": 2.0}
        ]
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "manager": "Satya Nadella",
        "description": "Microsoft's strategic investments emphasizing AI, cloud, and enterprise technology.",
        "holdings": [
            {"symbol": "RBRK", "shares": 5000000, "avg_buy_price": 32.0, "shares_change_pct": 0},
            {"symbol": "GRAB", "shares": 12000000, "avg_buy_price": 3.1, "shares_change_pct": 0},
            {"symbol": "ARM", "shares": 1200000, "avg_buy_price": 50.0, "shares_change_pct": 0}
        ]
    },
    "AMZN": {
        "name": "Amazon.com Inc.",
        "manager": "Andy Jassy",
        "description": "Amazon's investments in mobility, logistics, and cloud infrastructure.",
        "holdings": [
            {"symbol": "RIVN", "shares": 158363834, "avg_buy_price": 78.0, "shares_change_pct": 0},
            {"symbol": "AUR", "shares": 5000000, "avg_buy_price": 4.5, "shares_change_pct": 0},
            {"symbol": "SG", "shares": 2000000, "avg_buy_price": 15.0, "shares_change_pct": 0}
        ]
    },
    "TSM": {
        "name": "Taiwan Semiconductor",
        "manager": "C.C. Wei",
        "description": "TSMC's strategic ecosystem investments across the semiconductor supply chain.",
        "holdings": [
            {"symbol": "ASML", "shares": 250000, "avg_buy_price": 500.0, "shares_change_pct": 0},
            {"symbol": "ARM", "shares": 850000, "avg_buy_price": 51.0, "shares_change_pct": 0}
        ]
    },
    "META": {
        "name": "Meta Platforms Inc.",
        "manager": "Mark Zuckerberg",
        "description": "Meta's strategic holdings focusing on connectivity, AR/VR ecosystem, and communications.",
        "holdings": [
            {"symbol": "RBLX", "shares": 5000000, "avg_buy_price": 45.0, "shares_change_pct": 0},
            {"symbol": "U", "shares": 3500000, "avg_buy_price": 35.0, "shares_change_pct": 0},
            {"symbol": "MSFT", "shares": 2000000, "avg_buy_price": 280.0, "shares_change_pct": 0}
        ]
    },
    "AVGO": {
        "name": "Broadcom Inc.",
        "manager": "Hock Tan",
        "description": "Broadcom's corporate investments in semiconductor and infrastructure software.",
        "holdings": [
            {"symbol": "MRVL", "shares": 2000000, "avg_buy_price": 45.0, "shares_change_pct": 0},
            {"symbol": "SWKS", "shares": 500000, "avg_buy_price": 100.0, "shares_change_pct": 0}
        ]
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "manager": "Elon Musk",
        "description": "Tesla's non-operational corporate treasury, primarily focused on Bitcoin alongside liquid cash reserves.",
        "holdings": [
            {"symbol": "BTC", "shares": 11509, "avg_buy_price": 31620.0, "shares_change_pct": 0}
        ]
    },
    "BRK-B": {
        "name": "Berkshire Hathaway",
        "manager": "Warren Buffett",
        "description": "The Oracle of Omaha's massive value investing portfolio.",
        "holdings": [
            {"symbol": "AAPL", "shares": 400000000, "avg_buy_price": 39.0, "shares_change_pct": -12.5},
            {"symbol": "BAC", "shares": 790000000, "avg_buy_price": 24.0, "shares_change_pct": 0},
            {"symbol": "AXP", "shares": 151610700, "avg_buy_price": 15.0, "shares_change_pct": 0},
            {"symbol": "KO", "shares": 400000000, "avg_buy_price": 3.25, "shares_change_pct": 0},
            {"symbol": "CVX", "shares": 122980206, "avg_buy_price": 95.0, "shares_change_pct": -3.2},
            {"symbol": "OXY", "shares": 248018128, "avg_buy_price": 50.0, "shares_change_pct": 4.5}
        ]
    },
    "WMT": {
        "name": "Walmart Inc.",
        "manager": "Doug McMillon",
        "description": "Walmart's strategic stakes in retail, logistics, and e-commerce partners globally.",
        "holdings": [
            {"symbol": "JD", "shares": 144000000, "avg_buy_price": 30.0, "shares_change_pct": -10.0},
            {"symbol": "SYMB", "shares": 4500000, "avg_buy_price": 40.0, "shares_change_pct": 0}
        ]
    },
    "LLY": {
        "name": "Eli Lilly",
        "manager": "David Ricks",
        "description": "Biotech and pharmaceutical investments in promising clinical-stage companies.",
        "holdings": [
            {"symbol": "PRME", "shares": 2500000, "avg_buy_price": 15.0, "shares_change_pct": 0},
            {"symbol": "RXRX", "shares": 1200000, "avg_buy_price": 10.0, "shares_change_pct": 0}
        ]
    },
    "SSNLF": {
        "name": "Samsung Electronics",
        "manager": "Han Jong-hee",
        "description": "Samsung's stakes in suppliers and joint ventures across the electronics sector.",
        "holdings": [
            {"symbol": "ASML", "shares": 1500000, "avg_buy_price": 350.0, "shares_change_pct": -5.0},
            {"symbol": "GLW", "shares": 11500000, "avg_buy_price": 20.0, "shares_change_pct": 0},
            {"symbol": "BYDDY", "shares": 4500000, "avg_buy_price": 15.0, "shares_change_pct": 0}
        ]
    },
    "JPM": {
        "name": "JPMorgan Chase",
        "manager": "Jamie Dimon",
        "description": "JPMorgan's massive institutional holding portfolio across diverse asset classes.",
        "holdings": [
            {"symbol": "MSFT", "shares": 120000000, "avg_buy_price": 250.0, "shares_change_pct": 2.5},
            {"symbol": "AAPL", "shares": 115000000, "avg_buy_price": 160.0, "shares_change_pct": -1.5},
            {"symbol": "SPY", "shares": 45000000, "avg_buy_price": 410.0, "shares_change_pct": 5.0},
            {"symbol": "NVDA", "shares": 35000000, "avg_buy_price": 350.0, "shares_change_pct": 8.0}
        ]
    },
    "XOM": {
        "name": "Exxon Mobil",
        "manager": "Darren Woods",
        "description": "Energy transition and strategic resource investments.",
        "holdings": [
            {"symbol": "DEN", "shares": 15000000, "avg_buy_price": 85.0, "shares_change_pct": 0},
            {"symbol": "PXD", "shares": 25000000, "avg_buy_price": 220.0, "shares_change_pct": 0}
        ]
    },
    "V": {
        "name": "Visa Inc.",
        "manager": "Ryan McInerney",
        "description": "Visa's investments in fintech, payments networks, and digital infrastructure.",
        "holdings": [
            {"symbol": "SQ", "shares": 1500000, "avg_buy_price": 65.0, "shares_change_pct": 0},
            {"symbol": "MQ", "shares": 8500000, "avg_buy_price": 12.0, "shares_change_pct": 0},
            {"symbol": "TOST", "shares": 3000000, "avg_buy_price": 18.0, "shares_change_pct": 0}
        ]
    },
    "JNJ": {
        "name": "Johnson & Johnson",
        "manager": "Joaquin Duato",
        "description": "Strategic stakes in medical devices and innovative healthcare solutions.",
        "holdings": [
            {"symbol": "KVUE", "shares": 190000000, "avg_buy_price": 22.0, "shares_change_pct": 0},
            {"symbol": "LNTH", "shares": 3500000, "avg_buy_price": 65.0, "shares_change_pct": 0}
        ]
    },
    "ASML": {
        "name": "ASML Holding",
        "manager": "Peter Wennink",
        "description": "ASML's strategic holdings to secure the high-end semiconductor supply chain.",
        "holdings": [
            {"symbol": "LRCX", "shares": 150000, "avg_buy_price": 450.0, "shares_change_pct": 0},
            {"symbol": "AMAT", "shares": 250000, "avg_buy_price": 120.0, "shares_change_pct": 0},
            {"symbol": "KLAC", "shares": 180000, "avg_buy_price": 300.0, "shares_change_pct": 0}
        ]
    }
}
