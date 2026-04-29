# Suggested Improvements

Ideas that would meaningfully improve the Investor Ops & Intelligence Suite
beyond the 7-day plan. Each is listed with **why it matters**, **rough
effort**, and **a hint at how to implement** so you can pick them up later.

Nothing here is required for the capstone; the 38-item plan is the contract.
These are post-submission follow-ups.

---

## Reliability + observability

### 1. Sentry / OpenTelemetry instrumentation
- **Why:** the current backend has structured logs but no centralised error
  reporting. Eval failures and 502s in `/api/scrape` or `/api/approvals/*`
  will be invisible in production unless someone tails Render logs.
- **Effort:** small (~1 hour). `sentry-sdk` for FastAPI auto-instruments.
- **Hint:** `sentry_sdk.init(dsn=settings.sentry_dsn, integrations=[FastApiIntegration()])`
  in `app/main.py`. Wire `traces_sample_rate=0.1` so demo cost stays low.

### 2. Pre-flight env-var validation on startup
- **Why:** today the backend starts even if `ANTHROPIC_API_KEY` is missing,
  and only surfaces the failure on the first request. A `pydantic-settings`
  required-field check would surface misconfiguration at boot.
- **Effort:** small.
- **Hint:** mark critical fields with no default; fail-fast on import.

### 3. Database-backed audit log table for admin actions
- **Why:** `action_audit` covers post-approval execution but not the human
  decision metadata (which admin approved, when, IP, user-agent). A
  `decision_audit` table closes the loop for compliance review.
- **Effort:** small.

---

## Eval + scoring rigor

### 4. LLM-grader for RAG cases
- **Why:** `evals/run_evals.py` uses URL-string matching as a faithfulness
  proxy. A second Claude call comparing each answer to the cited chunk would
  score faithfulness more accurately. The current grader is conservative,
  but it can both over-credit (URL in answer ≠ fact in answer) and
  under-credit (correct answer with URL truncated).
- **Effort:** medium. Add a `_grade_with_llm` function that prompts Claude
  with question + answer + retrieved chunks and asks for a 0/2/4 score.

### 5. Eval drift tracking over time
- **Why:** corpus content can shift (URLs update, expense ratios drift). A
  weekly eval-runner workflow that posts the score to a Slack/Discord
  channel would catch silent regressions.
- **Effort:** small (mirror `weekly-scrape.yml`).

### 6. Adversarial eval harness
- **Why:** our 3 safety cases are fixed strings. A fuzz-style generator that
  rewrites refusal triggers in ~50 surface forms and re-runs S1/S3 would
  push Safety closer to a true 30/30 guarantee.
- **Effort:** medium.

---

## Product UX

### 7. Pulse history page (`/admin/pulse/history`)
- **Why:** the `pulses` table accumulates rows weekly. Today only the latest
  is surfaced. A history page with mini-line-charts of theme volume over time
  would give the admin a real product-research surface.
- **Effort:** medium. Reuse the existing pulse cards.

### 8. WebSocket for live approval queue
- **Why:** the admin currently clicks "Refresh" to see new pending actions.
  A Supabase realtime subscription on `pending_actions` would let the queue
  auto-update as voice calls land.
- **Effort:** small (Supabase JS already supports `.on('postgres_changes')`).

### 9. Mobile-responsive layouts
- **Why:** the glass-card UI uses fixed widths and inline styles. On a
  phone the sidebar overflows.
- **Effort:** medium. Either rewrite to Tailwind responsive utilities or
  collapse the sidebar to a hamburger.

### 10. Light/dark theme toggle
- **Why:** today the CSS variables hard-code one palette. A class-based
  toggle on the body would not be invasive.
- **Effort:** small.

### 11. Voice transcript download + booking-code display post-call
- **Why:** users hear the booking code on the call but can't see it in the
  UI; the post-call frontend just says "check email after approval". A
  short post-call poll on `/api/voice/calls/{id}` would expose the booking
  code immediately.
- **Effort:** small. New endpoint + a 3-attempt poll on call-end.

---

## RAG + Pulse depth

### 12. Expand the corpus to 30+ Nippon India schemes (or add other AMCs)
- **Why:** the current 6-fund corpus limits R3-style ambiguity tests and
  caps Smart-Sync coverage. Adding all 30+ Nippon India direct-plan
  schemes (or the SEBI-registered top-50 by AUM) makes the demo feel
  production-realistic.
- **Effort:** small per fund. Add URLs to `corpus.py` and let the daily
  refresh pick them up.

### 13. pgvector instead of Chroma
- **Why:** Chroma works for the demo but adds a separate persistence layer
  on Render's ephemeral disk. pgvector lives inside Supabase, removes the
  startup ingest race, and unifies backups.
- **Effort:** medium. Implement `Retriever` with pgvector, swap in
  `get_retriever()`. The retriever interface was designed for this.

### 14. Hybrid retrieval (BM25 + dense)
- **Why:** dense-only retrieval misses exact-string queries like
  "expense ratio 1.04%". BM25 over the same chunks, fused with the dense
  scores, would catch those.
- **Effort:** medium. `rank_bm25` for the BM25 side; weighted RRF fusion.

### 15. Citation chunk highlighting in the UI
- **Why:** today the chatbot shows the cited URL but not which paragraph
  was used. Highlighting the source chunk in a side panel would build
  trust faster than a bare URL.
- **Effort:** medium. Return chunk text + offset alongside the URL; render
  in a collapsible side card.

### 16. PII pattern expansion
- **Why:** `core/pii.py` covers PAN, Aadhaar, phone, email, account number.
  Common gaps: Indian DOB strings, IFSC codes, UPI handles, bank-account
  IBANs. Each is a small regex; small impact individually but compounding.
- **Effort:** small per pattern.

---

## Voice agent depth

### 17. Vapi function-tool for live slot lookup
- **Why:** today the assistant "offers two slots" hard-coded. A function tool
  hitting `/api/voice/slots` (which queries the calendar SA) would give real
  availability.
- **Effort:** medium.

### 18. Multi-language voice support (Hindi + Tamil + Bengali)
- **Why:** INDMoney's user base is non-English-majority. Vapi supports
  multiple LLM-voice combinations; the prompt template just needs locale
  branches.
- **Effort:** medium.

### 19. Call-recording playback in `/admin/approvals`
- **Why:** when approving a borderline action the admin currently has to go
  to Vapi's dashboard to listen. Embedding the recording URL inline would
  cut review time.
- **Effort:** small.

---

## Infra + DX

### 20. CI workflow that runs tests on every PR
- **Why:** today the test suite runs locally only. A `.github/workflows/ci.yml`
  with `uv run pytest` and `npm run lint` would catch regressions before
  merge.
- **Effort:** small.

### 21. OpenAPI → TypeScript codegen
- **Why:** the frontend hand-writes interfaces matching FastAPI responses.
  A `pnpm gen:api` step that pulls FastAPI's OpenAPI schema and runs
  `openapi-typescript` would make the contract type-safe end-to-end.
- **Effort:** small.

### 22. Devcontainer / Docker compose for one-command dev
- **Why:** new contributors today need Python 3.11, uv, Node 20, npm, and
  to deal with ChromaDB native deps on Windows. A devcontainer or docker
  compose file would reduce onboarding to `code .` → "Reopen in container".
- **Effort:** medium.

### 23. Real database tests (not mocks) in a Postgres container
- **Why:** every test in `backend/tests/` mocks Supabase. Schema-mismatch
  bugs (we hit one on Day 3 when the scraper used `score`/`at` instead of
  `rating`/`posted_at`) would be caught immediately by a Postgres + pgvector
  testcontainer.
- **Effort:** medium. `pytest-postgres` + a fixture that runs the migration
  before each session.

### 24. Pre-commit hooks (ruff format + lint, mypy, eslint)
- **Why:** code quality drift is easier to prevent than to fix.
- **Effort:** small.

---

## Compliance + business

### 25. RBI / SEBI compliance review checklist
- **Why:** "no investment advice" is encoded in `R-G1` but a real product
  needs a documented compliance review (RBI advertising guidelines, SEBI
  Investment Adviser regulations). A checklist file would lower the bar
  for a real launch conversation.
- **Effort:** small (write the doc; review is external).

### 26. User-facing privacy policy + data retention page
- **Why:** the system stores transcripts, reviews, and contact emails. Real
  users need to see what's kept, for how long, and how to delete it.
- **Effort:** small (template). Backed by Supabase delete cascade rules
  already in the schema.

### 27. Rate limiting on more endpoints
- **Why:** today only `/api/rag/query` is rate-limited (10/min). Add limiters
  to `/api/voice/post-call` (per call_id), `/api/scrape` (1/hour by source),
  and `/api/approvals/*/decide` (per admin) to prevent runaway behaviour.
- **Effort:** small. SlowAPI is already wired.

---

## Notes on prioritisation

If you only do **three** of these, pick:

1. **#23 Real DB tests** — biggest correctness win, prevents the schema
   bugs we hit in Day 3.
2. **#4 LLM-grader for RAG** — biggest eval-quality win; pushes the
   reported score closer to the true score.
3. **#13 pgvector** — biggest ops win; removes the Chroma cold-start and
   unifies backups inside Supabase.

If you have one afternoon, pick **#20 CI workflow** + **#2 startup env-var
validation**. Both are tiny and protect everything else.
