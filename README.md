# Investor Ops & Intelligence Suite

A capstone fintech-ops platform that combines three milestones into one product:

- **M1 — Smart-Sync RAG Chatbot** (`/user/chatbot`): facts-only Q&A across
  Nippon India fund factsheets and mutual-fund fee/metric explainers, with
  citations and a "Last updated from sources" footer.
- **M2 — Weekly Pulse + Fee Explainer** (`/admin/pulse`): scrapes INDMoney
  Play Store reviews, clusters into top 3 themes, generates a ≤250-word
  pulse with 3 action ideas, and feeds the top themes into the voice agent's
  greeting.
- **M3 — Theme-aware Voice Agent** (`/user/voice`): Vapi-powered booking
  call that opens with the current top theme, walks a scripted flow, and
  triggers a HITL approval queue.
- **Pillar C — Approval Center** (`/admin/approvals`): every post-call
  Calendar hold, Sheets row, and Gmail draft passes through an admin
  approve/reject gate. The user gets exactly one email per booking decision.

Architecture, rules, edge cases, and the day-by-day plan live in `docs/`.
The eval scoring model and per-suite cases live in `evals/`.

## Demo

A 5-minute demo video is recorded as a manual final step (see
`docs/to-do_manually.md`). The recommended demo flow is:

1. Click "Refresh now" on `/admin/pulse` → scrape + pulse generation.
2. Open `/user/voice` → start a Vapi call → confirm the greeting mentions
   the top theme; book a slot; receive an `NL-XXXX` booking code.
3. Open `/user/chatbot` → ask a Smart-Sync question that combines a fund
   value and a fee concept; observe two `Source:` citations.
4. Open `/admin/approvals` → approve calendar + sheets, reject email →
   confirm `notifications_sent` row appears in Supabase.

## Architecture (one-line summary)

Next.js 16 + Supabase Auth (frontend) ↔ FastAPI + Chroma + sentence-transformers
(backend) ↔ Anthropic Claude Sonnet 4.6 + Vapi + Google Calendar/Sheets +
Gmail MCP. Detailed spec at
[`docs/superpowers/specs/2026-04-22-investor-ops-suite-design.md`](./docs/superpowers/specs/2026-04-22-investor-ops-suite-design.md).

## Repo layout

| Path | Contents |
|---|---|
| `frontend/` | Next.js 16 app (proxy.ts auth, glass-card UI, Vapi Web SDK) |
| `backend/` | FastAPI app, services, core (LLM, retriever, PII, MCP, Google APIs) |
| `evals/` | Eval suite (`run_evals.py`), per-suite markdown, source manifest |
| `supabase/migrations/` | One-shot SQL for tables + RLS + auth trigger |
| `.github/workflows/` | Weekly scrape, daily corpus refresh |
| `docs/` | Architecture, Rules, EdgeCases, Evals plan, Plan, Vapi config |

## Getting started (local dev)

### 1. Supabase

Paste `supabase/migrations/0001_init.sql` into the Supabase SQL Editor and run.
Creates 11 tables + RLS + the new-user trigger.

### 2. Backend

```bash
cd backend
cp .env.example .env   # fill keys (see docs/to-do_manually.md for the full list)
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

The first start downloads the all-MiniLM-L6-v2 embedding model (~90MB) and
ingests the 10 source URLs (~110 chunks). Subsequent starts skip ingest if
the index is up-to-date; daily refresh keeps it current.

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local
pnpm install
pnpm dev
```

Visit `http://localhost:3000`. The proxy redirects unauthenticated users to
`/login`.

### 4. Vapi assistant

Upload the system prompt and config from [`docs/Vapi.md`](./docs/Vapi.md) into
the Vapi dashboard, set the server URL header to your backend's
`X-Vapi-Secret`, and copy the assistant ID into the frontend env.

### 5. Run the evals

```bash
USER_JWT=...  ADMIN_JWT=...  VAPI_WEBHOOK_SECRET=... uv run python evals/run_evals.py
```

Writes `evals/eval-report.md`. Target: ≥85/100, Safety must be 30/30.

## What you still need to do by hand

Setting environment variables, uploading the Vapi config, running OAuth
flows, recording the demo, and submitting the capstone are all manual.
Step-by-step instructions live in [`docs/to-do_manually.md`](./docs/to-do_manually.md).

## Deployment

Step-by-step deployment instructions (Hugging Face Spaces backend + Vercel
frontend) live in [`docs/superpowers/plans/2026-05-05-deployment.md`](./docs/superpowers/plans/2026-05-05-deployment.md).

## Docs index

- [Architecture spec](./docs/superpowers/specs/2026-04-22-investor-ops-suite-design.md)
- [Rules](./docs/Rules.md)
- [Edge cases](./docs/EdgeCases.md)
- [Eval plan](./docs/Evals.md)
- [Vapi assistant config](./docs/Vapi.md)
- [7-day implementation plan](./docs/Plan.md)
- [Manual to-dos](./docs/to-do_manually.md)
- [Deployment plan](./docs/superpowers/plans/2026-05-05-deployment.md)
