"""Question-budget enforcement (ADR-002).

THIS IS THE SINGLE SOURCE OF TRUTH for what counts as a question and for the
cap that prevents a sixth question from being asked.

What counts as a question
-------------------------
A "question" is any turn in which the agent solicits NEW information from the
user — a filing-status question counts, a dependent-count question counts.
The following do NOT count:

  * A validation re-ask: the user gave an unrecognisable answer and the agent
    asks them to try again.  The agent already asked; it is asking again for the
    same information.
  * A confirmation or summary: the agent repeats a value already known (e.g.
    "I see your wages are $44,629 — does that look right?").

The enforcement point — the conditional-edge predicate
------------------------------------------------------
`budget_exhausted(questions_asked)` is the function a judge can point at.
When it returns True the collect node's outbound edge routes to compute,
bypassing any ask. The LLM never sees a 6th question prompt because the graph
does not call the LLM after this function returns True.

Usage
-----
  from app.agent.budget import increment, budget_exhausted, QUESTION_CAP

  # Increment only when asking a NEW-information question.
  questions_asked = increment(questions_asked)

  # Check before deciding whether to ask vs. compute.
  if budget_exhausted(questions_asked):
      # route to compute
      ...
"""

from __future__ import annotations

QUESTION_CAP: int = 5


def increment(questions_asked: int) -> int:
    """Return questions_asked + 1.  Only call this when asking for NEW
    information (see module docstring).  Never call it for re-asks or
    confirmations."""
    return questions_asked + 1


def budget_exhausted(questions_asked: int) -> bool:
    """True when no more new-information questions may be asked.

    THIS IS THE ENFORCEMENT POINT referenced in ADR-002.  The graph's
    conditional edge calls this predicate; when it returns True the edge routes
    to the compute node and the LLM is never asked to produce a question.
    """
    return questions_asked >= QUESTION_CAP
