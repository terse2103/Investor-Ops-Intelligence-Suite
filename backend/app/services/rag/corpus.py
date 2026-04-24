"""Seed URLs for the INDMoney RAG corpus (Pillar A).

6 Nippon India schemes covering ELSS, sector index, short-duration debt,
target-maturity debt, commodity FoF, and hybrid BAF. M2 fee-explainer docs
will be added on Day 3.
"""

NIPPON_INDIA_SCHEMES: list[dict] = [
    {
        "url": "https://www.indmoney.com/mutual-funds/nippon-india-elss-tax-saver-fund-direct-plan-growth-option-2751",
        "title": "Nippon India ELSS Tax Saver Fund",
        "category": "mf_factsheet",
    },
    {
        "url": "https://www.indmoney.com/mutual-funds/nippon-india-nifty-auto-index-fund-direct-growth-1048613",
        "title": "Nippon India Nifty Auto Index Fund",
        "category": "mf_factsheet",
    },
    {
        "url": "https://www.indmoney.com/mutual-funds/nippon-india-short-duration-fund-direct-plan-growth-plan-2268",
        "title": "Nippon India Short Duration Fund",
        "category": "mf_factsheet",
    },
    {
        "url": "https://www.indmoney.com/mutual-funds/nippon-india-crisil-ibx-aaa-financial-svcs-dec-2026-idx-fd-dir-growth-1048293",
        "title": "Nippon India CRISIL IBX AAA Financial Services Dec 2026 Index Fund",
        "category": "mf_factsheet",
    },
    {
        "url": "https://www.indmoney.com/mutual-funds/nippon-india-silver-etf-fund-of-fund-fof-direct-growth-1040380",
        "title": "Nippon India Silver ETF Fund of Fund",
        "category": "mf_factsheet",
    },
    {
        "url": "https://www.indmoney.com/mutual-funds/nippon-india-balanced-advantage-fund-direct-growth-plan-4324",
        "title": "Nippon India Balanced Advantage Fund",
        "category": "mf_factsheet",
    },
]
