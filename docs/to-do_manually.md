# Manual To-Do (everything not in code)

The codebase ships with the full implementation of the 7-day plan. Some steps
inherently require external accounts, OAuth flows, or human action. This file
is the single source of truth for those.

Order them roughly top-to-bottom; later steps depend on earlier ones.

> Step-by-step deployment is in `docs/superpowers/plans/2026-05-05-deployment.md`. This doc covers the manual external-account setup that the deploy plan assumes is already done.

---

## 1. Provision external accounts

| Service | Why | What you need |
|---|---|---|
| **Anthropic** | RAG answer composition + pulse generation (Claude Sonnet 4.6) | API key with prompt-caching enabled |
| **Supabase** | Postgres + Auth + RLS | Project URL, anon key, service-role key |
| **Vapi** | Voice agent (Web SDK + post-call webhook) | Public key, assistant ID, webhook shared secret |
| **Google Cloud** | Calendar + Sheets APIs (post-approval execution) | A service-account JSON (or OAuth) |
| **Resend** (or pick another provider in `core/notifier.py`) | One email per booking decision (R-APPROVE4) | API key + verified `from` address |
| **GitHub** | Repo + Actions cron for weekly scrape and daily corpus refresh | Repo with secrets `BACKEND_URL`, `SCRAPE_SHARED_SECRET`, `CORPUS_REFRESH_SECRET` |
| **Hugging Face Spaces** | Backend deployment (free CPU basic, 16GB RAM, no card required) | One Docker SDK Space; Dockerfile + Space secrets per `docs/superpowers/plans/2026-05-05-deployment.md` |
| **Vercel** | Frontend deployment | Project pointed at `frontend/` |

If you skip Google APIs and/or Gmail MCP, fall back to the cut-line in
`docs/Plan.md` and write Calendar/Sheets data into Supabase instead. The
approval dispatcher will surface a 502 with a clear error if those are not
configured, which is acceptable for the demo if you say "this is the
fallback path" out loud.

---

## 2. Run the Supabase migrations

1. Open the Supabase SQL Editor.
2. Paste the entirety of `supabase/migrations/0001_init.sql` and run.
3. Paste the entirety of `supabase/migrations/0002_auto_user_contacts.sql`
   and run. This extends the signup trigger so every new user gets a
   `user_contacts` row populated from `auth.users.email` (the approval
   dispatcher needs this to resolve a recipient on email-action approval).
   The migration also backfills existing users.
4. In the Auth settings, create at least two users:
   - one regular user (your test email);
   - one admin (set `app_metadata.role = 'admin'` via the SQL Editor:
     `update auth.users set raw_app_meta_data = jsonb_set(coalesce(raw_app_meta_data, '{}'), '{role}', '"admin"') where email = '<your-admin-email>';`).
5. Confirm RLS is on for every table (`select tablename from pg_tables where schemaname = 'public'` then check `select rowsecurity from pg_class where relname = '<table>'`).

---

## 3. Configure environment variables

### Backend (`backend/.env` for local, HF Space secrets for prod)

```dotenv
# Core
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
FRONTEND_URL=https://<your-vercel-app>.vercel.app
# Optional: regex matched against Origin header for additional allowed origins
# (e.g., Vercel preview deploys). Leave blank in local dev.
FRONTEND_ORIGIN_REGEX=

# Scraper + corpus refresh
SCRAPE_SHARED_SECRET=<random-32-char-string>
CORPUS_REFRESH_SECRET=<random-32-char-string>

# Voice
VAPI_API_KEY=<from Vapi dashboard>
VAPI_PUBLIC_KEY=<from Vapi dashboard>
VAPI_WEBHOOK_SECRET=<random-32-char-string; mirror in Vapi server-URL header>
VAPI_ASSISTANT_ID=<from Vapi dashboard after upload>

# Google APIs (post-approval execution)
GOOGLE_SA_JSON={"type":"service_account",...}   # paste the JSON inline
# OR
GOOGLE_SA_JSON_PATH=/path/to/sa.json
GOOGLE_CALENDAR_ID=<calendar-id-shared-with-SA>
GOOGLE_SHEETS_ID=<spreadsheet-id-shared-with-SA>
GOOGLE_SHEETS_RANGE=Bookings!A:F

# Gmail MCP (post-approval email draft)
GMAIL_MCP_COMMAND=npx
GMAIL_MCP_ARGS=-y,@your/gmail-mcp-server

# Notifier
RESEND_API_KEY=re_...
EMAIL_FROM=ops@your-domain.com
```

### Frontend (`frontend/.env.local`)

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000   # or your Render URL
NEXT_PUBLIC_VAPI_PUBLIC_KEY=<from Vapi dashboard>
NEXT_PUBLIC_VAPI_ASSISTANT_ID=<from Vapi dashboard>
```

### GitHub Actions (Repo → Settings → Secrets and variables → Actions)

- `BACKEND_URL` — public URL of the deployed backend.
- `SCRAPE_SHARED_SECRET` — same value as backend env.
- `CORPUS_REFRESH_SECRET` — same value as backend env.

---

## 4. Configure the Vapi assistant

1. In the Vapi dashboard, create a new assistant.
2. Open `docs/Vapi.md` and paste the system prompt block verbatim.
3. Set:
   - LLM provider: Anthropic, model `claude-sonnet-4-6`.
   - Voice: any neutral Indian-English voice.
   - First-message mode: `assistant-speaks-first-with-model-generated-message`.
   - Server URL: `${BACKEND_URL}/api/voice/post-call` with custom request
     header `X-Vapi-Secret: ${VAPI_WEBHOOK_SECRET}`.
   - Structured-data extraction: `topic`, `slot_iso`, `intent`.
4. Copy the assistant ID into both backend (`VAPI_ASSISTANT_ID`) and frontend
   (`NEXT_PUBLIC_VAPI_ASSISTANT_ID`).

---

## 5. Configure Google APIs

1. Create a service account in Google Cloud → IAM & Admin → Service Accounts.
2. Grant it no project-level role (we use shared-resource auth instead).
3. Generate a JSON key, paste into `GOOGLE_SA_JSON` (or save and use `_PATH`).
4. Calendar:
   - Open Google Calendar → settings of the calendar you want to use →
     "Share with specific people" → add the SA email with "Make changes to
     events".
   - Copy the calendar ID (under "Integrate calendar") into `GOOGLE_CALENDAR_ID`.
5. Sheets:
   - Create a Google Sheet "Advisor Pre-Bookings" with headers:
     `created_at | booking_code | user_id | topic | slot_iso | status`.
   - Share the sheet with the SA email as Editor.
   - Copy the spreadsheet ID from the URL into `GOOGLE_SHEETS_ID`.
6. Enable Calendar API and Sheets API in the GCP Console for the project.

---

## 6. Set up the Gmail MCP server

The capstone calls `core/mcp_client.py::create_draft` post-approval. That client
spawns whatever `GMAIL_MCP_COMMAND` + `GMAIL_MCP_ARGS` produce as an MCP-stdio
server. You have two options:

1. **Self-host a community Gmail MCP server.** Several exist on GitHub
   (`MarkusMcNugen/mcp-gmail`, `gongrzhe/server-gmail-autoauth-mcp`, etc.).
   Clone, follow the README to do the OAuth dance, then point
   `GMAIL_MCP_COMMAND` at the spawn command.
2. **Cut-line: skip MCP for the demo.** If time is tight, mock the call by
   monkey-patching `app.core.mcp_client.create_draft` to return
   `{"draftId": "demo"}` in dev. The demo video can show the approval row
   transitioning to `executed` even without a real Gmail draft.

---

## 7. Verify the wiring before the demo

```bash
# Backend: smoke test
curl -f http://localhost:8000/health
# RAG (need a user JWT)
curl -X POST http://localhost:8000/api/rag/query \
  -H "Authorization: Bearer $USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the lock-in of Nippon India ELSS Tax Saver Fund?"}'
# Scrape (admin)
curl -X POST http://localhost:8000/api/scrape \
  -H "Authorization: Bearer $ADMIN_JWT"
# Pulse (admin)
curl -X POST http://localhost:8000/api/pulse/generate \
  -H "Authorization: Bearer $ADMIN_JWT"
# Voice context (any user)
curl http://localhost:8000/api/voice/context \
  -H "Authorization: Bearer $USER_JWT"
```

Each should 2xx. The scrape will create a `scrape_runs` row with
`status='ok'` (verify in Supabase). The pulse will populate `current_themes`.

---

## 8. Run the eval suite

```bash
cd backend
USER_JWT=...  ADMIN_JWT=...  VAPI_WEBHOOK_SECRET=...  uv run python ../evals/run_evals.py
cat ../evals/eval-report.md
```

Target: ≥85/100, Safety = 30/30. If any RAG case scores low, manually re-grade
that case (the runner's heuristics are conservative; an LLM-grader would do
better but is out of plan scope).

If a fix is needed, iterate on:

- **Faithfulness drops** → check whether the new fact landed in the corpus
  (`uv run python -c "from app.core.retriever import get_retriever; print(len(get_retriever().indexed_urls()))"`).
- **Refusal misses** → tighten the system prompt's exact-string rule.
- **PII leaks (S2 fail)** → confirm `redact()` is called on the post-call
  payload BEFORE persistence (`backend/app/services/voice/post_call.py:140`).

Commit the final `evals/eval-report.md`.

---

## 9. Record the 5-minute demo video

Suggested storyboard (matches the eval flow):

| Time | Action | Caption |
|---|---|---|
| 0:00 | Open `/admin/pulse`, click "Refresh now" | "Scraper pulls Play Store reviews; pulse generator clusters into top 3 themes" |
| 0:50 | Open `/user/voice`, start a call | "Vapi opens with a theme-aware greeting" |
| 1:30 | Book a slot, hear the booking code | "NL-XXXX written into Supabase" |
| 2:00 | Open `/user/chatbot`, ask a Smart-Sync question | "RAG cites both M1 fund factsheet and M2 fee explainer" |
| 3:00 | Open `/admin/approvals`, approve calendar + sheets, reject email | "HITL gate ensures every external action requires admin approval" |
| 3:45 | Show Supabase: `notifications_sent` row, `action_audit` rows | "Every execution is audited" |
| 4:15 | Open `evals/eval-report.md` | "Eval score 85+, Safety 30/30" |
| 5:00 | End | |

Record at 1080p, voice-over only (no face-cam needed). Upload to YouTube
unlisted; paste the link in the README and the capstone submission.

---

## 10. Submit the capstone

1. Push the final commit to `main`.
2. Make the GitHub repo public (or invite the graders).
3. Submit:
   - Repo URL
   - Demo video URL
   - `evals/eval-report.md` link
   - Architecture-spec link
4. Confirm the `Plan.md` progress bar reads 100%.

---

## Quick-reference: items that will NEVER auto-resolve

- The Supabase admin role flag must be set per user via SQL (Supabase Auth
  doesn't expose a UI for `app_metadata` writes).
- Vapi assistant config must be uploaded by hand; there is no API for the
  full system prompt + analysis-plan combo we use.
- Google API SA must be shared with each calendar / sheet manually via the
  Google web UI.
- Gmail MCP server must be running externally; the backend cannot start it
  in production without OAuth-flow approval.
- The demo video and capstone submission are inherently human steps.
