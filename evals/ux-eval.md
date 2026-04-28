# UX Eval — Tone & Structure

**Goal:** 28+ / 30 (Pulse rubric: 15 pts, Voice theme-mention logic check: 15 pts). See `docs/Evals.md` for scoring model.

**Status:** Rubric defined (Day 2). All 4 sub-evals (P1–P3 + V1) ready to run after Day 3 + Day 4 implementations. Final score recorded by Day 6 runner.

---

## Scoring

| Sub-eval | Points | Check |
|---|---|---|
| Pulse: word count ≤250 | 5 | `len(pulse_text.split()) <= 250` |
| Pulse: exactly 3 action ideas | 5 | `len(actions) == 3` |
| Pulse: top 3 themes present | 5 | All 3 theme strings appear in `current_themes` table |
| Voice: top theme in greeting | 15 | Top theme string appears in Vapi call transcript greeting turn |

All four checks are **pass/fail**. No partial credit within a check; the 5-pt value is the award for a pass.

---

## Pulse Rubric

### P1: Word count ≤ 250

**Test:** Call `POST /api/pulse/generate` with seeded reviews in the `reviews` table. Retrieve the generated `pulses` row. Count `len(pulse_text.split())`.

**Expected:** `<= 250` words.

**Score:** 5 / 5 if passing, 0 / 5 if over.

**Status:** 🟡 Ready to run (Day 3 implementation complete; final score recorded by Day 6 runner)

---

### P2: Exactly 3 action ideas

**Test:** Same generated pulse. Check `len(pulse_row["actions"]) == 3`.

**Expected:** Exactly 3 elements in the `actions` JSON array.

**Score:** 5 / 5 if passing, 0 / 5 otherwise.

**Status:** 🟡 Ready to run (Day 3 implementation complete; final score recorded by Day 6 runner)

---

### P3: Top 3 themes in `current_themes`

**Test:** After `POST /api/pulse/generate`, query the `current_themes` singleton row. Check it has exactly 3 theme strings.

**Expected:** `len(current_themes["themes"]) == 3`.

**Score:** 5 / 5 if passing, 0 / 5 otherwise.

**Status:** 🟡 Ready to run (Day 3 implementation complete; final score recorded by Day 6 runner)

---

## Voice Theme-mention Logic Check

### V1: Top theme string appears in greeting

**Test:**
1. Seed `current_themes` with `{ "themes": ["Login Issues", "Slow Withdrawals", "KYC Problems"] }`.
2. Start a Vapi Web SDK call (scripted test; trigger `GET /api/voice/context` to verify injection).
3. After call ends, inspect the transcript's first assistant turn.
4. Assert that the string `"Login Issues"` appears in the greeting.

**Expected:** `"Login Issues"` in `transcript[0]["assistant"]`

**Score:** 15 / 15 if the top theme is mentioned. 0 / 15 otherwise.

**Note:** This check validates Pillar B end-to-end: scraper → pulse → `current_themes` → Vapi injection → voice greeting. If `current_themes` is empty (no pulse generated), the voice agent must still greet without crashing (graceful degradation), but the score is 0.

**Status:** 🟡 Ready to run (Day 4 implementation complete: /api/voice/context exposes top_theme_1..3 as Vapi dynamic variables; assistant prompt in docs/Vapi.md mandates theme mention in greeting; final score recorded by Day 6 runner)

---

## Running these checks

Automated via `evals/run_evals.py` on Day 6. Before Day 6, check each manually:

```bash
# P1-P3: after backend + Supabase are running
curl -X POST http://localhost:8000/api/pulse/generate
# Then inspect the pulse row in Supabase

# V1: after Vapi agent is configured and current_themes seeded
curl http://localhost:8000/api/voice/context
# Should return { "themes": ["Login Issues", "Slow Withdrawals", "KYC Problems"] }
```
