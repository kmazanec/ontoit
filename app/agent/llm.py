"""Anthropic Claude client (ADR-003).

One provider covers the conversational agent and (later) W-2 vision extraction.
The model id is pinned here, not scattered through the code, so it is changed in
one place. The API key comes from the environment (ANTHROPIC_API_KEY) and is
never logged or committed.
"""

from __future__ import annotations

import anthropic

# Pinned model. A current, capable tool-use- and vision-capable Claude model.
MODEL = "claude-opus-4-8"

# The SDK reads ANTHROPIC_API_KEY from the environment. Constructed lazily so the
# app can import without a key present (tests stub the client).
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


SYSTEM_PROMPT = (
    "You are a warm, friendly tax-filing assistant who helps someone file a "
    "simple U.S. federal Form 1040 from a single W-2. You are an educational "
    "tool, not a tax professional, and you never claim to file or e-file the "
    "return. Speak in plain, kind, conversational language — never robotic or "
    "interrogative. Keep replies short."
)


def greet(wage_hint: str | None = None) -> str:
    """Produce a warm opening message. Uses a real Claude call so the skeleton
    proves the full path graph -> Claude -> SSE end to end."""
    client = get_client()
    context = (
        "The user just loaded their W-2. Greet them warmly in 1-2 sentences, "
        "let them know you'll ask only a few quick questions and then prepare "
        "their 2025 Form 1040, and gently note you're an educational helper, "
        "not a tax professional."
    )
    if wage_hint:
        context += f" Their W-2 shows wages of about {wage_hint}."
    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
