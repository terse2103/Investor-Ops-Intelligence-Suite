"""Endpoint tests for /api/approvals/* (admin auth + delegation)."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_list_pending_returns_items(client: TestClient) -> None:
    fake_items = [
        {"id": "a-1", "type": "calendar", "status": "pending", "call_id": "c-1", "payload": {}},
        {"id": "a-2", "type": "email", "status": "pending", "call_id": "c-1", "payload": {}},
    ]
    with patch(
        "app.api.approvals.list_pending",
        return_value=fake_items,
    ):
        resp = client.get("/api/approvals/pending")
    assert resp.status_code == 200
    assert resp.json() == {"items": fake_items}


def test_decide_approve_returns_dispatcher_result(client: TestClient) -> None:
    fake_result = {
        "action_id": "a-1",
        "decision": "approved",
        "execution_status": "executed",
        "notification": None,
    }
    with patch(
        "app.api.approvals.decide_action",
        return_value=fake_result,
    ):
        resp = client.post(
            "/api/approvals/a-1/decide",
            json={"status": "approved"},
        )
    assert resp.status_code == 200
    assert resp.json() == fake_result


def test_decide_invalid_decision_returns_400(client: TestClient) -> None:
    with patch(
        "app.api.approvals.decide_action",
        side_effect=ValueError("decision must be approved or rejected"),
    ):
        resp = client.post(
            "/api/approvals/a-1/decide",
            json={"status": "maybe"},
        )
    assert resp.status_code == 400
    assert "decision must be" in resp.json()["detail"]


def test_decide_dispatcher_failure_returns_502(client: TestClient) -> None:
    with patch(
        "app.api.approvals.decide_action",
        side_effect=RuntimeError("downstream provider down"),
    ):
        resp = client.post(
            "/api/approvals/a-1/decide",
            json={"status": "approved"},
        )
    assert resp.status_code == 502
    assert "Approval dispatch failed" in resp.json()["detail"]
