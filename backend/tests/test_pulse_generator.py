"""Unit tests for pulse generator (services/pulse/generator.py)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.pulse.generator import (
    _format_review_block,
    _parse_json_response,
    _redact_pulse,
    _validate_pulse,
    generate_pulse,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _valid_pulse() -> dict:
    return {
        "themes": [
            {"name": "Login Issues", "review_count": 12, "summary": "Users hit OTP failures."},
            {"name": "Slow Withdrawals", "review_count": 9, "summary": "Multi-day delays."},
            {"name": "KYC Problems", "review_count": 6, "summary": "Re-KYC loops."},
        ],
        "quotes": [
            "OTP never arrives, login broken for days.",
            "My withdrawal has been stuck for 5 days.",
            "Asked to redo KYC three times this month.",
        ],
        "pulse_note": "Top complaint themes this cycle are login OTP failures, slow withdrawals, and repeated KYC asks. Login issues dominate by volume.",
        "actions": [
            "Stabilise OTP delivery via secondary SMS provider.",
            "Add a withdrawal-status banner that surfaces current SLA.",
            "Audit the KYC retrigger heuristic for false positives.",
        ],
    }


def _fake_review(review_id: str, content: str, rating: int = 4) -> dict:
    return {
        "play_review_id": review_id,
        "content": content,
        "rating": rating,
        "posted_at": "2026-04-20T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def test_validate_pulse_accepts_valid_pulse() -> None:
    assert _validate_pulse(_valid_pulse()) == []


def test_validate_pulse_rejects_wrong_theme_count() -> None:
    pulse = _valid_pulse()
    pulse["themes"] = pulse["themes"][:2]
    errors = _validate_pulse(pulse)
    assert any("R-PULSE2" in e for e in errors)


def test_validate_pulse_rejects_wrong_quote_count() -> None:
    pulse = _valid_pulse()
    pulse["quotes"] = pulse["quotes"][:2]
    errors = _validate_pulse(pulse)
    assert any("R-PULSE3" in e for e in errors)


def test_validate_pulse_rejects_wrong_action_count() -> None:
    pulse = _valid_pulse()
    pulse["actions"] = pulse["actions"][:2]
    errors = _validate_pulse(pulse)
    assert any("R-PULSE5" in e for e in errors)


def test_validate_pulse_rejects_long_note() -> None:
    pulse = _valid_pulse()
    pulse["pulse_note"] = " ".join(["word"] * 251)
    errors = _validate_pulse(pulse)
    assert any("R-PULSE4" in e for e in errors)


def test_validate_pulse_rejects_missing_theme_keys() -> None:
    pulse = _valid_pulse()
    pulse["themes"][0] = {"name": "broken"}  # missing review_count
    errors = _validate_pulse(pulse)
    assert any("R-PULSE2" in e for e in errors)


# ---------------------------------------------------------------------------
# JSON parser
# ---------------------------------------------------------------------------


def test_parse_json_strips_markdown_fence() -> None:
    raw = '```json\n{"themes": []}\n```'
    assert _parse_json_response(raw) == {"themes": []}


def test_parse_json_handles_plain_json() -> None:
    raw = '{"themes": [], "actions": []}'
    assert _parse_json_response(raw) == {"themes": [], "actions": []}


def test_parse_json_raises_on_garbage() -> None:
    with pytest.raises(ValueError):
        _parse_json_response("not json at all")


def test_parse_json_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        _parse_json_response("")


# ---------------------------------------------------------------------------
# Redaction (R-PULSE6)
# ---------------------------------------------------------------------------


def test_redact_pulse_redacts_email_in_quote() -> None:
    pulse = _valid_pulse()
    pulse["quotes"][0] = "Email me at user@example.com if you fix it"
    out = _redact_pulse(pulse)
    assert "user@example.com" not in out["quotes"][0]
    assert "[REDACTED]" in out["quotes"][0]


def test_redact_pulse_redacts_phone_in_theme_name() -> None:
    pulse = _valid_pulse()
    pulse["themes"][0]["name"] = "Call me 9876543210"
    out = _redact_pulse(pulse)
    assert "9876543210" not in out["themes"][0]["name"]


def test_redact_pulse_redacts_pulse_note() -> None:
    pulse = _valid_pulse()
    pulse["pulse_note"] = "Contact admin@indmoney.in for details"
    out = _redact_pulse(pulse)
    assert "admin@indmoney.in" not in out["pulse_note"]


# ---------------------------------------------------------------------------
# Review formatter
# ---------------------------------------------------------------------------


def test_format_review_block_includes_rating_and_index() -> None:
    reviews = [_fake_review("r1", "App is great"), _fake_review("r2", "Login broken", rating=2)]
    block = _format_review_block(reviews)
    assert "[1]" in block and "[2]" in block
    assert "rating=4" in block and "rating=2" in block
    assert "App is great" in block


# ---------------------------------------------------------------------------
# generate_pulse end-to-end (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_pulse_happy_path() -> None:
    reviews = [_fake_review(f"r{i}", f"review text number {i} with enough words") for i in range(10)]
    valid_response = json.dumps(_valid_pulse())

    mock_supabase = MagicMock()
    select_chain = mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value
    select_chain.execute.return_value = MagicMock(data=reviews)

    insert_resp = MagicMock(data=[{"id": "pulse-uuid-1"}])
    mock_supabase.table.return_value.insert.return_value.execute.return_value = insert_resp
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.pulse.generator._supabase", return_value=mock_supabase),
        patch(
            "app.services.pulse.generator.complete_text",
            return_value=valid_response,
        ) as mock_llm,
    ):
        result = await generate_pulse()

    assert len(result["themes"]) == 3
    assert len(result["quotes"]) == 3
    assert len(result["actions"]) == 3
    mock_llm.assert_called_once()
    # Pulse persisted (insert) and current_themes upserted
    assert mock_supabase.table.return_value.insert.called
    assert mock_supabase.table.return_value.upsert.called


@pytest.mark.asyncio
async def test_generate_pulse_retries_on_invalid_response() -> None:
    reviews = [_fake_review(f"r{i}", f"review {i} with sufficient word count please") for i in range(5)]

    invalid = json.dumps({"themes": [], "quotes": [], "pulse_note": "", "actions": []})
    valid = json.dumps(_valid_pulse())

    mock_supabase = MagicMock()
    select_chain = mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value
    select_chain.execute.return_value = MagicMock(data=reviews)
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "pulse-uuid-2"}]
    )
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.pulse.generator._supabase", return_value=mock_supabase),
        patch(
            "app.services.pulse.generator.complete_text",
            side_effect=[invalid, valid],
        ) as mock_llm,
    ):
        result = await generate_pulse()

    assert mock_llm.call_count == 2
    assert len(result["themes"]) == 3


@pytest.mark.asyncio
async def test_generate_pulse_raises_after_two_failures() -> None:
    reviews = [_fake_review(f"r{i}", f"review {i} text for testing here please") for i in range(3)]

    invalid = json.dumps({"themes": [], "quotes": [], "pulse_note": "", "actions": []})

    mock_supabase = MagicMock()
    select_chain = mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value
    select_chain.execute.return_value = MagicMock(data=reviews)

    with (
        patch("app.services.pulse.generator._supabase", return_value=mock_supabase),
        patch(
            "app.services.pulse.generator.complete_text",
            side_effect=[invalid, invalid],
        ),
    ):
        with pytest.raises(ValueError, match="failed validation twice"):
            await generate_pulse()


@pytest.mark.asyncio
async def test_generate_pulse_raises_with_no_reviews() -> None:
    mock_supabase = MagicMock()
    select_chain = mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value
    select_chain.execute.return_value = MagicMock(data=[])

    with patch("app.services.pulse.generator._supabase", return_value=mock_supabase):
        with pytest.raises(ValueError, match="no reviews in window"):
            await generate_pulse()


@pytest.mark.asyncio
async def test_generate_pulse_persists_with_correct_fields() -> None:
    reviews = [_fake_review(f"r{i}", f"review number {i} with reasonable length text") for i in range(5)]
    valid_response = json.dumps(_valid_pulse())

    mock_supabase = MagicMock()
    select_chain = mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value
    select_chain.execute.return_value = MagicMock(data=reviews)
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "pulse-uuid-3"}]
    )
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.pulse.generator._supabase", return_value=mock_supabase),
        patch("app.services.pulse.generator.complete_text", return_value=valid_response),
    ):
        await generate_pulse()

    insert_calls = mock_supabase.table.return_value.insert.call_args_list
    assert len(insert_calls) == 1
    pulse_row = insert_calls[0].args[0]
    assert "window_start" in pulse_row
    assert "window_end" in pulse_row
    assert "themes" in pulse_row
    assert "quotes" in pulse_row
    assert "actions" in pulse_row
    assert "note_text" in pulse_row
    assert pulse_row["word_count"] == len(pulse_row["note_text"].split())

    upsert_calls = mock_supabase.table.return_value.upsert.call_args_list
    assert len(upsert_calls) == 1
    themes_payload = upsert_calls[0].args[0]
    assert themes_payload["id"] == 1
    assert themes_payload["pulse_id"] == "pulse-uuid-3"
    assert len(themes_payload["themes"]) == 3
