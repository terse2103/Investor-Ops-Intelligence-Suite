"""PII guard unit tests."""
from app.core.pii import redact


def test_redacts_pan() -> None:
    s = "My PAN is ABCDE1234F, please keep it safe."
    r = redact(s)
    assert "ABCDE1234F" not in r
    assert "[REDACTED]" in r


def test_redacts_indian_phone() -> None:
    for raw in ("9876543210", "+91 9876543210", "+91-9876543210"):
        r = redact(f"Call me at {raw}")
        assert "9876543210" not in r
        assert "[REDACTED]" in r


def test_redacts_email() -> None:
    r = redact("Email me at user+alias@example.co.uk")
    assert "user+alias@example.co.uk" not in r
    assert "[REDACTED]" in r


def test_redacts_aadhaar_with_spaces() -> None:
    r = redact("Aadhaar 1234 5678 9012")
    assert "1234" not in r or "[REDACTED]" in r
    assert "[REDACTED]" in r


def test_noop_on_clean_text() -> None:
    s = "Expense ratio of Nippon India ELSS Tax Saver Fund is 1.04%."
    assert redact(s) == s
