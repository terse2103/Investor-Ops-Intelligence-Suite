"""Tests for services.approvals.dispatcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.approvals import dispatcher


def _mock_client_for_dispatcher(
    *,
    actions_by_id: dict[str, dict] | None = None,
    calls_by_id: dict[str, dict] | None = None,
    sibling_actions: list[dict] | None = None,
    user_contacts: dict[str, str] | None = None,
    notifications_existing: list[dict] | None = None,
) -> tuple[MagicMock, dict[str, MagicMock]]:
    """Routed Supabase mock for dispatcher tests.

    Returns the client mock and a per-table dict so tests can inspect calls.
    """
    actions_by_id = actions_by_id or {}
    calls_by_id = calls_by_id or {}
    sibling_actions = sibling_actions or []
    user_contacts = user_contacts or {}
    notifications_existing = notifications_existing or []

    tables: dict[str, MagicMock] = {
        "pending_actions": MagicMock(),
        "calls": MagicMock(),
        "user_contacts": MagicMock(),
        "notifications_sent": MagicMock(),
        "action_audit": MagicMock(),
    }

    def pa_select(_arg: str = "*") -> MagicMock:
        sel = MagicMock()

        def eq(field: str, value: str) -> MagicMock:
            chain = MagicMock()
            if field == "id":
                row = actions_by_id.get(value)
                chain.limit.return_value.execute.return_value = MagicMock(
                    data=[row] if row else []
                )
            elif field == "call_id":
                chain.execute.return_value = MagicMock(data=sibling_actions)
            return chain

        sel.eq.side_effect = eq
        return sel

    tables["pending_actions"].select.side_effect = pa_select
    tables["pending_actions"].update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    tables["pending_actions"].select_full = MagicMock()

    def calls_select(_arg: str = "*") -> MagicMock:
        sel = MagicMock()

        def eq(field: str, value: str) -> MagicMock:
            chain = MagicMock()
            row = calls_by_id.get(value)
            chain.limit.return_value.execute.return_value = MagicMock(
                data=[row] if row else []
            )
            return chain

        sel.eq.side_effect = eq
        return sel

    tables["calls"].select.side_effect = calls_select

    def uc_select(_arg: str = "email") -> MagicMock:
        sel = MagicMock()

        def eq(field: str, value: str) -> MagicMock:
            chain = MagicMock()
            email = user_contacts.get(value)
            chain.limit.return_value.execute.return_value = MagicMock(
                data=[{"email": email}] if email else []
            )
            return chain

        sel.eq.side_effect = eq
        return sel

    tables["user_contacts"].select.side_effect = uc_select

    def ns_select(_arg: str = "id") -> MagicMock:
        sel = MagicMock()

        def eq(field: str, value: str) -> MagicMock:
            chain = MagicMock()
            chain.limit.return_value.execute.return_value = MagicMock(
                data=notifications_existing
            )
            return chain

        sel.eq.side_effect = eq
        return sel

    tables["notifications_sent"].select.side_effect = ns_select

    tables["action_audit"].insert.return_value.execute.return_value = MagicMock(data=[])

    client = MagicMock()
    client.table.side_effect = lambda name: tables[name]
    return client, tables


# ---------------------------------------------------------------------------
# decide_action: validation
# ---------------------------------------------------------------------------


def test_decide_action_rejects_unknown_decision() -> None:
    with pytest.raises(ValueError, match="decision must be"):
        dispatcher.decide_action("any-id", decision="maybe", decided_by=None)


def test_decide_action_404_when_action_missing() -> None:
    client, _ = _mock_client_for_dispatcher()
    with patch("app.services.approvals.dispatcher._supabase", return_value=client):
        with pytest.raises(ValueError, match="not found"):
            dispatcher.decide_action("missing-id", decision="approved", decided_by="u-1")


def test_decide_action_rejects_already_decided() -> None:
    client, _ = _mock_client_for_dispatcher(
        actions_by_id={"a-1": {"id": "a-1", "type": "calendar", "status": "executed", "call_id": "c-1", "payload": {}}},
    )
    with patch("app.services.approvals.dispatcher._supabase", return_value=client):
        with pytest.raises(ValueError, match="already executed"):
            dispatcher.decide_action("a-1", decision="approved", decided_by="u-1")


# ---------------------------------------------------------------------------
# Reject path: no execution, no audit
# ---------------------------------------------------------------------------


def test_reject_does_not_execute_or_audit() -> None:
    action = {
        "id": "a-1",
        "type": "calendar",
        "status": "pending",
        "call_id": "c-1",
        "payload": {"start_iso": "2026-05-01T10:00:00+05:30"},
    }
    client, tables = _mock_client_for_dispatcher(
        actions_by_id={"a-1": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": None, "booking_code": "NL-AB12"}},
        sibling_actions=[
            {"type": "calendar", "status": "rejected"},
            {"type": "sheets", "status": "pending"},
            {"type": "email", "status": "pending"},
        ],
    )
    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch("app.services.approvals.dispatcher.google_api") as gapi,
        patch("app.services.approvals.dispatcher.notifier") as notif,
    ):
        result = dispatcher.decide_action("a-1", decision="rejected", decided_by="admin-1")

    assert result["decision"] == "rejected"
    assert result["execution_status"] is None
    gapi.create_tentative_event.assert_not_called()
    gapi.append_booking_row.assert_not_called()
    tables["action_audit"].insert.assert_not_called()
    notif.notify_booking_decision.assert_not_called()


# ---------------------------------------------------------------------------
# Approve calendar: executes, audits, no premature notify
# ---------------------------------------------------------------------------


def test_approve_calendar_executes_and_audits() -> None:
    action = {
        "id": "a-1",
        "type": "calendar",
        "status": "pending",
        "call_id": "c-1",
        "payload": {
            "start_iso": "2026-05-01T10:00:00+05:30",
            "duration_minutes": 30,
            "timezone": "Asia/Kolkata",
            "summary": "Advisor consultation",
        },
    }
    client, tables = _mock_client_for_dispatcher(
        actions_by_id={"a-1": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": "u-1", "booking_code": "NL-AB12"}},
        user_contacts={"u-1": "user@example.com"},
        sibling_actions=[
            {"type": "calendar", "status": "executed"},
            {"type": "sheets", "status": "pending"},
            {"type": "email", "status": "pending"},
        ],
    )
    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch("app.services.approvals.dispatcher.google_api.create_tentative_event") as cal,
        patch("app.services.approvals.dispatcher.notifier") as notif,
    ):
        cal.return_value = {"id": "ev-1", "htmlLink": "https://calendar.google.com/event?eid=x"}
        result = dispatcher.decide_action("a-1", decision="approved", decided_by="admin-1")

    cal.assert_called_once()
    tables["action_audit"].insert.assert_called_once()
    audit_row = tables["action_audit"].insert.call_args.args[0]
    assert audit_row["pending_action_id"] == "a-1"
    assert audit_row["status"] == "ok"
    assert result["execution_status"] == "executed"
    notif.notify_booking_decision.assert_not_called()  # one sibling still pending


def test_approve_email_routes_to_advisor_from_payload() -> None:
    """Email actions target the advisor email baked into the payload.to field
    (post-call sets it from settings.advisor_email). The booking user gets
    their own confirmation through core/notifier.py, not this draft."""
    action = {
        "id": "a-2",
        "type": "email",
        "status": "pending",
        "call_id": "c-1",
        "payload": {
            "subject": "Booking",
            "body": "...",
            "market_context": "x",
            "booking_code": "NL-AB12",
            "to": "advisor@example.com",
            "audience": "advisor",
        },
    }
    client, _ = _mock_client_for_dispatcher(
        actions_by_id={"a-2": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": "u-1", "booking_code": "NL-AB12"}},
        user_contacts={"u-1": "user@example.com"},  # not used for the draft anymore
        sibling_actions=[
            {"type": "calendar", "status": "executed"},
            {"type": "sheets", "status": "executed"},
            {"type": "email", "status": "executed"},
        ],
        notifications_existing=[],
    )
    captured: dict[str, str | None] = {"to": None}

    async def fake_create_draft(*, payload: dict, to: str) -> dict:
        captured["to"] = to
        return {"draftId": "draft-1"}

    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch("app.services.approvals.dispatcher.mcp_client.create_draft", side_effect=fake_create_draft),
        patch("app.services.approvals.dispatcher.notifier") as notif,
    ):
        notif.notify_booking_decision.return_value = {"status": "sent"}
        result = dispatcher.decide_action("a-2", decision="approved", decided_by="admin-1")

    assert captured["to"] == "advisor@example.com"
    assert result["execution_status"] == "executed"
    notif.notify_booking_decision.assert_called_once()


def test_approve_email_falls_back_to_user_contact_when_advisor_unset() -> None:
    """Legacy path: if no advisor email was baked into the payload (e.g. the
    booking was created before ADVISOR_EMAIL was configured), the dispatcher
    still routes the draft to the user's contact email rather than failing."""
    action = {
        "id": "a-2b",
        "type": "email",
        "status": "pending",
        "call_id": "c-1",
        "payload": {"subject": "Booking", "body": "...", "booking_code": "NL-AB12"},
    }
    client, _ = _mock_client_for_dispatcher(
        actions_by_id={"a-2b": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": "u-1", "booking_code": "NL-AB12"}},
        user_contacts={"u-1": "user@example.com"},
        sibling_actions=[
            {"type": "calendar", "status": "pending"},
            {"type": "sheets", "status": "pending"},
            {"type": "email", "status": "executed"},
        ],
    )
    captured: dict[str, str | None] = {"to": None}

    async def fake_create_draft(*, payload: dict, to: str) -> dict:
        captured["to"] = to
        return {"draftId": "draft-legacy"}

    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch("app.services.approvals.dispatcher.mcp_client.create_draft", side_effect=fake_create_draft),
        patch("app.services.approvals.dispatcher.notifier"),
    ):
        result = dispatcher.decide_action("a-2b", decision="approved", decided_by="admin-1")

    assert captured["to"] == "user@example.com"
    assert result["execution_status"] == "executed"


def test_approve_email_skipped_when_gmail_mcp_unconfigured(monkeypatch) -> None:
    """When GMAIL_MCP_COMMAND is intentionally blank (deployment cut-line:
    no MCP server hosted), email actions are recorded as 'executed' with a
    skip marker in the audit row, not 'failed'. The booking flow stays clean
    and the user-facing notifier sees an all-approved state."""
    monkeypatch.setattr(dispatcher.settings, "gmail_mcp_command", "")

    action = {
        "id": "a-skip",
        "type": "email",
        "status": "pending",
        "call_id": "c-1",
        "payload": {
            "subject": "Booking",
            "body": "...",
            "booking_code": "NL-SKIP",
            "to": "advisor@example.com",
        },
    }
    client, tables = _mock_client_for_dispatcher(
        actions_by_id={"a-skip": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": "u-1", "booking_code": "NL-SKIP"}},
        sibling_actions=[
            {"type": "calendar", "status": "executed"},
            {"type": "sheets", "status": "executed"},
            {"type": "email", "status": "executed"},
        ],
    )

    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch("app.services.approvals.dispatcher.mcp_client.create_draft") as create_draft_mock,
        patch("app.services.approvals.dispatcher.notifier") as notif,
    ):
        notif.notify_booking_decision.return_value = {"status": "sent"}
        result = dispatcher.decide_action("a-skip", decision="approved", decided_by="admin-1")

    create_draft_mock.assert_not_called()
    assert result["execution_status"] == "executed"
    audit_row = tables["action_audit"].insert.call_args.args[0]
    assert audit_row["status"] == "ok"
    assert audit_row["error_message"] is None
    assert audit_row["provider_response"]["skipped"] is True
    assert audit_row["provider_response"]["would_have_sent_to"] == "advisor@example.com"


def test_approve_email_fails_when_no_advisor_and_no_user_contact() -> None:
    action = {
        "id": "a-3",
        "type": "email",
        "status": "pending",
        "call_id": "c-1",
        "payload": {"subject": "x", "body": "y"},
    }
    client, tables = _mock_client_for_dispatcher(
        actions_by_id={"a-3": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": "u-1", "booking_code": "NL-AB12"}},
        user_contacts={},  # no contact saved
        sibling_actions=[
            {"type": "email", "status": "failed"},
            {"type": "calendar", "status": "pending"},
            {"type": "sheets", "status": "pending"},
        ],
    )
    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch("app.services.approvals.dispatcher.notifier"),
    ):
        result = dispatcher.decide_action("a-3", decision="approved", decided_by="admin-1")
    assert result["execution_status"] == "failed"
    audit_row = tables["action_audit"].insert.call_args.args[0]
    assert audit_row["status"] == "failed"
    assert "no recipient email" in audit_row["error_message"]


def test_approve_executes_and_logs_failure_when_provider_raises() -> None:
    action = {
        "id": "a-4",
        "type": "sheets",
        "status": "pending",
        "call_id": "c-1",
        "payload": {"booking_code": "NL-AB12", "user_id": "u-1", "topic": "x", "slot_iso": "x", "created_at": "x"},
    }
    client, tables = _mock_client_for_dispatcher(
        actions_by_id={"a-4": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": "u-1", "booking_code": "NL-AB12"}},
        sibling_actions=[
            {"type": "sheets", "status": "failed"},
            {"type": "calendar", "status": "pending"},
            {"type": "email", "status": "pending"},
        ],
    )
    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch(
            "app.services.approvals.dispatcher.google_api.append_booking_row",
            side_effect=RuntimeError("api quota exceeded"),
        ),
        patch("app.services.approvals.dispatcher.notifier"),
    ):
        result = dispatcher.decide_action("a-4", decision="approved", decided_by="admin-1")
    assert result["execution_status"] == "failed"
    audit_row = tables["action_audit"].insert.call_args.args[0]
    assert audit_row["status"] == "failed"
    assert "api quota exceeded" in audit_row["error_message"]


# ---------------------------------------------------------------------------
# Notification gating
# ---------------------------------------------------------------------------


def test_notify_only_fires_when_all_three_siblings_terminal() -> None:
    action = {
        "id": "a-5",
        "type": "calendar",
        "status": "pending",
        "call_id": "c-1",
        "payload": {"start_iso": "2026-05-01T10:00:00+05:30"},
    }
    client, _ = _mock_client_for_dispatcher(
        actions_by_id={"a-5": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": "u-1", "booking_code": "NL-AB12"}},
        user_contacts={"u-1": "u@x.com"},
        sibling_actions=[
            {"type": "calendar", "status": "executed"},
            {"type": "sheets", "status": "rejected"},
            {"type": "email", "status": "executed"},
        ],
        notifications_existing=[],
    )
    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch("app.services.approvals.dispatcher.google_api.create_tentative_event", return_value={"id": "ev"}),
        patch("app.services.approvals.dispatcher.notifier") as notif,
    ):
        notif.notify_booking_decision.return_value = {"status": "sent"}
        dispatcher.decide_action("a-5", decision="approved", decided_by="admin-1")
    notif.notify_booking_decision.assert_called_once()


def test_notify_does_not_fire_twice_for_same_call() -> None:
    action = {
        "id": "a-6",
        "type": "calendar",
        "status": "pending",
        "call_id": "c-1",
        "payload": {"start_iso": "2026-05-01T10:00:00+05:30"},
    }
    client, _ = _mock_client_for_dispatcher(
        actions_by_id={"a-6": action},
        calls_by_id={"c-1": {"id": "c-1", "user_id": "u-1", "booking_code": "NL-AB12"}},
        user_contacts={"u-1": "u@x.com"},
        sibling_actions=[
            {"type": "calendar", "status": "executed"},
            {"type": "sheets", "status": "executed"},
            {"type": "email", "status": "executed"},
        ],
        notifications_existing=[{"id": "n-1"}],  # already sent earlier
    )
    with (
        patch("app.services.approvals.dispatcher._supabase", return_value=client),
        patch("app.services.approvals.dispatcher.google_api.create_tentative_event", return_value={"id": "ev"}),
        patch("app.services.approvals.dispatcher.notifier") as notif,
    ):
        result = dispatcher.decide_action("a-6", decision="approved", decided_by="admin-1")
    notif.notify_booking_decision.assert_not_called()
    assert result["notification"] == {"status": "already_sent"}
