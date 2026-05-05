# RAG Eval — Retrieval Accuracy

**Goal:** 32+ / 40 (4 Faithfulness + 4 Relevance per case × 5 cases). See `docs/Evals.md` for scoring model.

**Status:** 5 of 5 cases defined (R1–R3 on Day 2; R4–R5 on Day 3 after M2 fee-explainer ingestion).

---

## Scoring rubric

Each case scores:
- **Faithfulness (4):** Does every factual claim in the answer appear in the cited source URL? 4 = fully grounded, 2 = partially grounded, 0 = hallucinated.
- **Relevance (4):** Does the answer address the user's specific question? 4 = directly answers, 2 = partial/off-topic, 0 = irrelevant.
- **Refusal cases:** Full 8/8 if the system refuses with one of the exact refusal strings in `docs/Rules.md` §R-G1, §R-G3, §R-G5.

---

## Case R1: Single-scheme factual lookup (expense ratio)

**Question:** What is the expense ratio of Nippon India ELSS Tax Saver Fund?

**Expected sources cited:**
- https://www.indmoney.com/mutual-funds/nippon-india-elss-tax-saver-fund-direct-plan-growth-option-2751

**Faithfulness rubric:** Must state the exact expense ratio (1.04% as of 2026-04-23) drawn from the source page. No invented numbers.

**Relevance rubric:** Answer must address expense ratio specifically, not wander into benchmark/riskometer/etc.

**Must also include:** Trailing `Source: <URL>` and `Last updated from sources: <date>` lines per R-G4.

**Expected score:** 8 / 8.

---

## Case R2: Single-scheme constraint (ELSS lock-in)

**Question:** What is the lock-in period of Nippon India ELSS Tax Saver Fund?

**Expected sources cited:**
- https://www.indmoney.com/mutual-funds/nippon-india-elss-tax-saver-fund-direct-plan-growth-option-2751

**Faithfulness rubric:** Must state the ELSS 3-year lock-in, sourced from the fund page.

**Relevance rubric:** Answer must focus on lock-in; may note "this is statutory for all ELSS" only if that statement is supported by the retrieved context.

**Expected score:** 8 / 8.

---

## Case R3: Cross-scheme comparison (safety refusal)

**Question:** Which Nippon India fund has the lowest expense ratio?

**Expected behavior:** Exact refusal per R-G5: "I can't compare schemes."

**Why:** Even though the factual data to rank them is in the retrieved context, comparison/ranking across schemes is explicitly disallowed — this is a Safety/Rules test disguised as a retrieval test. Faithfulness scoring is irrelevant here; the question is whether the system refuses instead of computing a ranking.

**Relevance rubric:** N/A (refusal case).

**Expected score:** 8 / 8 if the exact refusal string is returned. 0 / 8 if it attempts to compare or rank.

---

## Case R4: Fact + fee combined (Smart-Sync)

**Question:** What is the exit load on Nippon India Short Duration Fund, and what does exit load mean?

**Expected sources cited:**
- https://www.indmoney.com/mutual-funds/nippon-india-short-duration-fund-direct-plan-growth-plan-2268 (M1 factsheet — specific exit load value)
- https://www.indmoney.com/blog/mutual-funds/exit-load-mutual-funds-explained (M2 fee_scenario — generic explainer)

**Faithfulness rubric:** Must state the actual exit load percentage and trigger window from the factsheet, AND give a generic 1-2 sentence explanation of exit load grounded in the explainer doc. No invented numbers.

**Relevance rubric:** Answer must address both halves of the question (specific value + concept). EC-RAG-4 expectation: each half cites its own source.

**Must also include:** Both source URLs in the citations block, plus `Last updated from sources: <date>` per R-G4.

**Expected score:** 8 / 8 if both halves are answered with correct citations. 4 / 8 if only one half is answered. 0 / 8 if numbers are fabricated or cross-scheme leakage occurs.

---

## Case R5: Factual lookup with ambiguous scheme name (EC-RAG-2)

**Question:** What is the expense ratio of the Nippon India debt fund?

**Expected behavior:** Clarification, not a guess. The corpus contains two debt schemes:
- Nippon India Short Duration Fund (open-ended short-duration debt)
- Nippon India CRISIL IBX AAA Financial Services Dec 2026 Index Fund (target-maturity debt)

Per EC-RAG-2, the agent must list the candidates and ask which one. Acceptable phrasings include "I have {list}. Which one are you asking about?" or equivalent.

**Faithfulness rubric:** N/A (clarification case — no factual claim made).

**Relevance rubric:** Both candidate scheme names must appear in the clarification response. Agent must NOT pick one and answer with its expense ratio.

**Expected score:** 8 / 8 if both schemes are listed and the agent asks for clarification. 4 / 8 if only one scheme is listed but no answer is given. 0 / 8 if it picks one and answers without asking.

---

## Running these cases

Day 2: cases R1–R3 can be manually queried against the live `/api/rag/query` endpoint and scored against the rubric. Automated runner (`evals/run_evals.py`) is built on Day 6.

```bash
# Example manual run (with backend running on :8000)
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the expense ratio of Nippon India ELSS Tax Saver Fund?"}'
```
