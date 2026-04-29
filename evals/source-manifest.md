# Source Manifest

Every URL the Investor Ops & Intelligence Suite uses, with the role each one
plays in the system. The capstone rubric requires 30+ unique sources across
the corpus, references, eval fixtures, and external integrations.

Last updated: 2026-04-29.

---

## 1. RAG corpus — M1 Nippon India fund factsheets (6)

Indexed by the startup ingest in `backend/app/main.py` via
`backend/app/services/rag/corpus.py::NIPPON_INDIA_SCHEMES`. Re-fetched daily by
`POST /api/rag/refresh` (cron `0 3 * * *` UTC).

1. https://www.indmoney.com/mutual-funds/nippon-india-elss-tax-saver-fund-direct-plan-growth-option-2751
2. https://www.indmoney.com/mutual-funds/nippon-india-nifty-auto-index-fund-direct-growth-1048613
3. https://www.indmoney.com/mutual-funds/nippon-india-short-duration-fund-direct-plan-growth-plan-2268
4. https://www.indmoney.com/mutual-funds/nippon-india-crisil-ibx-aaa-financial-svcs-dec-2026-idx-fd-dir-growth-1048293
5. https://www.indmoney.com/mutual-funds/nippon-india-silver-etf-fund-of-fund-fof-direct-growth-1040380
6. https://www.indmoney.com/mutual-funds/nippon-india-balanced-advantage-fund-direct-growth-plan-4324

## 2. RAG corpus — M2 Fee scenario explainers (4)

Same ingest path, category `fee_scenario`. Powers Smart-Sync answers that
combine a fund-specific value with a fee/metric concept.

7. https://groww.in/p/expense-ratio
8. https://groww.in/blog/asset-under-management
9. https://groww.in/p/exit-load-in-mutual-funds
10. https://groww.in/p/nav

## 3. Pulse data source (1)

11. Google Play Store reviews for the INDMoney app
    (https://play.google.com/store/apps/details?id=in.indmoney) —
    fetched via `google-play-scraper` at `POST /api/scrape`. Raw Play Store
    URL is the conceptual source; the actual payload is the scraper's JSON.

## 4. External SDKs / hosted services (10)

12. Anthropic API (Claude Sonnet 4.6) — https://docs.anthropic.com/en/api
13. Anthropic Python SDK — https://github.com/anthropics/anthropic-sdk-python
14. Supabase (Auth + Postgres + Storage) — https://supabase.com
15. Supabase Python SDK — https://github.com/supabase/supabase-py
16. Vapi voice agent (Web SDK) — https://docs.vapi.ai
17. Vapi Web SDK package — https://www.npmjs.com/package/@vapi-ai/web
18. Google Calendar API — https://developers.google.com/calendar/api
19. Google Sheets API — https://developers.google.com/sheets/api
20. Google API Python Client — https://github.com/googleapis/google-api-python-client
21. Resend transactional email — https://resend.com/docs/api-reference/emails/send-email

## 5. Embeddings + Vector store (3)

22. sentence-transformers/all-MiniLM-L6-v2 — https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
23. ChromaDB — https://docs.trychroma.com
24. langdetect (R-PULSE7 English filter) — https://pypi.org/project/langdetect/

## 6. Protocol / standards references (3)

25. Model Context Protocol — https://modelcontextprotocol.io
26. MCP Python SDK — https://github.com/modelcontextprotocol/python-sdk
27. SEBI guidance on mutual fund expense ratios (regulatory context) —
    https://www.sebi.gov.in/sebi_data/faqfiles/jul-2017/1500618083164.pdf

## 7. Frontend / runtime (4)

28. Next.js 16 (with renamed proxy.ts file convention) —
    https://nextjs.org/docs
29. React 19 — https://react.dev
30. FastAPI — https://fastapi.tiangolo.com
31. Render free web-service tier (deployment target) — https://render.com/docs/free

## 8. Eval fixtures + scoring references (2)

32. capstone problem statement (in-repo: `docs/ProblemStatement.md`)
33. architecture spec (in-repo: `docs/superpowers/specs/2026-04-22-investor-ops-suite-design.md`)

---

**Total unique URLs/sources: 33** (10 corpus + 1 Play Store + 10 SDKs/services
+ 3 embeddings/vector + 3 protocol + 4 frontend/runtime + 2 in-repo specs).

The system stays inside this set: no LLM is allowed to consult anything beyond
items 1-10 when answering RAG questions (R-G3 Sources are mandatory).
