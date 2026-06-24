# Status — Agentic Tax-Filing Assistant (OntoIt)

**Updated:** 2026-06-24 · **Roadmap:** [ROADMAP.md](./ROADMAP.md)

## Now

Iteration 01 (walking skeleton) is **built and verified locally**: open the chat, select the bundled sample W-2 (or upload one), and a warm Claude-written greeting streams back with each step shown as a live observation event. FastAPI + SSE + signed-cookie state + the LangGraph graph + the ObservationEvent contract all work end to end against the live API. Next up is iteration 02 (core filing).

## Iterations

| # | Iteration | Status | Build batch | Notes |
|---|-----------|--------|-------------|-------|
| 01 | Skeleton | **Built (local), unmerged on main** | A | F-01 done: graph-state + ObservationEvent + web/cookie/SSE contracts introduced; 7 tests pass; verified end-to-end with a live Claude greeting. Built directly on main per request. |
| 02 | Core filing | Not started | B | Hard-depends on 01. F-02 (extraction) and F-03 (tax engine) build concurrently; F-04 waits on both; F-05 waits on F-03. |
| 03 | Deploy & stretch | Not started | C | Hard-depends on the working filer (01–02). Deploy (F-06) + the two committed stretch features. |

The three iterations are a genuine linear chain (02 needs 01's shipped plumbing; 03 deploys 01–02), so they build in sequence — no independent-iteration batch to collapse here. The concurrency lives *within* iteration 02 (F-02 ⟂ F-03).

## What's next

Run `kmaz-plan-iteration` on `docs/iterations/01-skeleton/` to produce its BUILD-PLAN for approval, then `kmaz-build-iteration` once approved. After 01 ships, plan 02 (where the F-02/F-03 concurrency pays off).
