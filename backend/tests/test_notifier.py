"""Tests for core.notifier (user-facing booking confirmation email)."""
from __future__ import annotations

from html.parser import HTMLParser

from app.core.notifier import build_email


def _strip_html(html: str) -> str:
    """Tiny tag-stripper so substring assertions can run against rendered text."""

    class Stripper(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.chunks: list[str] = []

        def handle_data(self, data: str) -> None:
            self.chunks.append(data)

    p = Stripper()
    p.feed(html)
    return "".join(p.chunks)


def test_build_email_returns_subject_html_and_text() -> None:
    """Resend multipart needs both html and text; assert build_email exposes both."""
    actions = [
        {
            "type": "calendar",
            "status": "executed",
            "payload": {"start_iso": "2026-05-05T10:00:00+05:30"},
        },
        {"type": "sheets", "status": "executed", "payload": {}},
        {"type": "email", "status": "executed", "payload": {}},
    ]
    msg = build_email(booking_code="NL-AB12", actions=actions, topic="ELSS lock-in")
    assert set(msg.keys()) == {"subject", "html", "text"}
    assert msg["html"].startswith("<!DOCTYPE html>")
    assert msg["text"]
    # Text fallback must not contain HTML tags.
    assert "<table" not in msg["text"]
    assert "<html" not in msg["text"]


def test_build_email_approved_includes_topic_and_ist_slot() -> None:
    """Approved booking email: clear outcome, topic, IST date/time, code.
    No market context (that lives in the advisor draft, not the user inbox)."""
    actions = [
        {
            "type": "calendar",
            "status": "executed",
            "payload": {"start_iso": "2026-05-05T10:00:00+05:30"},
        },
        {"type": "sheets", "status": "executed", "payload": {"slot_iso": "2026-05-05T10:00:00+05:30"}},
        {"type": "email", "status": "executed", "payload": {}},
    ]
    msg = build_email(booking_code="NL-AB12", actions=actions, topic="ELSS lock-in")
    assert msg["subject"] == "Booking NL-AB12: approved"
    text = msg["text"]
    html_text = _strip_html(msg["html"])
    for body in (text, html_text):
        assert "approved" in body
        assert "ELSS lock-in" in body
        assert "Tuesday, May 5 2026 at 10:00 AM IST" in body
        assert "NL-AB12" in body
        # Market context belongs only in the advisor draft.
        assert "Market context" not in body
        assert "Market Context" not in body


def test_build_email_rejected_says_rejected_and_renders_topic_and_slot() -> None:
    actions = [
        {"type": "calendar", "status": "rejected", "payload": {"start_iso": "2026-05-05T10:00:00+05:30"}},
        {"type": "sheets", "status": "rejected", "payload": {}},
        {"type": "email", "status": "rejected", "payload": {}},
    ]
    msg = build_email(booking_code="NL-AB12", actions=actions, topic="KYC")
    assert msg["subject"] == "Booking NL-AB12: rejected"
    for body in (msg["text"], _strip_html(msg["html"])):
        assert "rejected" in body
        assert "KYC" in body
        assert "Tuesday, May 5 2026 at 10:00 AM IST" in body


def test_build_email_partial_approval_uses_partial_verdict() -> None:
    actions = [
        {"type": "calendar", "status": "executed", "payload": {"start_iso": "2026-05-05T10:00:00+05:30"}},
        {"type": "sheets", "status": "rejected", "payload": {}},
        {"type": "email", "status": "executed", "payload": {}},
    ]
    msg = build_email(booking_code="NL-AB12", actions=actions, topic="Switch fund")
    assert msg["subject"] == "Booking NL-AB12: partially approved"
    for body in (msg["text"], _strip_html(msg["html"])):
        assert "partially approved" in body


def test_build_email_handles_missing_slot_gracefully() -> None:
    """If the calendar action's payload doesn't carry a slot (degraded data),
    the body still renders with a 'to be scheduled' placeholder rather than
    crashing or leaking a raw ISO string at the user."""
    actions = [
        {"type": "calendar", "status": "executed", "payload": {}},
        {"type": "sheets", "status": "executed", "payload": {}},
        {"type": "email", "status": "executed", "payload": {}},
    ]
    msg = build_email(booking_code="NL-AB12", actions=actions, topic="general")
    for body in (msg["text"], _strip_html(msg["html"])):
        assert "to be scheduled" in body


def test_build_email_html_escapes_topic_to_block_injection() -> None:
    """A hostile topic with HTML should be escaped, never rendered as markup."""
    actions = [
        {
            "type": "calendar",
            "status": "executed",
            "payload": {"start_iso": "2026-05-05T10:00:00+05:30"},
        },
        {"type": "sheets", "status": "executed", "payload": {}},
        {"type": "email", "status": "executed", "payload": {}},
    ]
    msg = build_email(
        booking_code="NL-AB12",
        actions=actions,
        topic="<script>alert('x')</script> & <b>bold</b>",
    )
    html = msg["html"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html
