# ADR-010: Security & trust boundaries — out-of-path enforcement, validated inputs, no PII at rest, secret hygiene

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

(Mandatory cross-cutting round.) The system takes untrusted input across three boundaries: the **uploaded W-2 file** (parsed, and its text fed to the LLM), **user chat messages**, and holds one **secret** (the Anthropic API key). Research flagged that feeding W-2/document text to the LLM is a realistic **indirect prompt-injection** vector, and that guardrails belonging *inside* the LLM's decision path are bypassable (OWASP). The data is fake by mandate (R20), and the product must not act as a tax preparer (DOMAIN.md §8).

## Options considered

- **Prompt-only safety + trust the model.** Bypassable by injection; the cosmetic failure under test. Rejected.
- **Structural defense via existing design, documented (chosen).** Enforcement already lives in code outside the LLM's decision path (ADR-002); extracted values are schema-validated before use; state carries no PII; the secret is env-only. Document this as the posture.
- **Add an explicit injection classifier on W-2 text.** Defense-in-depth, but extra surface for a fake-data prototype whose enforcement is already out-of-path and whose math is deterministic. Over-engineering here; recorded as a future option.

## Decision

The trust-boundary posture:

1. **Enforcement is outside the LLM's decision path.** The question-budget counter and guardrail/validation checks run in application code *before* the LLM call and around tool dispatch (ADR-002). Injected instructions in W-2 text or chat cannot raise the counter, disable a guardrail, or alter the (deterministic) tax math.
2. **Validate at every boundary.** Extracted W-2 values and user answers are schema-validated (positive wages; filing status in the allowed set; non-negative integer dependents; Box 12 code/amount well-formed) before reaching the engine (ADR-008/ADR-002).
3. **No sensitive data at rest.** Session state lives only in a signed `HttpOnly/Secure/SameSite=Strict` cookie (ADR-009); nothing is written server-side. Data is fake by policy (R20).
4. **Secret hygiene.** The Anthropic API key is provided via environment variable, never committed; `.env` is gitignored; no secret appears in logs or the observation trail.
5. **Safety invariant.** The no-advice / no-filing guardrail (R14) is enforced as a trust/safety rule, and the output is a self-prepared, review-and-sign artifact — keeping the tool outside "tax return preparer" status (free, user reviews/signs; DOMAIN.md §8).

## Rationale

For a fake-data prototype, the strongest *honest* defense is structural: because nothing the model emits can change an enforced limit or a computed number, prompt injection has no high-value target. Validation stops malformed values at the door; cookie-only state means a breach exposes no PII; env-only secrets are basic hygiene a CTO expects. We explicitly record that a dedicated injection classifier was considered and deferred, so the omission is a decision, not a gap.

## Tradeoffs & risks

- **Gave up:** defense-in-depth against novel injection (no classifier). Accepted: fake data + out-of-path enforcement + deterministic math leaves injection no payoff; revisit if real PII or monetization is ever introduced (which also triggers preparer-status analysis and §7216 obligations — DOMAIN.md §8).
- **Risk:** an oversized/malicious upload. *Mitigation:* enforce an upload size/type limit; reject non-PDF/image.
- **Revisit if:** the product handles real taxpayer data — then injection screening, encryption at rest, and legal review become required.

## Consequences for the build

- **Policy:** no guardrail or limit may live only in the prompt (ADR-002). Validate every boundary input. Enforce an upload size/MIME limit.
- **Policy:** secrets via env only; `.env` gitignored; never log the key or raw cookie contents.
- **Policy:** the no-advice/no-filing refusal and the "self-prepared, review-and-sign, educational" framing are present in the UI and enforced (R14, AC14).
