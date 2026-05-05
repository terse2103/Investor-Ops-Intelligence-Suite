# Investor Ops & Intelligence Suite — High-Level Architecture

**Date:** 2026-04-22
**Status:** Approved (high-level); details deferred to future iterations
**Source docs:** `docs/ProblemStatement.md`, `docs/milestones/M1/M1_PS.md`, `docs/milestones/M2/M2_PS.md`, `docs/milestones/M3/M3_PS.md`

> **Note (2026-05-05):** Deploy host was switched from Render to Hugging Face Spaces during execution. The tech choices table (§3) has been updated. Current deployment steps are documented in `docs/superpowers/plans/2026-05-05-deployment.md`.

## 1. Purpose

Build a unified Fintech product operations suite for INDMoney that integrates three milestone capabilities into a single product:

- **M1 — RAG Chatbot:** facts-only Q&A on INDMoney mutual funds with source citations.
- **M2 — Review Analyst:** Weekly Product Pulse from scraped Play Store reviews, plus a structured Fee Explainer.
- **M3 — Voice Agent:** compliant advisor-appointment booking voice agent with HITL approval gates on post-call API & MCP actions.

The suite enforces three product-level integrations across these milestones:

- **Pillar A — Smart-Sync KB (M1 + M2):** unified search that can answer questions blending MF facts and fee logic.
- **Pillar B — Theme-aware voice (M2 → M3):** voice agent greets callers with the current top 3 review themes.
- **Pillar C — HITL Approval Center (M3 + M2):** post-call Calendar/Sheets/Email actions are queued for admin approval, with Market Context from the latest Pulse injected into the email draft.

## 2. Mode and Optimization Target

**Hybrid**: optimize for a polished capstone demo, but with clean service boundaries so components could later be lifted toward production without a rewrite. The five-minute demo video is the primary deliverable; architecture choices favor demo reliability over scale.

## 3. Technology Choices (locked)

| Area | Choice | Rationale |
|---|---|---|
| Frontend | Next.js (React + TypeScript) on Vercel | Real auth UX, WebSocket support for live approvals, Vapi Web SDK embedding |
| Backend | FastAPI (Python 3.11+), deployed on Hugging Face Spaces (Docker SDK, free CPU basic) | Native fit for LLM/RAG/evals work in Python; free without a credit card; 16GB RAM fits torch + sentence-transformers |
| Repo layout | Flat single monorepo: `/frontend`, `/backend`, `/evals`, `/docs`, `/.github` | Simplest possible; atomic full-stack commits; single GitHub URL for submission |
| RAG stack | Claude Sonnet 4.6 (LLM, with prompt caching) + HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (local, 384-dim embeddings) + Chroma (local, file-backed vector store) | No embedding/vector-DB API keys needed; fully local except for Claude calls; retriever interface keeps migration to pgvector a small change later |
| Database + Auth | Supabase (Postgres + Auth with RLS + Storage) | One provider for DB, auth, role separation, and file storage; keeps pgvector door open |
| Voice agent | Vapi (hosted), Web SDK only | Embedded call widget in the Next.js app; real phone dispatch is out of scope (see Section 10) |
| User notifications | Transactional email only (provider deferred) | On admin approve/reject of a booking, the user receives one email confirming the outcome; SMS is out of scope |
| Google APIs + MCP | Google Calendar API + Google Sheets API (direct), and Gmail via real MCP protocol; all three invoked only after HITL approval | Matches revised M3 spec: email draft goes through Gmail MCP; Calendar and Sheets use direct Google APIs |
| Review ingestion | `google-play-scraper` (Python) inside FastAPI | Matches actual ingestion pattern: scrape, not upload |
| Scrape scheduling | Manual "Refresh now" admin button **and** weekly GitHub Actions cron hitting the same endpoint | Keeps FastAPI scheduler-free; guarantees weekly rhythm plus on-demand demo trigger |
| Evals | Offline Python script + markdown deliverable, not a live service | Evals are a graded artifact, not a product feature |

## 4. Deferred Decisions (to be resolved in a later iteration)

1. Table schemas (columns, indexes, RLS policies).
2. Prompt templates per service.
3. Evals golden dataset contents and rubric thresholds.
4. Gmail MCP server selection (self-hosted vs community) and Google OAuth setup covering Calendar API, Sheets API, and Gmail MCP scopes together.
5. ~~Deployment specifics: secrets management, domains, CI.~~ Resolved: HF Spaces backend, Vercel frontend. See `docs/superpowers/plans/2026-05-05-deployment.md`.
6. Error handling policies, retry strategy, observability.
7. Email notification provider (Resend vs SendGrid vs Supabase SMTP vs other).

## 5. System Topology

```
┌─────────────────────────── Browser ───────────────────────────┐
│  Next.js App (Vercel)                                          │
│  /login  /user/chatbot  /user/voice  /user/settings            │
│  /admin/pulse  /admin/approvals                                │
│         │                        │                             │
│         │ Supabase Auth SDK      │ Vapi Web SDK                │
└─────────┼────────────────────────┼─────────────────────────────┘
          │                        │
          ▼                        ▼
┌──── Supabase ────┐      ┌── Vapi (hosted) ──┐
│  Postgres        │      │ Voice Agent        │
│  Auth + RLS      │      │ Web SDK only       │
│  Storage         │      │ STT/TTS/turns      │
└────────┬─────────┘      └────────┬───────────┘
         ▲                         │ post-call webhook
         │                         ▼
         │      ┌───────────── FastAPI Backend ───────────────────┐
         │      │  services/rag   services/pulse   services/voice │
         └──────┤                                                 │
                │  core: llm, retriever, mcp_client, google_api, │
                │        notifier, pii, audit                     │
                └──────────────────┬──────────────────────────────┘
                                   │
              ┌─────────────┬──────┴──────┬──────────────────┐
              ▼             ▼             ▼                  ▼
        ┌ Google APIs ┐  ┌ MCP Server ┐  ┌ Email Provider ┐
        │ Calendar    │  │ Gmail      │  │   (deferred)   │
        │ Sheets      │  └────────────┘  └────────────────┘
        └─────────────┘

GitHub Actions (weekly cron) ──POST──► FastAPI /api/scrape
```

## 6. Component Responsibilities

### 6.1 Next.js Frontend

Six routes, two roles:

- `/login` — Supabase Auth sign-in (email/password or OAuth).
- `/user/chatbot` — Pillar A surface. Chat UI calling `/api/rag/query`.
- `/user/voice` — Pillar B + C surface. Embeds Vapi Web SDK; shows call transcript and booking code after completion.
- `/user/settings` — User saves a notification email address used by the notifier when their bookings are approved or rejected.
- `/admin/pulse` — Admin view of reviews, "Refresh now" button, generated pulses, current top themes.
- `/admin/approvals` — Admin view of `pending_actions` queue; approve/reject triggers downstream API (Calendar, Sheets) or MCP (Gmail) execution plus a user notification.

Role gating via Supabase RLS plus Next.js middleware. The frontend never writes to `calls`, `pending_actions`, or executes Google APIs or MCP directly.

### 6.2 FastAPI Backend

One app, three service modules plus a shared core:

```
app/
├── services/
│   ├── rag/       # Pillar A (bootstrap, corpus, ingest, query)
│   ├── pulse/     # Pillar B (scraper + pulse generation)
│   ├── voice/     # Pillar C (context + post_call)
│   └── approvals/ # HITL dispatcher
├── core/
│   ├── llm.py            # Claude Sonnet 4.6 client (adaptive thinking + prompt caching)
│   ├── retriever.py      # Chroma + all-MiniLM-L6-v2 retriever
│   ├── mcp_client.py     # MCP protocol client (Gmail only)
│   ├── google_api.py     # Google Calendar + Sheets API clients
│   ├── notifier.py       # Transactional email dispatch (Resend)
│   ├── pii.py            # PII guard (regex-based)
│   ├── audit.py          # Audit logging (scrape_runs, action_audit, notifications_sent)
│   ├── auth.py           # Supabase JWT auth dependency
│   ├── email_template.py # HTML email renderer for booking notifications
│   └── limiter.py        # Rate limiting (slowapi)
├── api/                  # Routers: health, rag, pulse, scrape, voice, approvals, settings
└── config.py             # pydantic-settings env loader
```

Service modules do not import each other; they share only through `core/`. This preserves the option of splitting into separate deployables later.

### 6.3 Supabase

Hosts Postgres (app data), Auth (users and roles), Storage (uploaded corpus files), and RLS policies that enforce user-vs-admin separation.

### 6.4 Vapi

Hosted voice agent configured with M3's scripted flow (greet → disclaimer → topic → time → offer two slots → confirm). Served via the **Vapi Web SDK only**, embedded in `/user/voice`; the caller is always the logged-in user, so no caller-ID allow-list is needed. Both in-call tool calls and the post-call webhook target FastAPI. In-call tool calls are read-only (e.g., checking slot availability); all write operations and MCP executions happen only via the post-call path through the HITL approval gate. No audio traffic touches FastAPI. Real phone dispatch is out of scope (Section 10).

### 6.5 Gmail MCP Server

Real Gmail MCP server for drafting advisor emails. Invoked by `core/mcp_client.py` only after an admin approves a pending email action. Never invoked during a live call.

### 6.6 Google APIs (Calendar + Sheets)

Google Calendar API creates tentative advisor holds; Google Sheets API appends booking rows to the "Advisor Pre-Bookings" sheet. Invoked by `core/google_api.py` only after an admin approves the corresponding pending action. Shares the Google OAuth credential set used by the Gmail MCP server.

### 6.7 Notifications

`core/notifier.py` sends one transactional email to the booking's user when the admin finalizes the approval decision for that booking. Email provider is deferred. The notifier reads the target email from `user_contacts`, formats a short templated message (approved vs rejected + booking code + advisor email subject if approved), dispatches, and writes a `notifications_sent` audit row. Failures to send are logged but do not block the MCP/API execution path.

### 6.8 Scraper

`services/pulse/scraper.py` uses `google-play-scraper` to pull INDMoney reviews from Google Play, normalizes them, and writes to `reviews` with dedup on the Play review ID. Triggered by POST `/api/scrape` from either the admin "Refresh now" button or the GitHub Actions weekly cron.

### 6.9 Evals (offline)

```
evals/
├── rag-eval.md          # 5 M1+M2 retrieval test cases (golden dataset)
├── safety-eval.md       # 3 adversarial refusal cases (constraint adherence)
├── ux-eval.md           # Pulse structure rubric + voice theme-mention logic check
├── run_evals.py         # Hits live endpoints, writes scores
├── eval-report.md       # Submitted deliverable
└── source-manifest.md   # 30+ official URLs used across the project
```

Not part of the running FastAPI app. Run manually before demo recording and submission.

## 7. Data Model (tables only; schemas deferred)

- `profiles` — Role-bearing extension of `auth.users` (id, role ∈ {user, admin}). Auto-created on signup via trigger.
- `user_contacts` — User-provided notification email address used by the notifier. Auto-populated from `auth.users.email` via `0002_auto_user_contacts.sql`.
- `sources` — M1 + M2 corpus (INDMoney pages, fee scenario webpages).
- `reviews` — Scraped Play Store reviews, deduped on `play_review_id`.
- `scrape_runs` — Audit row per scrape (timestamp, count, `filtered_out_count`, trigger source).
- `pulses` — Generated weekly pulses (themes, quotes, actions, note_text, word_count).
- `current_themes` — Singleton cache of top 3 themes for Vapi agent injection.
- `calls` — Vapi call metadata (id, user_id, intent, transcript, booking_code, status ∈ {in_progress, completed, abandoned}).
- `pending_actions` — HITL queue (type ∈ {calendar, sheets, email}, payload, status ∈ {pending, approved, rejected, executed, failed}).
- `action_audit` — Post-approval execution results for both API (Calendar, Sheets) and MCP (Gmail) actions.
- `notifications_sent` — Audit row per email dispatch (user, call_id, status ∈ {sent, bounced, provider_error, skipped_no_contact}, provider_response).

## 8. Core Flows

### Pillar A — Smart-Sync KB

```
User query → /api/rag/query
  → retriever (unified M1+M2 index)
  → LLM composes answer (6-bullet + citations)
  → PII guard on output
  → response
```

### Pillar B — Theme-aware Voice

```
Trigger (GitHub Actions cron OR admin "Refresh now")
  → /api/scrape → google-play-scraper → reviews table
  → /api/pulse/generate
  → LLM clusters 5 themes, picks top 3, extracts 3 quotes,
    writes ≤250-word pulse + 3 action ideas
  → pulses + current_themes updated

Vapi call start (Web SDK):
  → FastAPI injects current_themes into Vapi dynamic variables
  → agent greets with theme-aware opening line
```

### Pillar C — HITL Approval Center

```
Vapi call end → webhook /api/voice/post-call
  → voice service writes 3 pending_actions:
    • calendar hold   (type=calendar,  executes via Google Calendar API)
    • sheets entry    (type=sheets,    executes via Google Sheets API)
    • email draft     (type=email,     executes via Gmail MCP;
                       Market Context from latest pulse injected)
  → admin reviews /admin/approvals
  → on approve → core dispatches by action type:
      calendar / sheets → google_api.py
      email             → mcp_client.py (Gmail MCP)
  → action_audit row recorded
  → on final decision for the booking:
      notifier.py → sends email to the user (from user_contacts)
      → notifications_sent audit row
```

## 9. Cross-Cutting Concerns

### 9.1 PII Guard

A `core/pii.py` middleware runs on:

- Every LLM input before prompting.
- Every LLM output before storing or returning.
- Every inbound webhook payload (Vapi transcripts).

Detects PAN, Aadhaar, phone, email, account numbers; replaces with `[REDACTED]`. Applied uniformly to all services.

### 9.2 Auth and Role Separation

Supabase Auth with RLS. `role=admin` required for:

- Any `/admin/*` frontend route (enforced by Next.js middleware).
- Any FastAPI endpoint that reads or mutates `pending_actions`, `reviews`, `pulses`.
- Any direct Supabase query for admin-only tables (enforced by RLS).

### 9.3 Single Write Path for Call/Action State

`calls`, `pending_actions`, `action_audit`, and `notifications_sent` are mutated only by FastAPI (triggered by Vapi webhooks or admin approval actions). The frontend reads these tables but never writes to them. The frontend *does* write to `user_contacts` via `/user/settings`, since those are self-service user records.

### 9.4 Audit Logging

`core/audit.py` writes to `scrape_runs`, `action_audit` (covering both API and MCP executions), `notifications_sent`, and eval-run metadata. Provides the paper trail needed for the demo and any compliance story.

### 9.5 User Contact Handling

User-supplied `email` in `user_contacts` is product data, not PII-in-transit. It is:

- Never injected into LLM prompts, Vapi dynamic variables, or stored call transcripts.
- Accessed only by `core/notifier.py` (for dispatch).
- Still run through the PII guard if it ever appears in an LLM input/output or transcript. PII guard remains a safety net, not a primary defense against deliberate user-provided contact info.

## 10. Out of Scope

- Real phone-dispatch telephony for the voice agent (Web SDK only; no provisioned Vapi phone number, no caller-ID allow-list, no inbound PSTN calls). Dropped for 7-day timeline.
- SMS notifications (email only). Dropped for 7-day timeline.
- Phone-number storage and OTP verification. Dropped because phone is no longer needed without phone dispatch or SMS.
- Multi-tenant support (single INDMoney corpus; single advisor; admins and users are roles, not tenants).
- Performance optimization beyond demo-scale traffic.
- A11y beyond default framework behavior.
- Mobile-specific UX (responsive is fine; native apps are not in scope).

## 11. Open Questions (status as of 2026-05-05)

1. ~~Which RAG stack?~~ **Resolved:** Claude Sonnet 4.6 (Anthropic, adaptive thinking + prompt caching) + `sentence-transformers/all-MiniLM-L6-v2` (local, 384-dim) + ChromaDB (in-process, file-backed).
2. ~~Which Gmail MCP server?~~ **Resolved:** Community MCP server via `GMAIL_MCP_COMMAND` env var. Google Calendar + Sheets use a service account; Gmail MCP uses its own OAuth. See `docs/to-do_manually.md` §5-6.
3. ~~Eval scoring rubric?~~ **Resolved:** 100 points: RAG=40, Safety=30, UX=30. Target ≥85. See `docs/Evals.md`.
4. ~~What goes into Rules/EdgeCases/Evals?~~ **Resolved:** All three are fully written. See `docs/Rules.md`, `docs/EdgeCases.md`, `docs/Evals.md`.
5. ~~Which advisors are bookable?~~ **Resolved:** Single advisor inbox configured via `ADVISOR_EMAIL` env var. Demo uses a test email.
6. ~~Demo data set?~~ **Resolved:** Nippon India mutual fund schemes (5-10 pages from INDMoney). Fee scenarios are INDMoney fee/metric explainer pages. Corpus is defined in `backend/app/services/rag/corpus.py`.
7. ~~Admin notifications?~~ **Not implemented.** Admin relies on the Approval Center UI. Out of scope per Section 10.
