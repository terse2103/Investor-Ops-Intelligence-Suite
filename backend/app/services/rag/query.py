"""RAG query pipeline: retrieve → LLM → validate."""
from __future__ import annotations

import logging

from app.core.llm import answer_from_context
from app.core.pii import redact
from app.core.retriever import get_retriever

log = logging.getLogger(__name__)

# Encodes Rules.md R-G1..7 and R-RAG1..4 for Pillar A.
SYSTEM_PROMPT = """You are the Investor Ops & Intelligence Suite RAG assistant \
answering facts-only questions about Nippon India mutual fund schemes from the \
INDMoney corpus.

Rules (strict, non-negotiable):
1. Use ONLY the retrieved context provided in the user message. Never use prior knowledge.
2. Never give investment advice. If asked "should I buy/hold/sell" or similar, reply EXACTLY:
   "I can't give investment advice."
3. Never predict returns. Never rank or compare schemes. If asked for a comparison ("which is better", "which is cheaper", "which has the lowest X"), reply EXACTLY:
   "I can't compare schemes."
4. If the retrieved context does not contain enough information, refuse with EXACTLY:
   "I don't have a verified source for that."
5. Every factual answer must end with:
   Source: <exact URL from the retrieved context metadata>
   Last updated from sources: <fetched_at value from the retrieved context metadata>
6. Keep answers to at most 3 sentences. For combined fact-and-fee questions (Smart-Sync), format as at most 6 bullets (3 for the fact, 3 for the fee logic).
7. Never echo PAN, Aadhaar, account numbers, OTPs, phone numbers, or email addresses.

Output format for a factual answer:
<answer body, at most 3 sentences, or at most 6 bullets for Smart-Sync>

Source: <URL>
Last updated from sources: <YYYY-MM-DD>

Output format for a refusal:
<one of the exact refusal strings above>"""


async def query_rag(question: str) -> dict:
    """Run a RAG query end-to-end. Returns {answer, citations, last_updated}."""
    safe_question = redact(question)  # R-G2 inbound

    retriever = get_retriever()
    chunks = retriever.query(safe_question, top_k=8)

    if not chunks:
        return {
            "answer": "I don't have a verified source for that.",
            "citations": [],
            "last_updated": None,
        }

    raw_answer = answer_from_context(
        question=safe_question,
        context_chunks=chunks,
        system_prompt=SYSTEM_PROMPT,
    )

    answer = redact(raw_answer)  # R-G2 outbound safety net
    citations = _extract_citations(answer, chunks)
    last_updated = _extract_last_updated(chunks)

    return {
        "answer": answer,
        "citations": citations,
        "last_updated": last_updated,
    }


def _extract_citations(answer: str, chunks: list[dict]) -> list[str]:
    """Return URLs from retrieved context that actually appear in the answer."""
    allowed = {c["metadata"]["url"] for c in chunks if c.get("metadata")}
    found: list[str] = []
    for url in allowed:
        if url in answer and url not in found:
            found.append(url)
    return found


def _extract_last_updated(chunks: list[dict]) -> str | None:
    dates = sorted(
        {
            c["metadata"].get("fetched_at")
            for c in chunks
            if c.get("metadata", {}).get("fetched_at")
        },
        reverse=True,
    )
    return dates[0] if dates else None
