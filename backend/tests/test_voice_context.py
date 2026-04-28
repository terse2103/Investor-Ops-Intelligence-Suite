"""Tests for voice context loader + /api/voice/context endpoint."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.services.voice.context import load_current_themes, to_vapi_variables


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
    assert body["variables"]["top_theme_1"] == "Login Issues"
    assert body["variables"]["top_theme_2"] == "Slow Withdrawals"
    assert body["variables"]["themes_count"] == "3"


def test_voice_context_endpoint_returns_empty_strings_with_no_pulse(
    client: TestClient,
) -> None:
    with patch("app.api.voice.load_current_themes", return_value=[]):
        resp = client.get("/api/voice/context")
    assert resp.status_code == 200
    body = resp.json()
    assert body["themes"] == []
    assert body["variables"]["top_theme_1"] == ""
    assert body["variables"]["themes_count"] == "0"
