"""Tests for the POST /api/scrape endpoint (auth + delegation to scrape_reviews)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings

# ---------------------------------------------------------------------------
# Constants
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
    """No X-Scrape-Secret and no Authorization header must be rejected with 401.

    _scrape_auth calls require_auth(authorization) directly (not via Depends), so
    the conftest dependency_overrides do not apply here. The real require_auth
    rejects a missing/None Authorization header with 401.
    """
    mock_scrape = AsyncMock(return_value=FAKE_SCRAPE_RESULT)

    with patch("app.api.scrape.scrape_reviews", mock_scrape):
        resp = client.post("/api/scrape")

    assert resp.status_code == 401
    mock_scrape.assert_not_awaited()


# ---------------------------------------------------------------------------
# Happy-path: admin JWT auth
# ---------------------------------------------------------------------------

def test_scrape_with_admin_jwt_returns_result(client: TestClient) -> None:
    """A bearer token resolving to an admin user should trigger scrape_reviews."""
    mock_scrape = AsyncMock(return_value=FAKE_SCRAPE_RESULT)
    admin_user = {"id": "u1", "email": "a@x.com", "role": "admin"}
    mock_require_auth = AsyncMock(return_value=admin_user)

    with (
        patch("app.api.scrape.scrape_reviews", mock_scrape),
        patch("app.api.scrape.require_auth", mock_require_auth),
    ):
        resp = client.post(
            "/api/scrape",
            headers={"Authorization": "Bearer faketoken"},
        )

    assert resp.status_code == 200
    assert resp.json() == FAKE_SCRAPE_RESULT
    mock_scrape.assert_awaited_once()


# ---------------------------------------------------------------------------
# Auth rejection: non-admin JWT
# ---------------------------------------------------------------------------

def test_scrape_with_user_jwt_returns_403(client: TestClient) -> None:
    """A bearer token resolving to a non-admin user must be rejected with 403."""
    mock_scrape = AsyncMock(return_value=FAKE_SCRAPE_RESULT)
    plain_user = {"id": "u2", "email": "u@x.com", "role": "user"}
    mock_require_auth = AsyncMock(return_value=plain_user)

    with (
        patch("app.api.scrape.scrape_reviews", mock_scrape),
        patch("app.api.scrape.require_auth", mock_require_auth),
    ):
        resp = client.post(
            "/api/scrape",
            headers={"Authorization": "Bearer faketoken"},
        )

    assert resp.status_code == 403
    mock_scrape.assert_not_awaited()
