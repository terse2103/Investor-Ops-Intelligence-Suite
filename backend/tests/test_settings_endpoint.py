"""Tests for /api/settings/contact (read + upsert)."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_get_contact_returns_empty_when_no_row(client: TestClient) -> None:
    with patch("app.api.settings._read_contact", return_value=None):
        resp = client.get("/api/settings/contact")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] is None
    assert body["updated_at"] is None


def test_get_contact_returns_existing_row(client: TestClient) -> None:
    row = {"email": "user@example.com", "updated_at": "2026-04-29T01:00:00+00:00"}
    with patch("app.api.settings._read_contact", return_value=row):
        resp = client.get("/api/settings/contact")
    assert resp.status_code == 200
    assert resp.json() == row


def test_post_contact_upserts_and_returns_row(client: TestClient) -> None:
    saved = {"email": "user@example.com", "updated_at": "2026-04-29T01:00:00+00:00"}
    with patch("app.api.settings._upsert_contact", return_value=saved) as up:
        resp = client.post(
            "/api/settings/contact",
            json={"email": "user@example.com"},
        )
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"
    up.assert_called_once_with("test-user-id", "user@example.com")


def test_post_contact_rejects_invalid_email(client: TestClient) -> None:
    resp = client.post("/api/settings/contact", json={"email": "not-an-email"})
    assert resp.status_code == 422


def test_post_contact_502_on_db_failure(client: TestClient) -> None:
    with patch("app.api.settings._upsert_contact", side_effect=RuntimeError("db down")):
        resp = client.post(
            "/api/settings/contact",
            json={"email": "user@example.com"},
        )
    assert resp.status_code == 502
    assert "Failed to save contact" in resp.json()["detail"]
