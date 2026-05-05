# Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the Investor Ops Suite to free-tier hosting: Next.js frontend on Vercel, FastAPI backend on Hugging Face Spaces (Docker SDK), with GitHub Actions cron pointing at the live backend.

**Architecture:** Backend ships as a Docker image to a Hugging Face Space (free CPU basic, 16GB RAM, fits `torch` + `sentence-transformers` comfortably). Frontend deploys via Vercel's GitHub integration. Supabase, Vapi, Anthropic, Resend, Google APIs stay external (already configured per `docs/to-do_manually.md`). CORS is widened to accept Vercel preview-deploy URLs via a regex env var. ChromaDB stays in-process; the existing lifespan handler in `backend/app/main.py:21-50` re-ingests on cold start (already designed for ephemeral disk).

**Tech Stack:** Docker, Hugging Face Spaces, Vercel, GitHub Actions, FastAPI, Next.js 16, uv, Supabase.

---

## Decisions locked in (do not revisit during execution)

- Backend host: **Hugging Face Spaces** (Docker SDK, free CPU basic).
- Frontend host: **Vercel Hobby**.
- Vector DB: **ChromaDB in-process** (no persistent disk; rely on lifespan re-ingest).
- Embedding model: **`sentence-transformers/all-MiniLM-L6-v2`**, baked into the Docker image at build time so cold starts skip the download.
- Deploy mechanism for HF Spaces: **`git subtree push`** of `backend/` from the main repo. No GitHub Action sync (out of scope).
- CORS: production origin via `FRONTEND_URL`, preview origins via `FRONTEND_ORIGIN_REGEX`.
- All external service provisioning is assumed done per `docs/to-do_manually.md` Sections 1, 2, 4, 5, 6. This plan covers Sections 3, 7 from a deployment perspective only.

---

## File map

### New files
- `backend/Dockerfile` — Docker image definition for HF Spaces
- `backend/.dockerignore` — exclude dev cruft from build context

### Modified files
- `backend/README.md` — add HF Spaces YAML frontmatter (currently empty)
- `backend/app/config.py:18` — add `frontend_origin_regex` setting
- `backend/app/main.py:63-69` — pass `allow_origin_regex` to CORS middleware
- `backend/.env.example:13` — document `FRONTEND_ORIGIN_REGEX`
- `docs/to-do_manually.md:21,49-86` — replace Render row with HF Spaces; update env-var section

### Files NOT touched (intentionally)
- `frontend/next.config.ts` — Vercel auto-detects; no config needed
- `frontend/vercel.json` — not created; auto-detect is sufficient
- `.github/workflows/*.yml` — already use `secrets.BACKEND_URL`; only the secret value changes

---

## Task 1: Add backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1.1: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

# System deps for compiled wheels (lxml, chromadb)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (pinned version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

# HF Spaces runs containers as a non-root user with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/user/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/user/.cache/sentence-transformers

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY --chown=user:user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Pre-download the embedding model into the image so cold starts skip the download
RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application code last (changes most often)
COPY --chown=user:user . .

EXPOSE 7860

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

- [ ] **Step 1.2: Verify the Dockerfile builds locally**

Run from the repo root:

```bash
docker build -t investor-ops-backend ./backend
```

Expected: build succeeds. Watch for the `sentence-transformers` model download line near the end of the `uv run python -c` step. Total build time on first run: 5-10 minutes.

If Docker is not installed locally, skip this verification; the HF Spaces builder will run the same Dockerfile.

- [ ] **Step 1.3: Smoke-test the container locally (optional, only if Docker is available)**

```bash
docker run --rm -p 7860:7860 -e SUPABASE_URL=http://placeholder -e ANTHROPIC_API_KEY=sk-placeholder investor-ops-backend
```

In a separate terminal:

```bash
curl -f http://localhost:7860/health
```

Expected output: `{"status":"ok"}`. Stop the container with Ctrl-C.

The startup ingest in the lifespan handler will fail with the placeholder Anthropic key. That is expected for the smoke test; the lifespan exception is caught at `backend/app/main.py:48-49` and the service still starts.

---

## Task 2: Add backend `.dockerignore`

**Files:**
- Create: `backend/.dockerignore`

- [ ] **Step 2.1: Create `backend/.dockerignore`**

```
# Python
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Local env files (use HF Space secrets, not files)
.env
.env.*
!.env.example

# Local data
chroma_data/
*.sqlite
*.db
*.log

# Tests (not needed in runtime image)
tests/

# Editor / OS
.idea/
.vscode/
.DS_Store

# Git
.git/
.gitignore
```

- [ ] **Step 2.2: Rebuild to confirm context shrunk**

```bash
docker build -t investor-ops-backend ./backend 2>&1 | head -5
```

Expected first line: `Sending build context to Docker daemon ...` with a context size measured in MB, not GB. (If the `chroma_data/` folder exists locally, the `.dockerignore` excludes it.)

---

## Task 3: Add HF Spaces frontmatter to `backend/README.md`

**Files:**
- Modify: `backend/README.md` (currently empty)

- [ ] **Step 3.1: Replace `backend/README.md` with HF-compatible content**

```markdown
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
Deployment steps live in `docs/to-do_manually.md`.
```

- [ ] **Step 3.2: Verify the frontmatter is valid YAML**

```bash
head -10 backend/README.md
```

Expected: the first line is `---`, followed by `title:`, `emoji:`, etc., and a closing `---`. The `sdk: docker` and `app_port: 7860` lines must be exact.

---

## Task 4: Widen CORS for Vercel preview deploys

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/.env.example`

- [ ] **Step 4.1: Add `frontend_origin_regex` to `Settings`**

In `backend/app/config.py`, add this field after `frontend_url` (around line 17):

```python
    frontend_url: str = "http://localhost:3000"
    frontend_origin_regex: str = ""
```

- [ ] **Step 4.2: Pass the regex to the CORS middleware**

In `backend/app/main.py`, replace the existing `app.add_middleware(CORSMiddleware, ...)` block (lines 63-69) with:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_origin_regex=settings.frontend_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 4.3: Document the new env var in `.env.example`**

In `backend/.env.example`, replace the CORS section (around line 11-12) with:

```
# --- CORS / frontend URL ---
FRONTEND_URL=http://localhost:3000
# Optional regex matched against the Origin header for additional allowed origins.
# Use to allow Vercel preview deploys, e.g.:
#   FRONTEND_ORIGIN_REGEX=https://[a-z0-9-]+-<vercel-scope>\.vercel\.app
FRONTEND_ORIGIN_REGEX=
```

- [ ] **Step 4.4: Run the existing test suite to confirm no regression**

```bash
cd backend
uv run pytest -q
```

Expected: all tests pass. The CORS change is config-only; nothing should break.

- [ ] **Step 4.5: Commit Tasks 1-4 together**

```bash
git add backend/Dockerfile backend/.dockerignore backend/README.md backend/app/config.py backend/app/main.py backend/.env.example
git commit -m "feat(deploy): add Dockerfile + HF Spaces frontmatter + CORS regex"
```

---

## Task 5: Verify external prerequisites

This task is a checklist, not code. Each item must be `done` before Task 6.

- [ ] **Step 5.1: Supabase ready**
  - Project created
  - Both migrations run: `supabase/migrations/0001_init.sql` and `supabase/migrations/0002_auto_user_contacts.sql`
  - At least one regular user and one admin user (with `app_metadata.role='admin'`)
  - You have: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

- [ ] **Step 5.2: Anthropic key in hand** (`sk-ant-...`)

- [ ] **Step 5.3: Vapi configured** per `docs/to-do_manually.md` Section 4
  - `VAPI_API_KEY`, `VAPI_PUBLIC_KEY`, `VAPI_ASSISTANT_ID`, `VAPI_WEBHOOK_SECRET` in hand
  - Assistant `Server URL` field is left blank for now (filled in Task 9)

- [ ] **Step 5.4: Google APIs configured** per `docs/to-do_manually.md` Section 5
  - `GOOGLE_SA_JSON` (inline JSON), `GOOGLE_CALENDAR_ID`, `GOOGLE_SHEETS_ID` in hand

- [ ] **Step 5.5: Resend configured**
  - `RESEND_API_KEY`, `EMAIL_FROM` (verified sender) in hand

- [ ] **Step 5.6: Generate two random 32-char secrets**

```bash
python -c "import secrets; print(secrets.token_urlsafe(24))"   # SCRAPE_SHARED_SECRET
python -c "import secrets; print(secrets.token_urlsafe(24))"   # CORPUS_REFRESH_SECRET
```

Save both values for use in Tasks 7 and 10.

- [ ] **Step 5.7: GitHub repo pushed and accessible**

```bash
git push origin main
```

Expected: `main` is up-to-date on the remote.

---

## Task 6: Create the Hugging Face Space

This task uses the HF web UI, then the HF git remote.

- [ ] **Step 6.1: Create an HF account and access token**
  - Sign up at https://huggingface.co/join (free)
  - Go to Settings → Access Tokens → "Create new token"
  - Token type: `write`. Name it `investor-ops-deploy`. Save the token string.

- [ ] **Step 6.2: Create a new Space**
  - Go to https://huggingface.co/new-space
  - Owner: your username
  - Space name: `investor-ops-backend` (this becomes part of the URL)
  - License: `mit`
  - Space SDK: **Docker** → "Blank"
  - Space hardware: `CPU basic - 2 vCPU - 16 GB - FREE`
  - Visibility: `Public` (private requires Pro)
  - Click "Create Space"

- [ ] **Step 6.3: Copy the Space URL**

After creation, the Space URL has the form:
- App URL: `https://<USER>-investor-ops-backend.hf.space`
- Git URL: `https://huggingface.co/spaces/<USER>/investor-ops-backend`

Save both. The app URL is what the frontend, GitHub Actions, and Vapi all point at.

---

## Task 7: Set Space secrets (env vars)

The HF Space UI calls these "Repository secrets". They map 1:1 to env vars at runtime.

- [ ] **Step 7.1: Open Space settings**

Go to `https://huggingface.co/spaces/<USER>/investor-ops-backend/settings`. Scroll to "Variables and secrets".

- [ ] **Step 7.2: Add each secret**

Click "New secret" for each row below. Use the values gathered in Task 5.

| Name | Value source |
|---|---|
| `ANTHROPIC_API_KEY` | Step 5.2 |
| `SUPABASE_URL` | Step 5.1 |
| `SUPABASE_SERVICE_ROLE_KEY` | Step 5.1 |
| `VAPI_API_KEY` | Step 5.3 |
| `VAPI_PUBLIC_KEY` | Step 5.3 |
| `VAPI_ASSISTANT_ID` | Step 5.3 |
| `VAPI_WEBHOOK_SECRET` | Step 5.3 |
| `SCRAPE_SHARED_SECRET` | Step 5.6 |
| `CORPUS_REFRESH_SECRET` | Step 5.6 |
| `RESEND_API_KEY` | Step 5.5 |
| `EMAIL_FROM` | Step 5.5 |
| `GOOGLE_SA_JSON` | Step 5.4 (paste the entire JSON inline) |
| `GOOGLE_CALENDAR_ID` | Step 5.4 |
| `GOOGLE_SHEETS_ID` | Step 5.4 |
| `GOOGLE_SHEETS_RANGE` | `Bookings!A:F` |
| `GMAIL_MCP_COMMAND` | (leave blank for the cut-line; see `docs/to-do_manually.md` Section 6) |
| `ADVISOR_EMAIL` | your advisor inbox or leave blank |

`FRONTEND_URL` and `FRONTEND_ORIGIN_REGEX` are set in Task 9 (after Vercel deploy gives you the URLs).

- [ ] **Step 7.3: Confirm "Variables" tab is empty, "Secrets" tab has all rows above**

The HF UI separates "Variables" (visible) from "Secrets" (encrypted). Everything in this app goes in Secrets.

---

## Task 8: Push the backend to the Space

- [ ] **Step 8.1: Add the HF Space as a git remote**

From the repo root:

```bash
git remote add hfspace https://huggingface.co/spaces/<USER>/investor-ops-backend
```

- [ ] **Step 8.2: Authenticate to HF git**

Configure git to use the access token from Step 6.1:

```bash
git config credential.https://huggingface.co.username <USER>
```

When prompted for a password during the next push, paste the token (not your HF account password).

- [ ] **Step 8.3: Subtree-push `backend/` as the Space's `main` branch**

```bash
git subtree push --prefix=backend hfspace main
```

If this fails because the Space already has a commit (HF auto-creates an initial commit), force-set the branch:

```bash
git push hfspace `git subtree split --prefix=backend main`:main --force
```

Expected: HF starts a Docker build immediately. The Space page status flips to `Building`.

- [ ] **Step 8.4: Watch the build logs**

In the Space page, click "Logs" → "Build". The build takes 6-12 minutes on first run (downloads torch and pre-downloads the embedding model). Subsequent pushes use cached layers and take 1-3 minutes.

Expected end-of-log: `Successfully built ...` followed by container start, then logs from uvicorn: `Uvicorn running on http://0.0.0.0:7860`.

- [ ] **Step 8.5: Smoke-test the deployed backend**

```bash
curl -fsS https://<USER>-investor-ops-backend.hf.space/health
```

Expected: `{"status":"ok"}`. If you get HTML back, the Space is still building or sleeping; wait 30s and retry.

If the response is a 503 or hangs, open the Space's "Logs" → "Container" tab and look for the lifespan-handler exception or an OOM. Likely culprit: a missing secret (re-check Task 7).

---

## Task 9: Deploy frontend to Vercel

- [ ] **Step 9.1: Sign in to Vercel with GitHub**

Go to https://vercel.com/new. Click "Import Git Repository" and authorize Vercel for the GitHub account that owns this repo.

- [ ] **Step 9.2: Import the repo**

Select the repo. On the "Configure Project" screen:
- Framework Preset: **Next.js** (auto-detected)
- Root Directory: click "Edit" → set to `frontend`
- Build/Output settings: leave as defaults (Vercel reads `frontend/package.json`)
- Node version: leave as default (20.x)

- [ ] **Step 9.3: Add environment variables (before first deploy)**

Click "Environment Variables" on the same screen. Add each:

| Name | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | from Step 5.1 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | from Step 5.1 (anon key, NOT service role) |
| `NEXT_PUBLIC_BACKEND_URL` | `https://<USER>-investor-ops-backend.hf.space` (from Task 6.3) |
| `NEXT_PUBLIC_VAPI_PUBLIC_KEY` | from Step 5.3 |
| `NEXT_PUBLIC_VAPI_ASSISTANT_ID` | from Step 5.3 |

Apply each to all three environments (Production, Preview, Development).

- [ ] **Step 9.4: Click "Deploy"**

Build takes 1-2 minutes. When done, Vercel shows a production URL: `https://<project>.vercel.app`.

- [ ] **Step 9.5: Smoke-test the frontend**

Open `https://<project>.vercel.app` in a browser. The login page should render. Do NOT try to log in yet (CORS not wired).

---

## Task 10: Wire CORS and finish backend env

The frontend now exists; back-fill its URL into the backend.

- [ ] **Step 10.1: In HF Space settings, add CORS-related secrets**

Add these two secrets in `Variables and secrets`:

| Name | Value |
|---|---|
| `FRONTEND_URL` | `https://<project>.vercel.app` (from Step 9.4) |
| `FRONTEND_ORIGIN_REGEX` | `^https://[a-z0-9-]+-<vercel-scope>\.vercel\.app$` (replace `<vercel-scope>` with your team/user slug; copy from any preview URL) |

If you don't need preview-deploy CORS for the demo, leave `FRONTEND_ORIGIN_REGEX` blank.

- [ ] **Step 10.2: Restart the Space**

In the Space UI: "Settings" → "Factory rebuild" is overkill. Use "Restart this Space" instead (Settings → "Restart" button). Restart picks up the new env vars without rebuilding the image.

- [ ] **Step 10.3: Re-run the health check**

```bash
curl -fsS -H "Origin: https://<project>.vercel.app" -i https://<USER>-investor-ops-backend.hf.space/health | grep -i access-control-allow-origin
```

Expected: a header `access-control-allow-origin: https://<project>.vercel.app`.

- [ ] **Step 10.4: Browser end-to-end check**

In an incognito window, log into `https://<project>.vercel.app` with a regular Supabase test user. Verify:
- Login succeeds
- `/user/chatbot` page loads and a question round-trips to the backend
- DevTools → Network: the call to `<HF Space URL>/api/rag/query` returns 200 with no CORS error in the console

If CORS errors appear, double-check `FRONTEND_URL` exact match (no trailing slash) and re-restart the Space.

---

## Task 11: Wire GitHub Actions cron secrets ~~(DROPPED)~~

> **DROPPED 2026-05-05:** No cron jobs needed for this deploy. The two workflows (`weekly-scrape.yml`, `daily-corpus-refresh.yml`) were disabled in the GitHub Actions UI; the duplicate `scrape.yml` was deleted. Steps below preserved for reference if cron is ever re-enabled.

`.github/workflows/weekly-scrape.yml` and `.github/workflows/daily-corpus-refresh.yml` already reference `${{ secrets.BACKEND_URL }}`. Just supply the secret values.

- [ ] **Step 11.1: Open repo settings → Secrets and variables → Actions**

URL: `https://github.com/<owner>/<repo>/settings/secrets/actions`

- [ ] **Step 11.2: Add three repository secrets**

| Name | Value |
|---|---|
| `BACKEND_URL` | `https://<USER>-investor-ops-backend.hf.space` |
| `SCRAPE_SHARED_SECRET` | same value as the HF Space secret from Step 5.6 |
| `CORPUS_REFRESH_SECRET` | same value as the HF Space secret from Step 5.6 |

- [ ] **Step 11.3: Manually trigger the weekly scrape workflow to verify**

GitHub UI → Actions → "Weekly Review Scrape" → "Run workflow" → "Run".

Expected: the run goes green within ~30s. In Supabase, a new `scrape_runs` row appears with `status='ok'`.

- [ ] **Step 11.4: Manually trigger the daily corpus refresh**

GitHub UI → Actions → "Daily corpus refresh" → "Run workflow" → "Run".

Expected: green within 1-3 minutes (the endpoint re-ingests M1 + M2 sources). On HF Space "Logs", you'll see the ingest progress.

---

## Task 12: Update Vapi server URL

The Vapi assistant's post-call webhook now points at the deployed backend.

- [ ] **Step 12.1: Vapi dashboard → your assistant → "Server" tab**

- Server URL: `https://<USER>-investor-ops-backend.hf.space/api/voice/post-call`
- Custom Headers → Add: `X-Vapi-Secret: <VAPI_WEBHOOK_SECRET from Step 5.3>`

Save. Vapi will call this endpoint after each completed call.

- [ ] **Step 12.2: Confirm the assistant ID matches both env vars**

The same `VAPI_ASSISTANT_ID` value must be set in:
- HF Space secret `VAPI_ASSISTANT_ID` (Step 7.2)
- Vercel env `NEXT_PUBLIC_VAPI_ASSISTANT_ID` (Step 9.3)

Mismatch causes the frontend to start a session against the wrong assistant.

---

## Task 13: Full smoke test against deployed services

This is the same checklist from `docs/to-do_manually.md` Section 7, run against the live URLs.

- [ ] **Step 13.1: Health**

```bash
curl -f https://<USER>-investor-ops-backend.hf.space/health
```
Expected: `{"status":"ok"}`.

- [ ] **Step 13.2: RAG query (browser)**

Log in as a regular user on `https://<project>.vercel.app/user/chatbot`. Ask: "What is the lock-in of Nippon India ELSS Tax Saver Fund?" Expected: an answer with citations to the M1 fund factsheet, returned within ~5s.

- [ ] **Step 13.3: Pulse refresh (browser)**

Log in as admin. Open `/admin/pulse`. Click "Refresh now". Expected: the page transitions through `running` to a populated themes list within 60-120s.

- [ ] **Step 13.4: Voice call (browser)**

Open `/user/voice` as a regular user. Click the call button. Expected: the assistant greets you with a theme-aware first line. Speak: "Book a 30-minute slot tomorrow at 2pm to discuss tax-saving funds." Expected: the assistant confirms a booking code (format `NL-XXXX`), and a row appears in Supabase `bookings`.

- [ ] **Step 13.5: Approval HITL (browser)**

After the voice booking, log in as admin. Open `/admin/approvals`. Approve the calendar action; reject the email action. Expected: the row transitions to `executed` (calendar event appears in Google Calendar) for the approve, and `rejected` for the email.

If any step fails, the HF Space "Logs" tab has the full backend log; check there first.

---

## Task 14: Update `docs/to-do_manually.md` to match reality

Replace the Render-specific guidance with HF Spaces guidance so the doc stays accurate.

**Files:**
- Modify: `docs/to-do_manually.md`

- [ ] **Step 14.1: Update the services table (around line 21)**

Replace the `Render` row with:

```
| **Hugging Face Spaces** | Backend deployment (free CPU basic, 16GB RAM, no card required) | One Docker SDK Space; Dockerfile + Space secrets per `docs/superpowers/plans/2026-05-05-deployment.md` |
```

- [ ] **Step 14.2: Update the env-var section header (around line 51)**

Change `### Backend (`backend/.env` for local, Render env for prod)` to `### Backend (`backend/.env` for local, HF Space secrets for prod)`.

- [ ] **Step 14.3: Add the new CORS regex env var to the dotenv block**

Inside the dotenv block (around line 55-85), append after `FRONTEND_URL=...`:

```
# Optional: regex matched against Origin header for additional allowed origins
# (e.g., Vercel preview deploys). Leave blank in local dev.
FRONTEND_ORIGIN_REGEX=
```

- [ ] **Step 14.4: Add a pointer to the deployment plan**

At the top of `docs/to-do_manually.md` (after the intro paragraph around line 8), add:

```markdown
> Step-by-step deployment is in `docs/superpowers/plans/2026-05-05-deployment.md`. This doc covers the manual external-account setup that the deploy plan assumes is already done.
```

- [ ] **Step 14.5: Commit doc updates**

```bash
git add docs/to-do_manually.md
git commit -m "docs: update manual to-do for HF Spaces backend deploy"
git push origin main
```

(The push triggers a Vercel auto-deploy. Verify on Vercel that the production deploy goes green.)

---

## Task 15: (Optional) Keep-warm cron ~~(DROPPED)~~

> **DROPPED 2026-05-05:** Deemed unnecessary for the demo cadence. Steps below preserved for reference.

HF Spaces free CPU basic sleeps after a stretch of inactivity. If demo-day cold-start latency matters, add a tiny GitHub Action that pings every 10 minutes during business hours.

- [ ] **Step 15.1: Decide whether to add this**

Skip if: the daily and weekly cron jobs already keep the Space warm enough for your demo cadence.

Add if: you want sub-second response from the demo URL with zero warmup.

- [ ] **Step 15.2: Create `.github/workflows/keep-warm.yml`**

```yaml
name: Keep HF Space warm
on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch: {}
jobs:
  ping:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - run: curl -fsS --max-time 30 "${{ secrets.BACKEND_URL }}/health" || true
```

The trailing `|| true` keeps the workflow green even if a single ping times out (the Space might be mid-restart).

- [ ] **Step 15.3: Commit and verify**

```bash
git add .github/workflows/keep-warm.yml
git commit -m "ci: keep HF Space warm with 10-min ping"
git push origin main
```

In GitHub Actions, manually trigger once to confirm green.

---

## Verification: definition of done

This deployment is complete when ALL of the following are true:

1. `curl https://<USER>-investor-ops-backend.hf.space/health` returns `{"status":"ok"}`.
2. The Vercel production URL renders the login page and a logged-in user can complete a RAG query end-to-end with no CORS errors in the browser console.
3. The "Weekly Review Scrape" GitHub Action goes green on manual trigger and inserts a `scrape_runs` row in Supabase.
4. The "Daily corpus refresh" GitHub Action goes green on manual trigger.
5. A test voice call from `/user/voice` produces a booking code and a Supabase `bookings` row.
6. An admin approval on `/admin/approvals` transitions a row to `executed` (or `rejected`).
7. `docs/to-do_manually.md` reflects HF Spaces (not Render) and points at this plan file.

---

## Rollback notes

- The HF Space lives in its own git history. To roll back the deployed backend, `git push hfspace <previous-sha>:main --force` against the `git subtree split` of an earlier commit.
- Vercel keeps every production deploy. Use Vercel dashboard → "Deployments" → "..." → "Promote to production" on a prior deploy.
- Env-var rollback: HF Space secrets and Vercel env vars are versioned in their respective UIs; you can revert individual secret values without touching code.
