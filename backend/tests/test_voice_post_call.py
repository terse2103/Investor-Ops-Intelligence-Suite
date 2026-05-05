"""Tests for the post-call handler + /api/voice/post-call webhook."""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services.voice.post_call import (
    _build_pending_actions,
    _extract_payload,
    generate_booking_code,
    handle_post_call,
    render_advisor_email_body,
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


def test_extract_payload_reads_user_id_from_assistant_overrides() -> None:
    """Vapi Web SDK puts metadata at call.assistantOverrides.metadata, not call.metadata.

    Without this fallback, calls.user_id stays NULL and the email-action dispatch
    later fails with "no recipient email configured for booking user".
    """
    raw = {
        "message": {
            "call": {
                "id": "call-overrides",
                "assistantOverrides": {"metadata": {"user_id": "u-from-overrides"}},
            },
        }
    }
    parsed = _extract_payload(raw)
    assert parsed["user_id"] == "u-from-overrides"


def test_extract_payload_user_id_top_level_metadata_wins_over_overrides() -> None:
    """If both paths carry a user_id, prefer the top-level one (more specific)."""
    raw = {
        "message": {
            "call": {
                "id": "call-both",
                "metadata": {"user_id": "u-top"},
                "assistantOverrides": {"metadata": {"user_id": "u-overrides"}},
            },
        }
    }
    assert _extract_payload(raw)["user_id"] == "u-top"


def test_extract_payload_reads_booking_code_from_metadata() -> None:
    """The frontend echoes the call-start booking code via metadata so the
    persisted record matches what the assistant read on the call."""
    raw = {
        "message": {
            "call": {
                "id": "call-bc",
                "metadata": {"user_id": "u-1", "booking_code": "NL-XK42"},
            },
        }
    }
    parsed = _extract_payload(raw)
    assert parsed["booking_code"] == "NL-XK42"


def test_extract_payload_reads_booking_code_from_assistant_overrides() -> None:
    raw = {
        "message": {
            "call": {
                "id": "call-bc-overrides",
                "assistantOverrides": {"metadata": {"booking_code": "NL-AB12"}},
            },
        }
    }
    assert _extract_payload(raw)["booking_code"] == "NL-AB12"


def test_extract_payload_ignores_malformed_metadata_booking_code() -> None:
    """Anything that doesn't match NL-[A-Z0-9]{4} is dropped; handler falls
    back to server-side generation rather than persist garbage."""
    raw = {
        "message": {
            "call": {"id": "call-bad", "metadata": {"booking_code": "totally bogus"}},
        }
    }
    assert _extract_payload(raw)["booking_code"] is None


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
        advisor_email="advisor@example.com",
    )
    assert [a["type"] for a in actions] == ["calendar", "sheets", "email"]
    assert all(a["status"] == "pending" for a in actions)
    assert all(a["call_id"] == "c-1" for a in actions)


def test_build_pending_actions_email_targets_advisor_with_market_context() -> None:
    """R-APPROVE2 (refined): the Gmail draft is the advisor's, carries the
    booking details, and embeds a topic-relevant pulse snippet. The user's
    own confirmation is generated separately by core/notifier.py."""
    actions = _build_pending_actions(
        call_id="c-1",
        booking_code="NL-AB12",
        topic="KYC",
        slot_iso="2026-05-01T10:00:00+05:30",
        market_context="Theme: KYC Problems — Repeated KYC asks frustrate users.",
        user_id="u-1",
        advisor_email="advisor@example.com",
    )
    email = next(a for a in actions if a["type"] == "email")
    payload = email["payload"]
    assert payload["to"] == "advisor@example.com"
    assert payload["audience"] == "advisor"
    assert payload["mime_type"] == "text/html"
    assert payload["market_context"] == (
        "Theme: KYC Problems — Repeated KYC asks frustrate users."
    )
    # body is HTML, text is the plaintext fallback. Substring checks run
    # against text to stay readable; html gets a smoke check.
    assert payload["body"].startswith("<!DOCTYPE html>")
    text = payload["text"]
    assert "Market context" in text
    assert "KYC Problems" in text
    assert "NL-AB12" in text
    assert "Friday, May 1 2026 at 10:00 AM IST" in text
    assert "Topic" in text and "KYC" in text


def test_build_pending_actions_email_to_is_none_when_advisor_unset() -> None:
    actions = _build_pending_actions(
        call_id="c-1",
        booking_code="NL-AB12",
        topic="KYC",
        slot_iso="2026-05-01T10:00:00+05:30",
        market_context="X",
        user_id="u-1",
        advisor_email=None,
    )
    email = next(a for a in actions if a["type"] == "email")
    assert email["payload"]["to"] is None


def test_build_pending_actions_calendar_uses_kolkata_tz() -> None:
    actions = _build_pending_actions(
        call_id="c-1",
        booking_code="NL-AB12",
        topic="KYC",
        slot_iso="2026-05-01T10:00:00+05:30",
        market_context="X",
        user_id="u-1",
        advisor_email="advisor@example.com",
    )
    calendar = next(a for a in actions if a["type"] == "calendar")
    assert calendar["payload"]["timezone"] == "Asia/Kolkata"
    assert calendar["payload"]["duration_minutes"] == 30
    assert "NL-AB12" in calendar["payload"]["summary"]


# ---------------------------------------------------------------------------
# handle_post_call (end-to-end with mocked Supabase)
# ---------------------------------------------------------------------------


def _mock_supabase_for_post_call(
    pulses_data: list[dict] | None = None,
    themes_data: list[dict] | None = None,
) -> tuple[MagicMock, dict[str, MagicMock]]:
    """Return (client_mock, table_mocks_by_name) so tests can inspect each table.

    Routes .table('pulses' | 'current_themes' | 'calls' | 'pending_actions')
    to a dedicated MagicMock kept in the dict, so insert/upsert calls can be
    inspected per-table.

    `pulses_data` feeds the latest-pulse lookup used by the topic-aware market
    context snippet. `themes_data` is kept for legacy callers that still want
    to populate current_themes (no longer read by post_call but useful if any
    other code path under test queries it).
    """
    mock_client = MagicMock()
    tables: dict[str, MagicMock] = {}

    def make_pulses_table() -> MagicMock:
        tbl = MagicMock()
        # _load_latest_pulse: select(...).order(...).limit(...).execute()
        chain = tbl.select.return_value.order.return_value.limit.return_value
        chain.execute.return_value = MagicMock(data=pulses_data or [])
        return tbl

    def make_themes_table() -> MagicMock:
        tbl = MagicMock()
        chain = tbl.select.return_value.eq.return_value.limit.return_value
        chain.execute.return_value = MagicMock(data=themes_data or [])
        return tbl

    def make_calls_table() -> MagicMock:
        tbl = MagicMock()
        tbl.upsert.return_value.execute.return_value = MagicMock(data=[])
        # _existing_call: select(...).eq(...).limit(...).execute() → no prior call
        tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    def make_pa_table() -> MagicMock:
        tbl = MagicMock()
        tbl.insert.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    tables["pulses"] = make_pulses_table()
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
    # Topic "ELSS lock-in" doesn't overlap with any theme tokens (login,
    # withdrawals, kyc), so the snippet falls back to the joined top-3 names.
    pulses = [
        {
            "themes": [
                {"name": "Login Issues", "summary": "Users report repeated login failures."},
                {"name": "Slow Withdrawals", "summary": "Withdrawals taking 3-4 days."},
                {"name": "KYC", "summary": "Repeated KYC asks."},
            ],
            "quotes": ["q1", "q2", "q3"],
        }
    ]
    mock_client, tables = _mock_supabase_for_post_call(pulses_data=pulses)

    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(payload)

    assert result["call_id"] == "call-42"
    assert re.fullmatch(r"NL-[A-Z0-9]{4}", result["booking_code"])
    assert result["pending_actions"] == 3
    assert result["market_context"] == (
        "Top investor themes this week: Login Issues, Slow Withdrawals, KYC"
    )

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


def test_handle_post_call_persists_metadata_booking_code() -> None:
    """The booking_code from call metadata wins over a fresh generation, so
    the persisted code matches the one the assistant read on the call."""
    payload = {
        "message": {
            "call": {
                "id": "call-bc-persist",
                "metadata": {"user_id": "u-1", "booking_code": "NL-Z9Q3"},
            },
            "transcript": "x",
            "analysis": {"structuredData": {"topic": "T", "slot_iso": "2026-05-01T10:00:00+05:30"}},
        }
    }
    mock_client, tables = _mock_supabase_for_post_call()

    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(payload)

    assert result["booking_code"] == "NL-Z9Q3"
    upserted_row = tables["calls"].upsert.call_args.args[0]
    assert upserted_row["booking_code"] == "NL-Z9Q3"
    inserted_rows = tables["pending_actions"].insert.call_args.args[0]
    for row in inserted_rows:
        if row["type"] == "email":
            assert "NL-Z9Q3" in row["payload"]["text"]
            assert row["payload"]["booking_code"] == "NL-Z9Q3"


def test_handle_post_call_falls_back_to_generation_when_metadata_missing() -> None:
    """No metadata booking_code → handler still mints one (legacy / non-web flow)."""
    payload = {
        "message": {
            "call": {"id": "call-no-bc", "metadata": {"user_id": "u-1"}},
            "transcript": "x",
            "analysis": {"structuredData": {"topic": "T", "slot_iso": "2026-05-01T10:00:00+05:30"}},
        }
    }
    mock_client, _ = _mock_supabase_for_post_call()

    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(payload)

    assert re.fullmatch(r"NL-[A-Z0-9]{4}", result["booking_code"])


def _payload_with_structured(
    *, call_id: str = "call-x", topic: str = "ELSS", slot_iso: str = "2026-05-05T10:00:00+05:30",
    intent: str = "book_new",
) -> dict:
    """Helper for skip-actions tests: build a minimal Vapi end-of-call envelope."""
    return {
        "message": {
            "call": {"id": call_id, "metadata": {"user_id": "u-1"}},
            "transcript": "x",
            "analysis": {
                "structuredData": {
                    "topic": topic,
                    "slot_iso": slot_iso,
                    "intent": intent,
                }
            },
        }
    }


def test_handle_post_call_skips_actions_when_topic_missing() -> None:
    """Empty topic → call ends without a booking; no pending_actions queued."""
    mock_client, tables = _mock_supabase_for_post_call()
    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(_payload_with_structured(topic=""))

    assert result["booking_captured"] is False
    assert result["pending_actions"] == 0
    tables["pending_actions"].insert.assert_not_called()
    # The call is still persisted for audit, but marked abandoned.
    upserted_row = tables["calls"].upsert.call_args.args[0]
    assert upserted_row["status"] == "abandoned"


def test_handle_post_call_skips_actions_when_slot_missing() -> None:
    """No slot_iso captured → no booking, no pending_actions."""
    mock_client, tables = _mock_supabase_for_post_call()
    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(_payload_with_structured(slot_iso=""))

    assert result["booking_captured"] is False
    assert result["pending_actions"] == 0
    tables["pending_actions"].insert.assert_not_called()
    upserted_row = tables["calls"].upsert.call_args.args[0]
    assert upserted_row["status"] == "abandoned"


def test_handle_post_call_skips_actions_when_slot_malformed() -> None:
    """A non-ISO slot string (Vapi's analysis got confused) → no booking."""
    mock_client, tables = _mock_supabase_for_post_call()
    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(_payload_with_structured(slot_iso="next Tuesday"))

    assert result["booking_captured"] is False
    assert result["pending_actions"] == 0
    tables["pending_actions"].insert.assert_not_called()


def test_handle_post_call_skips_actions_for_cancel_intent() -> None:
    """A cancellation should never queue calendar/sheets/email actions."""
    mock_client, tables = _mock_supabase_for_post_call()
    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(_payload_with_structured(intent="cancel"))

    assert result["booking_captured"] is False
    tables["pending_actions"].insert.assert_not_called()


def test_handle_post_call_writes_actions_when_booking_is_complete() -> None:
    """Full topic + slot + book_new intent → 3 pending_actions queued, status=completed."""
    mock_client, tables = _mock_supabase_for_post_call()
    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(_payload_with_structured())

    assert result["booking_captured"] is True
    assert result["pending_actions"] == 3
    tables["pending_actions"].insert.assert_called_once()
    upserted_row = tables["calls"].upsert.call_args.args[0]
    assert upserted_row["status"] == "completed"


def test_handle_post_call_no_pulse_uses_fallback_market_context() -> None:
    payload = {
        "message": {
            "call": {"id": "call-mc", "metadata": {"user_id": "u-1"}},
            "transcript": "x",
            "analysis": {"structuredData": {"topic": "T", "slot_iso": "2026-05-01T10:00:00+05:30"}},
        }
    }
    mock_client, _ = _mock_supabase_for_post_call(pulses_data=[])

    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(payload)
    assert result["market_context"] == "no current pulse available"


def test_handle_post_call_picks_topic_relevant_theme_for_advisor_email() -> None:
    """Topic-aware market context: the advisor draft should embed the theme
    whose tokens match the booking's topic, plus the matching verbatim quote."""
    payload = {
        "message": {
            "call": {"id": "call-topic-match", "metadata": {"user_id": "u-1"}},
            "transcript": "x",
            "analysis": {
                "structuredData": {
                    "topic": "Withdrawal failure investigation",
                    "slot_iso": "2026-05-01T10:00:00+05:30",
                }
            },
        }
    }
    pulses = [
        {
            "themes": [
                {"name": "Login Issues", "summary": "OTP failures dominate this cycle."},
                {"name": "Slow Withdrawals", "summary": "Withdrawal requests stall for 3-4 days."},
                {"name": "KYC", "summary": "Repeated KYC asks frustrate users."},
            ],
            "quotes": [
                "Cannot log in for two days.",
                "My withdrawal has been pending forever.",
                "They keep asking for KYC documents.",
            ],
        }
    ]
    mock_client, tables = _mock_supabase_for_post_call(pulses_data=pulses)

    with patch("app.services.voice.post_call._supabase", return_value=mock_client):
        result = handle_post_call(payload)

    assert "Slow Withdrawals" in result["market_context"]
    assert "stall for 3-4 days" in result["market_context"]
    assert "withdrawal has been pending forever" in result["market_context"].lower()

    inserted_rows = tables["pending_actions"].insert.call_args.args[0]
    email = next(r for r in inserted_rows if r["type"] == "email")
    text = email["payload"]["text"]
    assert "Slow Withdrawals" in text
    assert "stall for 3-4 days" in text


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
        json={"message": {"type": "end-of-call-report", "transcript": "no call id"}},
        headers={"X-Vapi-Secret": WEBHOOK_SECRET},
    )
    assert resp.status_code == 400
    assert "missing call id" in resp.json()["detail"]


def test_post_call_webhook_happy_path(client: TestClient) -> None:
    payload = {
        "message": {
            "type": "end-of-call-report",
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


def test_render_advisor_email_body_returns_html_and_text_with_key_fields() -> None:
    """Lock the advisor-email rendered output (html + text) so future edits surface in PRs."""
    html, text = render_advisor_email_body(
        topic="KYC",
        slot_human="Friday, May 1 2026 at 10:00 AM IST",
        booking_code="NL-AB12",
        market_context="Theme: KYC — Repeated KYC asks frustrate users.",
    )
    assert html.startswith("<!DOCTYPE html>")
    # All the booking-critical fields land in the plaintext fallback verbatim.
    assert "NL-AB12" in text
    assert "Market context" in text
    assert "Theme: KYC" in text
    assert "Repeated KYC asks" in text
    assert "Friday, May 1 2026 at 10:00 AM IST" in text
    # HTML carries the same data points (escape-free since none of these inputs
    # contain HTML metacharacters).
    assert "NL-AB12" in html
    assert "Market context" in html
    assert "Friday, May 1 2026 at 10:00 AM IST" in html


def test_render_advisor_email_body_html_escapes_hostile_topic() -> None:
    """A topic that includes raw HTML must come out HTML-escaped, not as live markup."""
    html, text = render_advisor_email_body(
        topic="<script>alert('x')</script>",
        slot_human="Friday, May 1 2026 at 10:00 AM IST",
        booking_code="NL-AB12",
        market_context="A & B",
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html
    # Plaintext keeps the raw characters (it's not rendered as markup).
    assert "<script>" in text
    assert "A & B" in text


def test_render_advisor_email_body_html_parses_without_error() -> None:
    """The rendered HTML should be well-formed enough that html.parser doesn't crash."""
    from html.parser import HTMLParser

    html, _ = render_advisor_email_body(
        topic="KYC",
        slot_human="Friday, May 1 2026 at 10:00 AM IST",
        booking_code="NL-AB12",
        market_context="Theme: KYC.",
    )

    class TagCounter(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.tag_count = 0

        def handle_starttag(self, tag: str, attrs: list) -> None:  # type: ignore[override]
            self.tag_count += 1

    counter = TagCounter()
    counter.feed(html)
    # Card has at least html, body, an outer table, and several rows: well into double digits.
    assert counter.tag_count >= 10
