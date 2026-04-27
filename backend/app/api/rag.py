"""Pillar A: Smart-Sync KB (M1 RAG + M2 Fee Explainer unified index)."""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.config import settings
from app.core.auth import require_admin, require_auth
from app.core.limiter import limiter
from app.services.rag.corpus import ALL_SOURCES
from app.services.rag.ingest import ingest_sources
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


async def _refresh_auth(
    x_cron_secret: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    """Allow either a daily cron secret OR an admin JWT.

    Returns 'cron' for shared-secret callers, 'manual' for admin-JWT callers.
    """
    if x_cron_secret is not None:
        if (
            not settings.corpus_refresh_secret
            or x_cron_secret != settings.corpus_refresh_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid cron secret",
            )
        return "cron"
    user = await require_auth(authorization)
    await require_admin(user)
    return "manual"


@router.post("/refresh")
async def refresh_corpus(trigger_source: str = Depends(_refresh_auth)) -> dict:
    """Re-ingest all sources to keep the RAG index up-to-date.

    Triggered daily by GitHub Actions cron, or manually by an admin. Upserts
    every chunk by deterministic id (sha256(url) + chunk_index), so existing
    chunks get refreshed `fetched_at` metadata and any updated content from
    the source page.

    Returns: {"trigger_source": ..., "sources": N, "chunks": N}.
    """
    try:
        chunks = await ingest_sources(ALL_SOURCES)
    except Exception as exc:
        log.exception("corpus refresh failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Corpus refresh failed: {exc}",
        ) from exc
    return {
        "trigger_source": trigger_source,
        "sources": len(ALL_SOURCES),
        "chunks": chunks,
    }
