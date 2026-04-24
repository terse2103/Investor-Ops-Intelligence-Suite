"""PII guard: redact PAN, Aadhaar, phone, email, account numbers with [REDACTED]."""
import re

# Indian-focused patterns; refine during Day 2 as we see real inputs.
PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PHONE_RE = re.compile(r"\b(?:\+?91[-\s]?)?[6-9]\d{9}\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
ACCOUNT_RE = re.compile(r"\b\d{9,18}\b")

REDACTED = "[REDACTED]"


def redact(text: str) -> str:
    """Replace detected PII tokens with [REDACTED].

    Applied to every LLM input, every LLM output, and every inbound Vapi
    webhook payload (R-G2 + R-VOICE4 + R-SCRAPE2).
    """
    if not text:
        return text
    text = PAN_RE.sub(REDACTED, text)
    text = AADHAAR_RE.sub(REDACTED, text)
    text = PHONE_RE.sub(REDACTED, text)
    text = EMAIL_RE.sub(REDACTED, text)
    text = ACCOUNT_RE.sub(REDACTED, text)
    return text
