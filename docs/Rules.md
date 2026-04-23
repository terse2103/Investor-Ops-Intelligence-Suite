# Product Rules

These are the cross-cutting rules that govern every LLM call, voice turn, and user-facing output in the Investor Ops & Intelligence Suite. They are enforced in three layers:

1. **Prompt templates** — baked into every service's system message.
2. **Output validators** — programmatic checks in FastAPI before a response is returned.
3. **PII guard middleware** — `core/pii.py`, applied on every LLM input and output.

If a rule has a numeric constraint, the validator must enforce it; if the LLM produces a violation, the service should silently repair (retry once) or fail closed (return a clear error message).

---

## 1. Global rules (apply to every service)

### R-G1: No investment advice
Never recommend buying, selling, holding, or comparing schemes. Never predict returns, performance, or market direction. If asked, respond:
> "I can't give investment advice."

Enforcement: system prompt + output-scan for banned phrases (e.g., "I recommend", "you should buy", "will give X% returns").

### R-G2: PII never echoes in LLM output
If user input contains PAN, Aadhaar, account number, OTP, or phone number, the PII guard replaces the value with `[REDACTED]` before the prompt reaches the LLM. The LLM must never emit any of those tokens literally. The user's own saved notification email in `user_contacts` is product data, not PII-in-transit (see R-G7).

Enforcement: regex-based PII guard middleware; output-scan as a safety net.

### R-G3: Sources are mandatory
Every factual answer (M1 RAG, M2 Fee Explainer) ends with at least one official source URL from the approved corpus. If no source supports the answer, the service refuses:
> "I don't have a verified source for that."

Enforcement: retrieval step must return at least one chunk; generator prompt requires a citation slot; validator rejects responses with no URL.

### R-G4: "Last updated / Last checked" timestamps
- RAG answers: append `Last updated from sources: {YYYY-MM-DD}` (derived from the most recent source chunk used).
- Fee Explainer entries: append `Last checked: {YYYY-MM-DD}` (the date the fee doc was last refreshed).

Enforcement: validator checks for the literal string suffix.

### R-G5: No opinion, no comparison, no performance claims
Do not compute or compare returns across schemes. Do not rate schemes. Do not say "this is better than that." If asked, refer to the official factsheet.

Enforcement: output-scan for comparative language ("better", "higher returns", "outperforms") in fact-only contexts.

### R-G6: English, neutral tone
All outputs in English. Neutral, factual tone. No marketing language, no emoji, no exclamation points in factual answers.

Enforcement: style section of the system prompt; light output-scan for emoji/exclamation.

### R-G7: User-saved contact info is product data
The `email` a user saves in `/user/settings` is stored in `user_contacts` and used only by `core/notifier.py`. It is:
- Never put into an LLM prompt.
- Never included in Vapi dynamic variables.
- Never logged in call transcripts.

This rule is how R-G2 ("no PII in LLM output") coexists with the notifications feature. If the user's email somehow appears in an LLM-facing context, the PII guard still redacts it as a safety net.

---

## 2. RAG Chatbot (M1 + Pillar A)

### R-RAG1: Answers are ≤3 sentences
Short, factual, no filler. If the answer cannot fit in 3 sentences, split into a bullet list of at most 6 bullets (this also covers the "6-bullet structure" for combined M1+M2 fee + fact questions).

### R-RAG2: Exactly one citation per answer
Inline or trailing. URL must be in the approved `sources` table.

### R-RAG3: Refuse opinionated/portfolio questions
Example triggers: "Should I buy?", "Which fund is better?", "Will this go up?" Respond with R-G1's refusal template.

### R-RAG4: Smart-Sync 6-bullet for combined fact + fee questions
When a query spans both MF facts (M1) and fee logic (M2), format the response as exactly 6 bullets: 3 for the factual scheme answer, 3 for the fee explanation. Each set cites its own source.

---

## 3. Fee Explainer (M2 Part B)

### R-FEE1: ≤6 bullets per scenario
Structured explanation only. No prose.

### R-FEE2: Exactly one official source link per scenario
Same approval as R-RAG2.

### R-FEE3: "Last checked: {date}"
Appended to every fee entry.

### R-FEE4: No recommendations, no comparisons
Factual explanation of what a fee is and when it applies. Never "this fund charges less than that one."

---

## 4. Weekly Pulse (M2 Part A)

### R-PULSE1: Max 5 clustered themes
Reviews get grouped into at most 5 themes; smaller groups are merged.

### R-PULSE2: Top 3 themes surfaced
Ranked by review count. These 3 feed `current_themes` for the voice agent's greeting (see R-VOICE2).

### R-PULSE3: Exactly 3 user quotes
Verbatim quotes from real reviews. PII guard runs on each quote before storage.

### R-PULSE4: ≤250-word pulse note
Single weekly note summarizing themes + outlook. Validator rejects anything over 250 words.

### R-PULSE5: Exactly 3 action ideas
Concrete, product-facing suggestions. Not 2, not 4. Validator enforces.

### R-PULSE6: No PII in quotes or themes
PII guard runs both on inbound review text and on the pulse output.

### R-PULSE7: Input filter — English reviews longer than 5 words
Pulse generation considers only reviews that satisfy both conditions:
1. Detected language is English.
2. Length is strictly more than 5 words (so 6 words or more) after whitespace tokenization.

Non-qualifying reviews are **never written to the `reviews` table**. The filter is applied by the scraper during ingestion, so by construction the `reviews` table only ever contains valid input for pulse generation.

Enforcement: ingestion-time filter in `services/pulse/scraper.py` using a lightweight language detector (e.g., `langdetect`) plus a whitespace token-count check. The number of rejected reviews per scrape is recorded on the `scrape_runs` row as `filtered_out_count` for audit.

---

## 5. Voice Agent (M3 + Pillars B, C)

### R-VOICE1: Opening disclaimer
First agent turn after greeting: "This is an informational call. I cannot provide investment advice."

### R-VOICE2: Theme-aware greeting
The greeting line must mention the current top 3 themes (or at least the top 1 if themes are short-text). Example: "I see many users are asking about Nominee updates today. I can help you book a call for that!"

### R-VOICE3: IST only; repeat date/time on confirm
All times quoted in Indian Standard Time. On confirmation, the agent repeats the booked date and time before reading the booking code.

### R-VOICE4: No PII collected on the call
Agent never asks for phone, email, PAN, Aadhaar, or account numbers. If the caller volunteers any, the agent ignores it and does not write it to the transcript payload (PII guard on webhook payload).

### R-VOICE5: Refuse investment advice mid-call
Same refusal template as R-G1. Agent returns to the booking flow after refusing.

### R-VOICE6: Always generate a booking code on confirm
Format `NL-XXXX` where XXXX is a 4-char alphanumeric. Read the code to the caller at end of call.

---

## 6. Approval Center + MCP/API actions (Pillar C)

### R-APPROVE1: No external action without admin approval
`pending_actions` start in status `pending`. Google Calendar, Google Sheets, and Gmail MCP are only invoked after an admin flips an action to `approved`. A rejected action is never executed.

### R-APPROVE2: Market Context is mandatory in the email draft
Before the email action is queued, the current top 3 themes from the latest pulse are injected into the email body as a "Market Context" snippet. Validator checks the snippet is present in the payload.

### R-APPROVE3: Every execution produces an audit row
Every approved action writes to `action_audit` on success or failure, including the provider's response. No silent execution.

### R-APPROVE4: Notifications fire once per booking decision
When the admin has finalized all three `pending_actions` for a booking (any mix of approve/reject), the notifier sends exactly one email to the booking user. Not three (one per action); one.

---

## 7. Scraper + Pulse ingestion

### R-SCRAPE1: Dedup on Play review ID
The scraper never writes a duplicate review row. If the Play review ID is already present, the row is skipped.

### R-SCRAPE2: PII guard on every inbound review
Applied before the review is stored in `reviews`. Reviews containing phone/email/account numbers get those tokens redacted at ingestion.

### R-SCRAPE3: Window is 8-12 weeks
Pulse is generated from reviews scraped within the last 8-12 weeks, matching the M2 spec.

---

## 8. Guardrail failures

If any validator above rejects a generated output, the service:

1. Logs the violation with the prompt ID.
2. Retries once with a stricter prompt.
3. If the retry also fails, returns a generic safe message:
   > "I can't produce a verified answer for that. Please contact support."

Silent pass is never acceptable. Guardrail failures are one of the things the Safety eval (`evals/safety-eval.md`) specifically tests for.
