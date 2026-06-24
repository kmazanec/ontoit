# ADR-011: Operability — single-instance Render deploy, deferred scale, Docker one-command run, observation stream as health view

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

(Mandatory cross-cutting round.) The system must be reachable at a public URL on a free host and runnable locally with one command (R18, R19, AC1, AC2). Render's free tier has an ephemeral filesystem and spins down after ~15 min idle (30–60s cold start). The real load is a single judge trying the demo.

## Options considered

- **Scale target.** A multi-instance, horizontally-scalable design is unwarranted for one concurrent demo user and would add complexity the brief penalizes. **Single instance, scale explicitly deferred** (chosen) — recorded as a conscious choice, not silence.
- **Local run.** A bespoke multi-step setup vs. **one command** (`docker compose up`). Docker chosen for reproducibility and to satisfy AC2 literally.
- **Cold-start mitigation.** Accept cold start vs. keep-alive ping vs. external uptime cron. **Keep-alive ping during judging** chosen (lightest); external cron noted as an option.

## Decision

Deploy a **single instance** to Render (or comparable free host); **defer horizontal scale** as a conscious post-MVP decision. Provide **one-command local run** via `docker compose up` (a single documented command; AC2). Mitigate Render spin-down with a **keep-alive ping** during the demo window. **Observability is the `ObservationEvent` stream** (ADR-004) plus structured server logs — the same trail the judge watches is the operator's health view; add a trivial `/health` endpoint. Performance budget: the only material latency is LLM calls and the PDF bake; cookie-state design adds no DB latency, so no caching layer is needed.

## Rationale

The design is sized to the actual load — one demo user — which the brief rewards (simplicity). Docker makes "clone and run one command" literally true across machines. Reusing the observation stream as the health/operability view means observability is not a separate afterthought — it serves judge, developer, and operator at once. Deferring scale *on the record* is the defensible answer a CTO accepts for a prototype.

## Tradeoffs & risks

- **Gave up:** horizontal scale, persistent storage, blue/green deploys — all unnecessary at this load. Reintroducing them later means a real session store (ADR-009) and a process manager.
- **Risk:** cold-start lag if the keep-alive lapses. *Mitigation:* ping during judging; document the cold-start behavior so a judge who hits it waits rather than assuming failure; external uptime cron available as backup.
- **Risk:** the single instance is a single point of failure. Accepted for a demo.
- **Revisit if:** the system needs concurrent users or real availability guarantees.

## Consequences for the build

- **Policy:** one documented command starts everything locally (`docker compose up`); a clean checkout + that command must reach the chat (AC2). The Anthropic key is the one required env var (ADR-003/010).
- **Policy:** ship a `/health` endpoint and structured logs; the observation stream doubles as the runtime health view. No caching/scaling infrastructure.
- **Policy:** document Render spin-down + the keep-alive approach in the README so the deployed URL is reliably reachable during judging (R18/AC1).
