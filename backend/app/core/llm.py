"""Claude LLM client. Sonnet 4.6 with adaptive thinking + prompt caching."""
from __future__ import annotations

from anthropic import Anthropic

from app.config import settings

MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 2048  # R-RAG1: answers <= 3 sentences; this is safe headroom


def get_client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def complete_text(
    *,
    system_prompt: str,
    user_content: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Single-turn completion. Caches the system prompt; returns text only.

    Used for non-RAG flows (Pulse generator, structured-output tasks) where the
    user content is composed by the caller rather than retrieved from a corpus.
    """
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def answer_from_context(
    *,
    question: str,
    context_chunks: list[dict],
    system_prompt: str,
) -> str:
    """Compose an answer grounded in context_chunks. Returns the raw text.

    Caches the system prompt (stable across requests) and enables adaptive
    thinking (recommended for 4.6 per the claude-api skill).
    """
    client = get_client()
    context_block = _format_context(context_chunks)

    user_content = (
        "Retrieved context:\n\n"
        f"{context_block}\n"
        f"<user_query>{question}</user_query>\n\n"
        "Produce an answer following the rules in the system prompt. "
        "If the context does not contain enough information, refuse with: "
        '"I don\'t have a verified source for that."'
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def _format_context(chunks: list[dict]) -> str:
    lines: list[str] = []
    for i, c in enumerate(chunks, start=1):
        meta = c.get("metadata", {}) or {}
        url = meta.get("url", "unknown")
        title = meta.get("title", "untitled")
        fetched_at = meta.get("fetched_at", "unknown")
        lines.append(
            f"[{i}] {title} (fetched_at={fetched_at})\n"
            f"URL: {url}\n"
            f"{c['text']}\n"
        )
    return "\n".join(lines)
