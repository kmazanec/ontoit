# ADR-003: Anthropic Claude provides the agent's tool-calling LLM and W-2 vision extraction

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The agent needs a tool-use-capable LLM (ADR-001) that also produces warm, natural conversation (R17/AC17, a judging criterion) and, ideally, can read a W-2 image directly (R2, feeds ADR-008). Provider is a HOW decision left open by the PRD (dep 6).

## Options considered

- **Anthropic Claude (chosen).** Strong tool-use, warm tone, and multimodal — one provider can both drive the agent and read the W-2 image, reducing moving parts. Integrates with LangGraph.
- **OpenAI.** Equally capable tool-calling and vision, widely documented with LangGraph. A fine alternative; chosen against only to standardize on one provider the user preferred.
- **Provider-agnostic interface, decide at build.** Maximum flexibility but defers a decision that does not need deferring; the harness benefits from being built against one provider's tool-use semantics.

## Decision

Use **Anthropic Claude** for both the agent's tool-calling LLM and (per ADR-008, if vision extraction is chosen) the W-2 image extraction. The exact model is selected at build time, choosing a current tool-use- and vision-capable Claude model.

## Rationale

One provider covers both the conversational agent and W-2 reading, which simplifies the system and keeps the warm-tone and multimodal capabilities aligned. Claude's tool-use fits the LangGraph agent (ADR-001) and its tone supports the conversation-quality criterion. Standardizing now (rather than a provider-agnostic abstraction) keeps the prototype simple — the brief explicitly rewards simplicity.

## Tradeoffs & risks

- **Gave up:** provider portability — switching providers later means touching the model-call sites. Accepted for a prototype; the call surface is small.
- **Risk:** API key is a secret that must not leak (handled in ADR-010) and a cost/availability dependency. *Mitigation:* secret via env var, never committed; the bundled-sample fallback (R3) does not remove the LLM dependency but bounds the demo surface.
- **Revisit if:** a build-time evaluation shows another provider materially better for tone or W-2 vision accuracy.

## Consequences for the build

- **Policy:** the LLM provider is Anthropic Claude; the model id is pinned in config (not scattered) and chosen as a current capable model at build time.
- **Policy:** the API key is provided via environment variable and is required for both local run and deploy (documented in ADR-011's one-command run).
