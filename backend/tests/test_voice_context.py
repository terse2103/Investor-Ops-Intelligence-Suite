"""Tests for voice context loader + /api/voice/context endpoint."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.services.voice.context import (
    IST,
    load_current_themes,
    to_vapi_date_variables,
    to_vapi_variables,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_to_vapi_variables_with_three_themes() -> None:
    out = to_vapi_variables(["Login Issues", "Slow Withdrawals", "KYC Problems"])
    assert out["top_theme_1"] == "Login Issues"
    assert out["top_theme_2"] == "Slow Withdrawals"
    assert out["top_theme_3"] == "KYC Problems"
    assert out["themes_joined"] == "Login Issues, Slow Withdrawals, KYC Problems"
    assert out["themes_count"] == "3"


def test_to_vapi_variables_with_one_theme_blanks_rest() -> None:
    out = to_vapi_variables(["Onboarding"])
    assert out["top_theme_1"] == "Onboarding"
    assert out["top_theme_2"] == ""
    assert out["top_theme_3"] == ""
    assert out["themes_count"] == "1"


def test_to_vapi_variables_with_no_themes_returns_empty_strings() -> None:
    out = to_vapi_variables([])
    assert out["top_theme_1"] == ""
    assert out["themes_joined"] == ""
    assert out["themes_count"] == "0"


# ---------------------------------------------------------------------------
# Date anchors (to_vapi_date_variables)
# ---------------------------------------------------------------------------


def test_date_variables_saturday_skips_weekend() -> None:
    # Saturday 2026-05-02 IST -> next 3 BDs are Mon May 4, Tue May 5, Wed May 6
    saturday = datetime(2026, 5, 2, 9, 0, tzinfo=IST)
    out = to_vapi_date_variables(saturday)
    assert out["today_date_iso"] == "2026-05-02"
    assert out["today_weekday"] == "Saturday"
    assert out["today_human"] == "Saturday, May 2"
    assert out["next_3_business_days_human"] == (
        "Monday, May 4; Tuesday, May 5; Wednesday, May 6"
    )


def test_date_variables_friday_rolls_into_following_week() -> None:
    # Friday 2026-05-01 IST -> next 3 BDs are Mon May 4, Tue May 5, Wed May 6
    friday = datetime(2026, 5, 1, 23, 0, tzinfo=IST)
    out = to_vapi_date_variables(friday)
    assert out["today_weekday"] == "Friday"
    assert out["next_3_business_days_human"] == (
        "Monday, May 4; Tuesday, May 5; Wednesday, May 6"
    )


def test_date_variables_midweek_picks_next_three_weekdays() -> None:
    # Tuesday 2026-05-05 -> Wed May 6, Thu May 7, Fri May 8
    tuesday = datetime(2026, 5, 5, 12, 0, tzinfo=IST)
    out = to_vapi_date_variables(tuesday)
    assert out["today_weekday"] == "Tuesday"
    assert out["next_3_business_days_human"] == (
        "Wednesday, May 6; Thursday, May 7; Friday, May 8"
    )


def test_date_variables_crosses_month_boundary() -> None:
    # Thursday 2026-04-30 -> Fri May 1, Mon May 4, Tue May 5
    thursday = datetime(2026, 4, 30, 12, 0, tzinfo=IST)
    out = to_vapi_date_variables(thursday)
    assert out["today_human"] == "Thursday, April 30"
    assert out["next_3_business_days_human"] == (
        "Friday, May 1; Monday, May 4; Tuesday, May 5"
    )


# ---------------------------------------------------------------------------
# load_current_themes
# ---------------------------------------------------------------------------


def _mock_supabase_with_data(data: list[dict]) -> MagicMock:
    mock_client = MagicMock()
    chain = mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = MagicMock(data=data)
    return mock_client


def test_load_current_themes_handles_pulse_generator_dict_shape() -> None:
    rows = [
        {
            "themes": [
                {"name": "Login Issues", "review_count": 12, "summary": "x"},
                {"name": "Slow Withdrawals", "review_count": 8, "summary": "y"},
                {"name": "KYC Problems", "review_count": 4, "summary": "z"},
            ],
            "updated_at": "2026-04-25T01:00:00+00:00",
        }
    ]
    with patch(
        "app.services.voice.context._supabase",
        return_value=_mock_supabase_with_data(rows),
    ):
        result = load_current_themes()
    assert result == ["Login Issues", "Slow Withdrawals", "KYC Problems"]


def test_load_current_themes_caps_at_three() -> None:
    rows = [
        {
            "themes": [
                {"name": "T1"},
                {"name": "T2"},
                {"name": "T3"},
                {"name": "T4"},
            ]
        }
    ]
    with patch(
        "app.services.voice.context._supabase",
        return_value=_mock_supabase_with_data(rows),
    ):
        result = load_current_themes()
    assert result == ["T1", "T2", "T3"]


def test_load_current_themes_skips_empty_names() -> None:
    rows = [
        {
            "themes": [
                {"name": "  "},  # whitespace
                {"name": "Real Theme"},
                {"name": ""},
            ]
        }
    ]
    with patch(
        "app.services.voice.context._supabase",
        return_value=_mock_supabase_with_data(rows),
    ):
        result = load_current_themes()
    assert result == ["Real Theme"]


def test_load_current_themes_returns_empty_when_singleton_missing() -> None:
    with patch(
        "app.services.voice.context._supabase",
        return_value=_mock_supabase_with_data([]),
    ):
        assert load_current_themes() == []


def test_load_current_themes_swallows_db_errors() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = (
        RuntimeError("network down")
    )
    with patch("app.services.voice.context._supabase", return_value=mock_client):
        assert load_current_themes() == []


# ---------------------------------------------------------------------------
# /api/voice/context endpoint
# ---------------------------------------------------------------------------


def test_voice_context_endpoint_returns_themes_and_variables(
    client: TestClient,
) -> None:
    with patch(
        "app.api.voice.load_current_themes",
        return_value=["Login Issues", "Slow Withdrawals", "KYC Problems"],
    ):
        resp = client.get("/api/voice/context")
    assert resp.status_code == 200
    body = resp.json()
    assert body["themes"] == ["Login Issues", "Slow Withdrawals", "KYC Problems"]
    vars_ = body["variables"]
    assert vars_["top_theme_1"] == "Login Issues"
    assert vars_["top_theme_2"] == "Slow Withdrawals"
    assert vars_["themes_count"] == "3"
    # Date anchors must always be populated so the assistant prompt never
    # interpolates a literal `{{today_*}}` to the caller.
    for key in ("today_date_iso", "today_weekday", "today_human", "next_3_business_days_human"):
        assert vars_[key], f"{key} should be a non-empty string"
    # A fresh booking_code is minted per call; agent reads it via {{booking_code}}.
    import re

    assert re.fullmatch(r"NL-[A-Z0-9]{4}", vars_["booking_code"])
    assert body["booking_code"] == vars_["booking_code"]


def test_voice_context_endpoint_mints_unique_booking_code_per_call(
    client: TestClient,
) -> None:
    """Two back-to-back calls must get distinct booking codes; otherwise the
    assistant repeats the same NL-XXXX across calls (the bug this fixes)."""
    with patch("app.api.voice.load_current_themes", return_value=[]):
        codes = {client.get("/api/voice/context").json()["booking_code"] for _ in range(20)}
    # 20 random 4-char alphanumeric draws: at most one collision is plausible.
    assert len(codes) >= 19


def test_voice_context_endpoint_returns_empty_strings_with_no_pulse(
    client: TestClient,
) -> None:
    with patch("app.api.voice.load_current_themes", return_value=[]):
        resp = client.get("/api/voice/context")
    assert resp.status_code == 200
    body = resp.json()
    assert body["themes"] == []
    vars_ = body["variables"]
    assert vars_["top_theme_1"] == ""
    assert vars_["themes_count"] == "0"
    # Date anchors are independent of pulse availability.
    assert vars_["today_weekday"], "today_weekday should always be set"
