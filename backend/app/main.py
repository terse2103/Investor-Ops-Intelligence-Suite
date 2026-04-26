"""FastAPI entrypoint for the Investor Ops & Intelligence Suite backend."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import approvals, health, pulse, rag, scrape
from app.core.limiter import limiter
from app.api import settings as settings_api
from app.api import voice
from app.config import settings

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Populate the RAG index on startup if empty (Render free tier disk is ephemeral).
    # Skip in test mode to keep TestClient instantiation fast and offline.
    if os.getenv("SKIP_STARTUP_INGEST") != "1":
        try:
            from app.core.retriever import get_retriever
            from app.services.rag.corpus import ALL_SOURCES
            from app.services.rag.ingest import ingest_sources

            retriever = get_retriever()
            indexed = retriever.indexed_urls()
            missing = [src for src in ALL_SOURCES if src["url"] not in indexed]
            if missing:
                n = await ingest_sources(missing)
                log.info(
                    "Startup ingest: %d new chunks across %d sources (was %d sources, %d chunks)",
                    n,
                    len(missing),
                    len(indexed),
                    retriever.count() - n,
                )
            else:
                log.info(
                    "RAG index up-to-date: %d chunks across %d sources",
                    retriever.count(),
                    len(indexed),
                )
        except Exception as e:
            log.warning("Startup ingest failed (proceeding with empty index): %s", e)
    yield


app = FastAPI(
    title="Investor Ops & Intelligence Suite",
    version="0.1.0",
    description="Backend for the 3-pillar fintech ops suite (RAG + Pulse + Voice).",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(rag.router)
app.include_router(pulse.router)
app.include_router(voice.router)
app.include_router(approvals.router)
app.include_router(scrape.router)
app.include_router(settings_api.router)
