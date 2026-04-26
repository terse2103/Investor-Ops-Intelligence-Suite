"""Endpoint tests for /api/pulse/generate and /api/pulse/latest."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import require_admin, require_auth
from app.main import app


def _admin() -> dict:
    return {"id": "a1", "email": "admin@x.com", "role": "admin"}


def _user() -> dict:
    return {"id": "u1", "email": "user@x.com", "role": "user"}


def test_generate_pulse_returns_pulse_json(client: TestClient) -> None:
    fake_pulse = {
        "themes": [{"name": "T1", "review_count": 5, "summary": "s"}] * 3,
        "quotes": ["q1", "q2", "q3"],
        "pulse_note": "note",
        "actions": ["a1", "a2", "a3"],
    }
    with patch(
        "app.api.pulse.generate_pulse",
        new=AsyncMock(return_value=fake_pulse),
    ) as mock_gen:
        resp = client.post("/api/pulse/generate")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["themes"]) == 3
    mock_gen.assert_awaited_once()


def test_generate_pulse_returns_422_when_no_reviews(client: TestClient) -> None:
    with patch(
        "app.api.pulse.generate_pulse",
        new=AsyncMock(side_effect=ValueError("no reviews in window")),
    ):
        resp = client.post("/api/pulse/generate")
    assert resp.status_code == 422
    assert "no reviews" in resp.json()["detail"]


def test_generate_pulse_requires_admin() -> None:
    """User-role JWT must hit 403."""
    app.dependency_overrides[require_admin] = require_admin  # restore real impl

    async def fake_user() -> dict:
        return _user()

    app.dependency_overrides[require_auth] = fake_user
    try:
        c = TestClient(app)
        with patch("app.api.pulse.generate_pulse", new=AsyncMock(return_value={})):
            resp = c.post("/api/pulse/generate")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_latest_pulse_returns_row(client: TestClient) -> None:
    fake_row = {
        "id": "p1",
        "themes": [],
        "quotes": [],
        "actions": [],
        "note_text": "x",
        "word_count": 1,
    }
    with patch(
        "app.api.pulse.load_latest_pulse",
        return_value=fake_row,
    ):
        resp = client.get("/api/pulse/latest")
    assert resp.status_code == 200
    assert resp.json()["id"] == "p1"


def test_latest_pulse_returns_404_when_none(client: TestClient) -> None:
    with patch("app.api.pulse.load_latest_pulse", return_value=None):
        resp = client.get("/api/pulse/latest")
    assert resp.status_code == 404
