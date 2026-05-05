---
title: Investor Ops Suite Backend
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Investor Ops Suite: Backend

FastAPI service powering the 3-pillar investor operations suite (RAG + Pulse + Voice).
See the project root README for the full overview.

## Local development

```bash
cd backend
cp .env.example .env   # fill in secrets
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Deployment

This directory is the deployable unit for a Hugging Face Space (Docker SDK).
Deployment steps live in `docs/to-do_manually.md` and the full runbook is in
`docs/superpowers/plans/2026-05-05-deployment.md`.
