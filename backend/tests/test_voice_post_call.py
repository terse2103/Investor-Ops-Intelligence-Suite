"""Tests for the post-call handler + /api/voice/post-call webhook."""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services.voice.post_call import (
    EMAIL_PAYLOAD_TEMPLATE,
    _build_pending_actions,
    _extract_payload,
    generate_booking_code,
    handle_post_call,
)


WEBHOOK_SECRET = "vapi-test-secret"


@pytest.fixture(autouse=True)
def _set_vapi_webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vapi_webhook_secret", WEBHOOK_SECRET)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_generate_booking_code_format_is_NL_XXXX() -> None:
    code = generate_booking_code()
    assert re.fullmatch(r"NL-[A-Z0-9]{4}", code), code


def test_generate_booking_code_is_random() -> None:
    codes = {generate_booking_code() for _ in range(50)}
    # 50 random 4-char alphanumeric draws from 36 chars: collisions vanishingly rare
    assert len(codes) >= 49


def test_extract_payload_with_wrapped_message() -> None:
    raw = {
        "message": {
            "call": {"id": "call-123", "metadata": {"user_id": "u-1"}},
            "transcript": "agent: hi\nuser: book a slot",
            "analysis": {
                "structuredData": {
                    "topic": "Nominee update",
                    "slot_iso": "2026-04-30T10:00:00+05:30",
                    "intent": "book_new",
                }
            },
        }
    }
    parsed = _extract_payload(raw)
    assert parsed["call_id"] == "call-123"
    assert parsed["user_id"] == "u-1"
    assert parsed["transcript"].startswith("agent: hi")
    assert parsed["topic"] == "Nominee update"
    assert parsed["slot_iso"] == "2026-04-30T10:00:00+05:30"
    assert parsed["intent"] == "book_new"


def test_extract_payload_unwrapped_message_works_too() -> None:
    raw = {
        "callId": "raw-call-9",
        "topic": "Login issues",
        "slot_iso": "2026-05-01T11:00:00+05:30",
    }
    parsed = _extract_payload(raw)
    assert parsed["call_id"] == "raw-call-9"
    assert parsed["topic"] == "Login issues"
    assert parsed["intent"] == "book_new"  # default


def test_extract_payload_rejects_missing_call_id() -> None:
    with pytest.raises(ValueError, match="missing call id"):
        _extract_payload({"message": {"transcript": "hi"}})


def test_extract_payload_normalises_unknown_intent_to_book_new() -> None:
    raw = {
        "message": {
            "call": {"id": "x"},
            "analysis": {"structuredData": {"intent": "totally-bogus"}},
        }
    }
    assert _extract_payload(raw)["intent"] == "book_new"


def test_build_pending_actions_creates_three_with_correct_types() -> None:
    actions = _build_pending_actions(
        call_id="c-1",
        booking_code="NL-AB12",
        topic="KYC",
        slot_iso="2026-05-01T10:00:00+05:30",
        market_context="Login Issues, Slow Withdrawals, KYC Problems",
        user_id="u-1",
    )
    assert [a["type"] for a in actions] == ["calendar", "sheets", "email"]
    assert all(a["status"] == "pending" for a in actions)
    assert all(a["call_id"] == "c-1" for a in actions)


def test_build_pending_actions_email_contains_market_context() -> None:
    """R-APPROVE2: email payload must include Market Context."""
    actions = _build_pending_actions(
        call_id="c-1",
        booking_code="NL-AB12",
        topic="KYC",
        slot_iso="2026-05-01T10:00:00+05:30",
        market_context="Login Issues, Slow Withdrawals, KYC Problems",
        user_id="u-1",
    )
    email = next(a for a in actions if a["type"] == "email")
    assert email["payload"]["market_context"] == (
        "Login Issues, Slow Withdrawals, KYC Problems"
    )
    assert "Market Context" in email["payload"]["body"]
    assert "Login Issues, Slow Withdrawals, KYC Problems" in email["payload"]["body"]


def test_build_pending_actions_calendar_uses_kolkata_tz() -> None:
    actions = _build_pending_actions(
        call_id="c-1",
        booking_code="NL-AB12",
        topic="KYC",
        slot_iso="2026-05-01T10:00:00+05:30",
        market_context="X",
        user_id="u-1",
    )
    calendar = next(a for a in actions if a["type"] == "calendar")
    assert calendar["payload"]["timezone"] == "Asia/Kolkata"
    assert calendar["payload"]["duration_minutes"] == 30
    assert "NL-AB12" in calendar["payload"]["summary"]


# ---------------------------------------------------------------------------
# handle_post_call (end-to-end with mocked Supabase)
# ---------------------------------------------------------------------------


def _mock_supabase_for_post_call(
    themes_data: list[dict] | None = None,
) -> tuple[MagicMock, dict[str, MagicMock]]:
    """Return (client_mock, table_mocks_by_name) so tests can inspect each table.

    Routes .table('current_themes' | 'calls' | 'pending_actions') to a
    dedicated MagicMock kept in the dict, so insert/upsert calls can be
    inspected per-table.
    """
    mock_client = MagicMock()
    tables: dict[str, MagicMock] = {}

    def make_themes_table() -> MagicMock:
        tbl = MagicMock()
        chain = tbl.select.return_value.eq.return_value.limit.return_value
        chain.execute.return_value = MagicMock(data=themes_data or [])
        return tbl

    def make_calls_table() -> MagicMock:
        tbl = MagicMock()
        tbl.upsert.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    def make_pa_table() -> MagicMock:
        tbl = MagicMock()
        tbl.insert.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    tables["current_themes"] = make_themes_table()
    tables["calls"] = make_calls_table()
    tables["pending_actions"] = make_pa_table()

    def route(name: str) -> MagicMock:
        return tables[name]

    mock_client.table.side_effect = route
    return mock_client, tables


def test_handle_post_call_writes_call_and_three_actions() -> None:
    payload = {
        "message": {
            "call": {"id": "call-42", "metadata": {"user_id": "u-1"}},
            "transcript": "agent: hi\nuser: book me",
            "analysis": {
                "structuredData": {
                    "topic": "ELSS lock-in",
                    "slot_iso": "2026-04-30T15:00:00+05:30",
                    "intent": "book_new",
                }
            },
        }
    }
    themes = [
        {"themes": [{"name": "Login Issues"}, {"name": "Slow Withdrawals"}, {"name": "KYC"}]}
    ]
    mock_client, tables = _mock_supabase_for_post_call(themes_data=themes)

    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(payload)

    assert result["call_id"] == "call-42"
    assert re.fullmatch(r"NL-[A-Z0-9]{4}", result["booking_code"])
    assert result["pending_actions"] == 3
    assert result["market_context"] == "Login Issues, Slow Withdrawals, KYC"

    # calls upsert called once with the right id
    tables["calls"].upsert.assert_called_once()
    upserted_row = tables["calls"].upsert.call_args.args[0]
    assert upserted_row["id"] == "call-42"
    assert upserted_row["status"] == "completed"

    # pending_actions insert called once with exactly 3 rows
    tables["pending_actions"].insert.assert_called_once()
    inserted_rows = tables["pending_actions"].insert.call_args.args[0]
    assert len(inserted_rows) == 3
    assert {r["type"] for r in inserted_rows} == {"calendar", "sheets", "email"}


def test_handle_post_call_pii_redacts_transcript_and_topic() -> None:
    """R-VOICE4: PII in transcript or topic must be redacted before persistence."""
    payload = {
        "message": {
            "call": {"id": "call-pii", "metadata": {"user_id": "u-1"}},
            "transcript": "user: my phone is 9876543210 please call",
            "analysis": {
                "structuredData": {
                    "topic": "Email me at user@example.com about KYC",
                    "slot_iso": "2026-05-01T10:00:00+05:30",
                }
            },
        }
    }
    mock_client, tables = _mock_supabase_for_post_call()

    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        handle_post_call(payload)

    call_row = tables["calls"].upsert.call_args.args[0]
    assert "9876543210" not in call_row["transcript"]
    assert "[REDACTED]" in call_row["transcript"]
    assert "user@example.com" not in call_row["topic"]


def test_handle_post_call_no_pulse_uses_fallback_market_context() -> None:
    payload = {
        "message": {
            "call": {"id": "call-mc", "metadata": {"user_id": "u-1"}},
            "transcript": "x",
            "analysis": {"structuredData": {"topic": "T", "slot_iso": "2026-05-01T10:00:00+05:30"}},
        }
    }
    mock_client, _ = _mock_supabase_for_post_call(themes_data=[])

    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(payload)
    assert result["market_context"] == "no current pulse available"


# ---------------------------------------------------------------------------
# Webhook auth
# ---------------------------------------------------------------------------


def test_post_call_webhook_rejects_missing_secret(client: TestClient) -> None:
    resp = client.post("/api/voice/post-call", json={"message": {}})
    assert resp.status_code == 401


def test_post_call_webhook_rejects_wrong_secret(client: TestClient) -> None:
    resp = client.post(
        "/api/voice/post-call",
        json={"message": {}},
        headers={"X-Vapi-Secret": "wrong"},
    )
    assert resp.status_code == 401


def test_post_call_webhook_returns_503_when_secret_unset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "vapi_webhook_secret", "")
    resp = client.post(
        "/api/voice/post-call",
        json={"message": {}},
        headers={"X-Vapi-Secret": "anything"},
    )
    assert resp.status_code == 503


def test_post_call_webhook_returns_400_on_invalid_payload(client: TestClient) -> None:
    resp = client.post(
        "/api/voice/post-call",
        json={"message": {"transcript": "no call id"}},
        headers={"X-Vapi-Secret": WEBHOOK_SECRET},
    )
    assert resp.status_code == 400
    assert "missing call id" in resp.json()["detail"]


def test_post_call_webhook_happy_path(client: TestClient) -> None:
    payload = {
        "message": {
            "call": {"id": "call-ok"},
            "analysis": {"structuredData": {"topic": "T", "slot_iso": "2026-05-01T10:00:00+05:30"}},
        }
    }
    fake_result = {
        "call_id": "call-ok",
        "booking_code": "NL-XYZ9",
        "pending_actions": 3,
        "market_context": "x",
    }
    with patch(
        "app.services.voice.post_call.handle_post_call", return_value=fake_result
    ):
        resp = client.post(
            "/api/voice/post-call",
            json=payload,
            headers={"X-Vapi-Secret": WEBHOOK_SECRET},
        )
    assert resp.status_code == 200
    assert resp.json() == fake_result


def test_email_template_format_is_stable() -> None:
    """Lock the format so future edits surface in PRs."""
    body = EMAIL_PAYLOAD_TEMPLATE.format(
        slot_iso="2026-05-01T10:00:00+05:30",
        topic="KYC",
        booking_code="NL-AB12",
        market_context="Login Issues",
    )
    assert "NL-AB12" in body
    assert "Market Context" in body
    assert "Login Issues" in body
