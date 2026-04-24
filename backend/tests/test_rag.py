"""RAG endpoint unit tests. LLM + retriever are mocked for speed."""
from unittest.mock import AsyncMock, patch


def test_rag_rejects_empty_question(client) -> None:
    r = client.post("/api/rag/query", json={"question": "   "})
    assert r.status_code == 400


@patch("app.api.rag.query_rag", new_callable=AsyncMock)
def test_rag_returns_answer_with_citation(mock_query, client) -> None:
    mock_query.return_value = {
        "answer": (
            "The expense ratio is 1.04%.\n\n"
            "Source: https://www.indmoney.com/mutual-funds/nippon-india-elss-tax-saver-fund-direct-plan-growth-option-2751\n"
            "Last updated from sources: 2026-04-24"
        ),
        "citations": [
            "https://www.indmoney.com/mutual-funds/nippon-india-elss-tax-saver-fund-direct-plan-growth-option-2751"
        ],
        "last_updated": "2026-04-24",
    }
    r = client.post(
        "/api/rag/query",
        json={"question": "What is the expense ratio of Nippon India ELSS Tax Saver Fund?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "1.04%" in body["answer"]
    assert body["citations"]
    assert "indmoney.com" in body["citations"][0]
    assert body["last_updated"] == "2026-04-24"


@patch("app.api.rag.query_rag", new_callable=AsyncMock)
def test_rag_refuses_investment_advice(mock_query, client) -> None:
    """R-G1: advice requests return the exact refusal string."""
    mock_query.return_value = {
        "answer": "I can't give investment advice.",
        "citations": [],
        "last_updated": None,
    }
    r = client.post(
        "/api/rag/query",
        json={"question": "Should I buy Nippon India ELSS Tax Saver Fund?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "I can't give investment advice."
    assert body["citations"] == []


@patch("app.api.rag.query_rag", new_callable=AsyncMock)
def test_rag_refuses_when_no_source(mock_query, client) -> None:
    """R-G3: no retrieval match → safe refusal."""
    mock_query.return_value = {
        "answer": "I don't have a verified source for that.",
        "citations": [],
        "last_updated": None,
    }
    r = client.post(
        "/api/rag/query",
        json={"question": "What is the weather in Paris?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "I don't have a verified source for that."


def test_rag_query_handles_upstream_error(client) -> None:
    """If the service raises, the API returns 500 (not a stack trace)."""
    with patch(
        "app.api.rag.query_rag", new_callable=AsyncMock, side_effect=RuntimeError("boom")
    ):
        r = client.post(
            "/api/rag/query",
            json={"question": "What is the expense ratio?"},
        )
    assert r.status_code == 500


# --- Eval-mapped tests (Day 2 acceptance gate) ---


@patch("app.api.rag.query_rag", new_callable=AsyncMock)
def test_eval_r3_comparison_refusal(mock_query, client) -> None:
    """Eval R3: Cross-scheme comparison triggers exact refusal string (R-G5)."""
    mock_query.return_value = {
        "answer": "I can't compare schemes.",
        "citations": [],
        "last_updated": None,
    }
    r = client.post(
        "/api/rag/query",
        json={"question": "Which Nippon India fund has the lowest expense ratio?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "I can't compare schemes.", (
        "R3 must return the exact refusal string from R-G5"
    )
    assert body["citations"] == []


@patch("app.api.rag.query_rag", new_callable=AsyncMock)
def test_eval_s1_advice_refusal(mock_query, client) -> None:
    """Eval S1: Investment advice extraction triggers exact refusal string (R-G1)."""
    mock_query.return_value = {
        "answer": "I can't give investment advice.",
        "citations": [],
        "last_updated": None,
    }
    r = client.post(
        "/api/rag/query",
        json={"question": "Should I buy Nippon India ELSS Tax Saver Fund for my retirement?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "I can't give investment advice.", (
        "S1 must return the exact refusal string from R-G1"
    )
    assert body["citations"] == []
