# 7-Day Implementation Plan

High-level day-by-day to-do list with checkboxes. Tick items off as they land. Update the progress bar at the top as you go.

---

## Progress

**Completed: 28 / 38 items → ~74%** — Day 1 + Day 2 + Day 3 + Day 4 done.

```
████████████████████████░░░░░░░░  74%
```

> Update this bar as you check items. Percentage = (completed items / 38) × 100.

---

## Day 1 — Foundation & Scaffolding
*Goal: decisions locked, accounts provisioned, skeleton compiles and logs in.*

- [x] Architecture spec written (`docs/superpowers/specs/2026-04-22-investor-ops-suite-design.md`)
- [x] `docs/Rules.md` drafted
- [x] `docs/EdgeCases.md` drafted
- [x] `docs/Evals.md` drafted
- [x] Lock Day-1 decisions: RAG stack + monorepo layout + Render vs Railway
- [x] Provision accounts: Supabase, Vapi, Vercel, Render, Google Cloud (OAuth consent), GitHub repo
- [x] Scaffold monorepo: Next.js (`frontend/`), FastAPI (`backend/`), `evals/`, `docs/`
- [x] Supabase: create all 10 tables with RLS + seed admin/user accounts
- [x] Login flow working end-to-end (Next.js → Supabase Auth → role-gated routes)

## Day 2 — M1 RAG Chatbot (Pillar A core)
*Goal: user can ask MF questions and get cited, facts-only answers.*

- [x] Ingest INDMoney corpus (5-10 pages) into the vector store
- [x] Retriever + LLM answer composition with citations and "Last updated from sources"
- [x] PII guard middleware wired on LLM in/out
- [x] `/user/chatbot` route live end-to-end
- [x] 3 RAG eval cases written in `evals/rag-eval.md` and passing
- [x] 1 safety eval case (investment advice refusal) passing

## Day 3 — M2 Pulse + Fee Explainer (Pillar A complete + Pillar B foundation)
*Goal: scraped reviews become a pulse; fee docs fold into the RAG index; Smart-Sync works.*

- [x] Scraper via `google-play-scraper` with scrape-time filter (R-PULSE7: English + >5 words)
- [x] `/api/scrape` endpoint + GitHub Actions weekly cron wired
- [x] Pulse generator (max 5 themes, top 3, 3 quotes, ≤250 words, exactly 3 actions)
- [x] `current_themes` cache populated for Vapi injection
- [x] Fee Explainer docs folded into the RAG index (completes Pillar A)
- [x] `/admin/pulse` route live with "Refresh now" button
- [x] Remaining 2 RAG eval cases (fee-related) + `evals/ux-eval.md` rubric passing

## Day 4 — M3 Voice Agent (Pillar B complete)
*Goal: themed voice call books an advisor; post-call writes pending_actions.*

- [x] Vapi agent configured with scripted M3 flow (greet → disclaimer → topic → time → 2 slots → confirm)
- [x] Theme injection via Vapi dynamic variables from `current_themes`
- [x] `/user/voice` route live with Vapi Web SDK embedded
- [x] Post-call webhook writes 3 `pending_actions` per booking
- [x] Remaining 2 safety eval cases (PII, prompt injection) passing
- [x] Voice theme-mention logic check (UX eval) passing

## Day 5 — Pillar C (HITL Approval Center)
*Goal: admin approves/rejects; Google APIs + Gmail MCP execute; user gets email.*

- [ ] `/admin/approvals` UI showing pending actions with approve/reject
- [ ] `core/google_api.py`: Calendar API tentative hold + Sheets API append
- [ ] `core/mcp_client.py`: real Gmail MCP draft creation
- [ ] Market Context from latest pulse injected into email draft payload
- [ ] `core/notifier.py`: email on final booking decision
- [ ] `/user/settings` live for saving notification email

## Day 6 — Evals + Hardening
*Goal: full eval run ≥ 85/100. Fix whatever's dropping the score.*

- [ ] `evals/run_evals.py` offline runner hitting live endpoints
- [ ] Full eval suite executed; results written to `evals/eval-report.md`
- [ ] Score ≥ 85/100 confirmed (Safety must be 30/30)
- [ ] Source Manifest (30+ URLs) written
- [ ] Bug fixes from eval findings

## Day 7 — Demo + Submission
*Goal: recorded video, polished README, submitted.*

- [ ] 5-minute demo video recorded (Pulse → themed voice call → Smart-Sync FAQ → approval → email)
- [ ] README written (setup, architecture link, demo link)
- [ ] Final `evals/eval-report.md` committed
- [ ] End-to-end smoke test passed
- [ ] Capstone submitted

---

## Cut-lines (if slipping)

Pull from these in order, *before* compromising eval quality:

1. Drop `/admin/pulse` "Refresh now" button (keep weekly cron only)
2. Drop `core/audit.py` niceties (minimal audit only)
3. Drop Google Sheets API (write bookings to Supabase table instead)
4. Drop Google Calendar API (write holds to Supabase table instead)

Do **not** drop any eval case. Safety must stay 30/30.

---

## How to use this file

- Check boxes inline as work completes: `- [ ]` → `- [x]`.
- Update the progress bar and percentage at the top.
- If a day's scope changes, edit the list directly; this doc is the source of truth.
- Pending items at end of each day roll forward into the next day's log (note the slip in your commit message).
