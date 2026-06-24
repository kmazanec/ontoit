# ADR-001: Build the agent on LangGraph (a real LLM-driven agent whose pillars are enforced by the graph)

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The product is judged primarily as an **agentic harness**: the four pillars (stateful chat loop, real tool use, code-enforced guardrails, observable behavior) must be *enforced and visible*, not cosmetic (PRD §1, R1, R4, R12–R16; brief: "'It's in the prompt' is weaker than 'it's enforced and visible.'"). The central design tension: a purely LLM-driven agent (model decides everything, limits requested in the prompt) is flexible but its limits are *emergent*, which scores poorly on the highest-weighted criterion; a purely code-driven state machine enforces everything but risks being "a deterministic loop with a chat UI" — not really an agent, which is the point of the exercise.

This decision picks the structure that resolves that tension.

## Options considered

- **Pure LLM-driven agent (ReAct loop, limits in the prompt).** Most flexible, least code. But the 5-question cap and guardrails are prompt requests the model can miss or be talked past — the "cosmetic" failure the brief warns against. Weak on the top judging criterion.
- **Pure code-driven state machine, LLM as a phrasing/parsing component.** Every pillar provably enforced, but the conversation runs on fixed rails and a critic could fairly say it's not really an agent — undercutting the spirit of the challenge.
- **LangGraph: an LLM-driven agent inside an explicit graph (chosen).** The LLM genuinely drives the conversation and decides which tools to call, but it runs inside a LangGraph state graph whose **state object, nodes, and conditional edges** carry the enforcement. The question counter lives in graph state; a conditional edge routes to compute once it hits the cap; guardrail/validation nodes gate tool inputs; the framework's streaming/checkpointer emits the observation trail. It is unmistakably an agent framework, and the pillars are enforced by the graph rather than by prose.

## Decision

Build the backend agent on **LangGraph (Python)**. The agent is LLM-driven — the model owns the conversational turn and tool-selection — but the harness's enforceable properties are carried by the graph: state-held counters, conditional edges, and dedicated validation/guardrail nodes. The LLM never decides when the conversation must end or whether a guardrail applies; the graph does.

## Rationale

This is the version of "LLM-driven agent" that survives a judge poking at it, and it is a genuine agent, not a disguised switch statement. The sentence to the judge: *"It's a real LangGraph agent — the model drives the conversation — but the 5-question budget is a counter in graph state with a conditional edge that routes past it, the guardrails are graph nodes that gate tool calls, and every node transition and tool call streams out as an observation event. The framework is what makes the pillars enforced and visible, not the prompt."* LangGraph also makes the **observability pillar** (the highest-leverage one to demo) nearly free: its event stream / checkpointer is the live observation trail (see ADR-004). Python is LangGraph's most mature ecosystem and hosts the best PDF-form-filling and tax libraries (ADR-005, ADR-007).

## Tradeoffs & risks

- **Gave up:** the minimal-code simplicity of a bare tool loop, and the absolute rail-tightness of a pure state machine. The graph is more moving parts than either pole.
- **Risk:** LangGraph has a learning curve and its abstractions can be over-applied; an over-engineered graph is a real failure mode. *Mitigation:* keep the graph small — a handful of nodes (intake → extract → converse/collect → compute → fill → done) and the few edges enforcement actually needs. Resist modeling every nuance as a node.
- **Risk:** the LLM, while driving, could still attempt to ask a 6th question or go off-task. *Mitigation:* that is exactly what the graph edges/guardrail nodes (ADR-002) catch — enforcement does not depend on the model's cooperation.
- **Revisit if:** the graph grows unwieldy for the bounded scope, or LangGraph's streaming proves awkward for the observation transport (ADR-009).

## Consequences for the build

- **Policy:** all agent control flow is expressed as a LangGraph graph; the LLM is invoked *within* nodes, never as the top-level loop owner. No business-critical limit (question budget, guardrail, validation) may live only in the system prompt — each must be carried by graph state/edges/nodes (enforced per ADR-002).
- **Policy:** tax math is never performed by the LLM; it is a deterministic tool the agent calls (ADR-006).
- **Contract consequences (Contract: yes — the agent's graph state shape):**
  - **Source of truth:** the LangGraph state schema, `app/agent/state.py` (a typed `TypedDict`/Pydantic model).
  - **Shape (minimum viable):** `messages: list` (chat history); `w2_data: W2 | None` (extracted figures); `answers: {filing_status, dependents, ...}`; `questions_asked: int` (the enforced budget counter); `phase: Literal["intake","extracting","collecting","computing","filling","done"]`; `tax_result: TaxResult | None`; `events: list[ObservationEvent]` (or emitted via stream — see ADR-004). 
  - **Exhaustive consumers:** every graph node reads/writes this state; the conditional edges branch on `questions_asked` and `phase`; the observation emitter serializes transitions; the API/transport layer streams it. Any new node or phase must extend `phase` and be handled by the edge router — a non-exhaustive `phase` is a build defect.
