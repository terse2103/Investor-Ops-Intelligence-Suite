"""Pillar A: Smart-Sync KB (M1 RAG + M2 Fee Explainer unified index)."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/rag", tags=["rag"])


class QueryIn(BaseModel):
    question: str


@router.post("/query")
async def query(payload: QueryIn) -> dict:
    """Accept a user question; return a cited, facts-only answer.

    TODO (Day 2): retrieve top-k chunks from Chroma, compose answer via Claude
    with R-RAG rules, run PII guard on output, return with citations + last_updated.
    """
    return {"status": "not_implemented", "question": payload.question}
