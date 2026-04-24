"""Pillar A: Smart-Sync KB (M1 RAG + M2 Fee Explainer unified index)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.auth import require_auth
from app.core.limiter import limiter
from app.services.rag.query import query_rag

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


class QueryIn(BaseModel):
    question: str


class QueryOut(BaseModel):
    answer: str
    citations: list[str]
    last_updated: str | None = None


@router.post("/query", response_model=QueryOut)
@limiter.limit("10/minute")
async def query(
    request: Request,
    payload: QueryIn,
    user: dict = Depends(require_auth),
) -> QueryOut:
    """Accept a user question; return a cited, facts-only answer."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")
    try:
        result = await query_rag(payload.question)
    except Exception as e:
        log.exception("rag.query failed: %s", e)
        raise HTTPException(status_code=500, detail="rag query failed") from e
    return QueryOut(**result)
