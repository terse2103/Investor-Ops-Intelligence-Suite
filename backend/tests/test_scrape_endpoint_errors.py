"""Verify the /api/scrape endpoint surfaces upstream failures as 502 + detail."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings

TEST_SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _set_scrape_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "scrape_shared_secret", TEST_SECRET)


def test_scrape_returns_502_on_play_store_failure(client: TestClient) -> None:
    """When scrape_reviews raises (e.g. Play Store rate limit), return 502 with detail."""
    with patch(
        "app.api.scrape.scrape_reviews",
        new=AsyncMock(side_effect=RuntimeError("play store unreachable")),
    ):
        resp = client.post(
            "/api/scrape",
            headers={"X-Scrape-Secret": TEST_SECRET},
        )
    assert resp.status_code == 502
    body = resp.json()
    assert "Scrape failed" in body["detail"]
    assert "play store unreachable" in body["detail"]


def test_scrape_returns_502_on_supabase_failure(client: TestClient) -> None:
    """A generic Supabase error from scrape_reviews must surface in the body, not as 500."""
    with patch(
        "app.api.scrape.scrape_reviews",
        new=AsyncMock(side_effect=ValueError("bad service-role key")),
    ):
        resp = client.post(
            "/api/scrape",
            headers={"X-Scrape-Secret": TEST_SECRET},
        )
    assert resp.status_code == 502
    assert "bad service-role key" in resp.json()["detail"]
