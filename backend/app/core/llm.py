"""Claude LLM client. Prompt caching is applied to the system portion."""
from anthropic import Anthropic

from app.config import settings


def get_anthropic_client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


# TODO (Day 2): add thin, typed wrappers over anthropic.messages.create for:
#   - answer_with_citations(query: str, context_chunks: list[str], system: str)
#   - cluster_themes(reviews: list[Review]) -> list[Theme]
#   - generate_pulse(themes, quotes) -> Pulse  (with strict output validators)
# Use ephemeral cache_control on the long system-prompt portion to reduce cost.
