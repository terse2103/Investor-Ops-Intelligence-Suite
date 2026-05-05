"""Seed URLs for the INDMoney RAG corpus (Pillar A).

M1: 6 Nippon India scheme factsheets (ELSS, sector index, short-duration debt,
target-maturity debt, commodity FoF, hybrid BAF).
M2: 4 INDMoney fee-explainer pages covering expense ratio, AUM, exit load, and NAV.

ALL_SOURCES is the unified seed used by the startup ingest in app.main.
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

FEE_EXPLAINER_DOCS: list[dict] = [
    {
        "url": "https://www.indmoney.com/blog/mutual-funds/what-is-expense-ratio",
        "title": "Expense Ratio in Mutual Funds",
        "category": "fee_scenario",
    },
    {
        "url": "https://www.indmoney.com/blog/mutual-funds/what-is-aum-in-mutual-funds",
        "title": "Assets Under Management (AUM)",
        "category": "fee_scenario",
    },
    {
        "url": "https://www.indmoney.com/blog/mutual-funds/exit-load-mutual-funds-explained",
        "title": "Exit Load in Mutual Funds",
        "category": "fee_scenario",
    },
    {
        "url": "https://www.indmoney.com/blog/mutual-funds/what-is-nav-in-mutual-funds",
        "title": "Net Asset Value (NAV)",
        "category": "fee_scenario",
    },
]

ALL_SOURCES: list[dict] = NIPPON_INDIA_SCHEMES + FEE_EXPLAINER_DOCS
