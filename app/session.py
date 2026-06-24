"""Signed-cookie session state (ADR-009).

The entire session — chat messages, the W-2 source (sample vs. upload), the
question counter, extracted figures — rides in one signed cookie. There is no
server-side store. This survives a free-host restart/spin-down, and because no
session data is persisted server-side it directly supports the fake-data /
no-PII guardrail (R20). The cookie is integrity-protected (signed), so a forged
cookie can't tamper with state the server later re-validates anyway.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from itsdangerous import BadSignature, URLSafeSerializer

COOKIE_NAME = "ontoit_session"

# A stable secret keeps sessions valid across restarts; a random fallback keeps
# local dev working without configuration. Never logged.
_SECRET = os.environ.get("SESSION_SECRET") or os.urandom(32).hex()
_serializer = URLSafeSerializer(_SECRET, salt="ontoit-session")


@dataclass
class SessionState:
    """The whole conversation, small enough (~2-5 KB) to live in a cookie."""

    messages: list[dict[str, str]] = field(default_factory=list)
    w2_source: str | None = None  # "sample" | "upload" | None
    w2_data: dict[str, Any] | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    questions_asked: int = 0
    phase: str = "intake"

    def to_dict(self) -> dict[str, Any]:
        return {
            "messages": self.messages,
            "w2_source": self.w2_source,
            "w2_data": self.w2_data,
            "answers": self.answers,
            "questions_asked": self.questions_asked,
            "phase": self.phase,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        return cls(
            messages=data.get("messages", []),
            w2_source=data.get("w2_source"),
            w2_data=data.get("w2_data"),
            answers=data.get("answers", {}),
            questions_asked=data.get("questions_asked", 0),
            phase=data.get("phase", "intake"),
        )


def serialize(state: SessionState) -> str:
    """Sign and encode the session for the Set-Cookie value."""
    return _serializer.dumps(state.to_dict())


def deserialize(raw: str | None) -> SessionState:
    """Verify and decode the session cookie. A missing or tampered cookie yields
    a fresh session rather than an error — the server re-validates any value it
    actually uses, so a forged cookie buys nothing."""
    if not raw:
        return SessionState()
    try:
        data = _serializer.loads(raw)
    except (BadSignature, json.JSONDecodeError, ValueError):
        return SessionState()
    if not isinstance(data, dict):
        return SessionState()
    return SessionState.from_dict(data)
