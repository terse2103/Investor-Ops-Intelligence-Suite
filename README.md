# Investor Ops & Intelligence Suite

Capstone project that integrates three milestones (M1 RAG chatbot, M2 review analyst, M3 voice agent) into a unified fintech ops suite for INDMoney, with a HITL approval center gating all post-call Google/MCP actions.

See [`docs/`](./docs) for the architecture spec, product rules, edge cases, eval plan, and day-by-day plan.

## Structure

- `frontend/` — Next.js 16 + TypeScript + Tailwind (deploys to Vercel)
- `backend/` — FastAPI + Python 3.11+ (deploys to Render)
- `evals/` — Offline eval suite, outputs `evals/eval-report.md`
- `supabase/migrations/` — SQL migrations for Postgres + RLS
- `.github/workflows/` — Weekly scrape cron
- `docs/` — Architecture spec, Rules, EdgeCases, Evals, Plan

## Getting started (local dev)

### 1. Supabase

Paste `supabase/migrations/0001_init.sql` into the Supabase SQL Editor and run. Creates 11 tables + RLS + the new-user trigger.

### 2. Backend

```bash
cd backend
cp .env.example .env   # fill in Anthropic, Supabase, Vapi keys
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local   # fill in Supabase + backend URL + Vapi public key
pnpm install
pnpm dev
```

Visit `http://localhost:3000`.

## Docs index

- [Architecture spec](./docs/superpowers/specs/2026-04-22-investor-ops-suite-design.md)
- [Rules](./docs/Rules.md)
- [EdgeCases](./docs/EdgeCases.md)
- [Evals plan](./docs/Evals.md)
- [7-day implementation plan](./docs/Plan.md)
