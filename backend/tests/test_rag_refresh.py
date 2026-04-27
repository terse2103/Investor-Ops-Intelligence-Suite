"""Tests for POST /api/rag/refresh (daily corpus refresh)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings

TEST_SECRET = "cron-refresh-secret"


@pytest.fixture(autouse=True)
def _set_corpus_refresh_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "corpus_refresh_secret", TEST_SECRET)


def test_refresh_with_valid_cron_secret_reingests(client: TestClient) -> None:
    """Cron caller with valid X-Cron-Secret should call ingest_sources."""
    mock_ingest = AsyncMock(return_value=113)
    with patch("app.api.rag.ingest_sources", mock_ingest):
        resp = client.post(
            "/api/rag/refresh",
            headers={"X-Cron-Secret": TEST_SECRET},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trigger_source"] == "cron"
    assert body["chunks"] == 113
    assert body["sources"] >= 10  # M1 (6) + M2 (4)
    mock_ingest.assert_awaited_once()


def test_refresh_with_invalid_cron_secret_returns_401(client: TestClient) -> None:
    mock_ingest = AsyncMock()
    with patch("app.api.rag.ingest_sources", mock_ingest):
        resp = client.post(
            "/api/rag/refresh",
            headers={"X-Cron-Secret": "wrong"},
        )
    assert resp.status_code == 401
    mock_ingest.assert_not_awaited()


def test_refresh_with_no_credentials_returns_401(client: TestClient) -> None:
    mock_ingest = AsyncMock()
    with patch("app.api.rag.ingest_sources", mock_ingest):
        resp = client.post("/api/rag/refresh")
    assert resp.status_code == 401
    mock_ingest.assert_not_awaited()


def test_refresh_with_admin_jwt_reingests(client: TestClient) -> None:
    """Admin-JWT path should also work and report trigger_source='manual'."""
    mock_ingest = AsyncMock(return_value=42)
    fake_admin = {"id": "a1", "email": "admin@x.com", "role": "admin"}
    with (
        patch("app.api.rag.ingest_sources", mock_ingest),
        patch("app.api.rag.require_auth", new=AsyncMock(return_value=fake_admin)),
    ):
        resp = client.post(
            "/api/rag/refresh",
            headers={"Authorization": "Bearer faketoken"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trigger_source"] == "manual"
    assert body["chunks"] == 42
    mock_ingest.assert_awaited_once()


def test_refresh_with_user_jwt_returns_403(client: TestClient) -> None:
    mock_ingest = AsyncMock()
    fake_user = {"id": "u1", "email": "user@x.com", "role": "user"}
    with (
        patch("app.api.rag.ingest_sources", mock_ingest),
        patch("app.api.rag.require_auth", new=AsyncMock(return_value=fake_user)),
    ):
        resp = client.post(
            "/api/rag/refresh",
            headers={"Authorization": "Bearer faketoken"},
        )
    assert resp.status_code == 403
    mock_ingest.assert_not_awaited()


def test_refresh_returns_502_on_ingest_failure(client: TestClient) -> None:
    """Ingest exceptions should surface as 502 with detail, not generic 500."""
    with patch(
        "app.api.rag.ingest_sources",
        new=AsyncMock(side_effect=RuntimeError("source unreachable")),
    ):
        resp = client.post(
            "/api/rag/refresh",
            headers={"X-Cron-Secret": TEST_SECRET},
        )
    assert resp.status_code == 502
    assert "Corpus refresh failed" in resp.json()["detail"]
    assert "source unreachable" in resp.json()["detail"]
