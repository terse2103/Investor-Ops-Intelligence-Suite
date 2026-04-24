"""FastAPI entrypoint for the Investor Ops & Intelligence Suite backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import approvals, health, pulse, rag, scrape
from app.api import settings as settings_api
from app.api import voice
from app.config import settings

app = FastAPI(
    title="Investor Ops & Intelligence Suite",
    version="0.1.0",
    description="Backend for the 3-pillar fintech ops suite (RAG + Pulse + Voice).",
)

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
