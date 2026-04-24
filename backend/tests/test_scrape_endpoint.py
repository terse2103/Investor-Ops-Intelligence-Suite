"""Tests for the POST /api/scrape endpoint (auth + delegation to scrape_reviews)."""
from __future__ import annotations

import os

os.environ.setdefault("SKIP_STARTUP_INGEST", "1")

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_SCRAPE_RESULT = {
    "fetched": 5,
    "accepted": 3,
    "inserted": 2,
    "filtered_out": 2,
}

TEST_SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _set_scrape_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Override the scrape shared secret so tests control it."""
    monkeypatch.setattr(settings, "scrape_shared_secret", TEST_SECRET)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Happy-path: shared-secret auth
# ---------------------------------------------------------------------------

def test_scrape_with_valid_secret_returns_result(client: TestClient) -> None:
    """A valid X-Scrape-Secret should trigger scrape_reviews and return its result."""
    mock_scrape = AsyncMock(return_value=FAKE_SCRAPE_RESULT)

    with patch("app.api.scrape.scrape_reviews", mock_scrape):
        resp = client.post(
            "/api/scrape",
            headers={"X-Scrape-Secret": TEST_SECRET},
        )

    assert resp.status_code == 200
    assert resp.json() == FAKE_SCRAPE_RESULT
    mock_scrape.assert_awaited_once()


# ---------------------------------------------------------------------------
# Auth rejection: invalid secret
# ---------------------------------------------------------------------------

def test_scrape_with_invalid_secret_returns_401(client: TestClient) -> None:
    """An incorrect X-Scrape-Secret must be rejected with 401."""
    mock_scrape = AsyncMock(return_value=FAKE_SCRAPE_RESULT)

    with patch("app.api.scrape.scrape_reviews", mock_scrape):
        resp = client.post(
            "/api/scrape",
            headers={"X-Scrape-Secret": "wrong-secret"},
        )

    assert resp.status_code == 401
    mock_scrape.assert_not_awaited()


# ---------------------------------------------------------------------------
# Auth rejection: no credentials at all
# ---------------------------------------------------------------------------

def test_scrape_with_no_credentials_returns_401(client: TestClient) -> None:
    """No X-Scrape-Secret and no Authorization header must be rejected with 401."""
    mock_scrape = AsyncMock(return_value=FAKE_SCRAPE_RESULT)

    with patch("app.api.scrape.scrape_reviews", mock_scrape):
        resp = client.post("/api/scrape")

    # require_auth raises 401 when no token is provided
    assert resp.status_code == 401
    mock_scrape.assert_not_awaited()
