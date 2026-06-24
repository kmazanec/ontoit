"""Anthropic Claude client (ADR-003).

One provider covers the conversational agent and (later) W-2 vision extraction.
The model id is pinned here, not scattered through the code, so it is changed in
one place. The API key comes from the environment (ANTHROPIC_API_KEY) and is
never logged or committed.

Tone rubric (ADR-002)
---------------------
Every question must:
  1. Acknowledge the user's prior answer (if any) warmly before asking anything
     new — e.g. "Thanks for that!" or "Great, got it."
  2. Be phrased as a friendly, plain-English question, never a form field.
  3. State the reason if not obvious — one short clause is enough.
  4. Keep the total reply to 1–3 sentences.

The `ask_question` helper below encodes this rubric by injecting a prior-answer
acknowledgement into the prompt; tests can assert that the generated question
contains the prior-answer text or verify the rubric via monkeypatching.
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

# Canned refusals — fixed text so the guardrail node never calls the LLM for
# off-task turns.  Keeping these as module-level constants makes them unit-
# testable and prevents accidental prompt-only enforcement.

GUARDRAIL_OFF_TASK = (
    "I'm here to help you work through your tax return from your W-2, "
    "so I'll have to skip that one! Let's get back on track — "
    "I just have a couple of quick questions left."
)

GUARDRAIL_NO_FILING = (
    "Just a reminder: I'm an educational helper, not a licensed tax professional, "
    "so I can't file your return or give personalised tax advice. "
    "I can walk you through the numbers so you understand your return, "
    "but you'd want a professional or IRS Free File for the actual submission. "
    "Let's carry on with your figures!"
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
    message = get_client().messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def ask_question(
    question_key: str,
    prior_answer_summary: str | None,
    w2_wages_hint: str | None = None,
) -> str:
    """Ask the next question following the tone rubric.

    `question_key` is one of "filing_status" or "dependents".
    `prior_answer_summary` is a plain-English summary of the user's last answer
    (e.g. "Single") — the rubric requires the generated question to acknowledge
    it.  When None (first question) no acknowledgement prefix is emitted.

    This function calls the LLM so tests should monkeypatch it.
    """
    client = get_client()

    ack = (
        f"The user just answered: {prior_answer_summary!r}. "
        "Acknowledge their answer warmly in a few words, then "
    ) if prior_answer_summary else ""

    if question_key == "filing_status":
        prompt = (
            f"{ack}ask the user in one friendly sentence whether they filed as "
            "Single or Married Filing Jointly for 2025. "
            "Do NOT ask any other question."
        )
    elif question_key == "dependents":
        prompt = (
            f"{ack}ask the user in one friendly sentence how many qualifying "
            "children or dependents they have. Zero is a perfectly fine answer. "
            "Do NOT ask any other question."
        )
    else:
        prompt = (
            f"{ack}ask the user for their {question_key} in one friendly sentence."
        )

    if w2_wages_hint:
        prompt += f" (Context: their W-2 shows wages of {w2_wages_hint}.)"

    message = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def parse_filing_status(user_text: str) -> str | None:
    """Parse a freeform filing-status answer into "single" or "mfj".

    Returns None when the answer is unrecognisable.  Uses simple pattern
    matching first; falls back to LLM only when ambiguous.  Tests monkeypatch
    this to avoid API calls.
    """
    normalised = user_text.lower().strip()

    # Fast path: obvious keywords
    if any(w in normalised for w in ("single", "alone", "unmarried", "individual")):
        return "single"
    if any(w in normalised for w in ("married", "joint", "mfj", "jointly", "spouse", "together")):
        return "mfj"

    # LLM fallback for ambiguous phrasing
    try:
        client = get_client()
        message = client.messages.create(
            model=MODEL,
            max_tokens=20,
            system=(
                "You extract a filing status from a user's freeform answer. "
                "Reply with exactly one word: 'single', 'mfj', or 'unknown'."
            ),
            messages=[
                {"role": "user", "content": f"Filing status answer: {user_text!r}"}
            ],
        )
        result = "".join(b.text for b in message.content if b.type == "text").strip().lower()
        if "single" in result:
            return "single"
        if "mfj" in result:
            return "mfj"
    except Exception:
        pass
    return None


def parse_dependents(user_text: str) -> int | None:
    """Parse a freeform dependent-count answer into a non-negative int.

    Returns None when the answer cannot be interpreted as an integer.  Tests
    monkeypatch this to avoid API calls.
    """
    import re

    normalised = user_text.strip()

    # Fast path: zero words
    if normalised.lower() in ("none", "no", "zero", "nope", "0", "no dependents", "no children"):
        return 0

    # Look for a digit string
    digits = re.search(r"\b(\d+)\b", normalised)
    if digits:
        return int(digits.group(1))

    # Word numbers (common small values)
    word_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    for word, value in word_map.items():
        if word in normalised.lower():
            return value

    return None


def present_result(
    refund: str,
    owed: str,
    wages: str,
    filing_status: str,
) -> str:
    """Ask the LLM to present the tax result warmly.  Tests monkeypatch this."""
    client = get_client()
    if refund != "$0":
        outcome = f"they're getting a refund of {refund}"
    else:
        outcome = f"they owe {owed}"

    prompt = (
        f"The user's 2025 federal tax calculation is complete. "
        f"Wages: {wages}, filing status: {filing_status}. "
        f"Result: {outcome}. "
        "Present this in 2-3 warm, plain sentences. "
        "Remind them this is an estimate for educational purposes and they should "
        "use IRS Free File or a professional for the actual submission. "
        "Do NOT invent any other numbers."
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


# Off-task and advice-request detection (guardrail) ----------------------------
# These run BEFORE the LLM so the graph can short-circuit off-task turns without
# ever prompting the model with them.

_OFF_TASK_KEYWORDS = frozenset({
    "poem", "joke", "recipe", "weather", "stock", "sports", "movie", "song",
    "write me", "tell me a story", "what is the meaning",
    "capital of", "translate", "how do i cook", "how do i build",
})

_ADVICE_KEYWORDS = frozenset({
    "file for me", "file this", "file my", "submit my", "e-file", "send it in",
    "pay less tax", "avoid tax", "reduce my tax", "shelter", "offshore",
    "hide income", "what should i do", "how can i pay less",
    "loophole", "not pay", "evade",
})


def classify_user_turn(user_text: str) -> str:
    """Classify the user's message.

    Returns one of:
      "answer"     — looks like a response to a tax question (proceed normally)
      "off_task"   — unrelated topic
      "advice"     — request to file, evade tax, or get personalised tax advice

    Classification is code-only (keyword matching); it never calls the LLM so
    the guardrail is always deterministic and cannot be subverted by rephrasing.
    """
    lower = user_text.lower()
    if any(kw in lower for kw in _ADVICE_KEYWORDS):
        return "advice"
    if any(kw in lower for kw in _OFF_TASK_KEYWORDS):
        return "off_task"
    return "answer"
