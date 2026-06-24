# Status — Agentic Tax-Filing Assistant (OntoIt)

**Updated:** 2026-06-24 · **Roadmap:** [ROADMAP.md](./ROADMAP.md)

## Now

Iterations 01 and 02 are **built and verified locally on main** — the full filer works end to end. A user opens the chat, loads the sample W-2 (or uploads one, really extracted via pdfplumber→Vision), has a warm ≤5-question conversation (answers parsed by Claude with strict JSON output; the question budget + guardrails enforced in code), the return is computed deterministically (sample: $28,879 taxable, $3,226 tax, $4,406 refund, $0 credits), and the user downloads a completed, baked **official IRS 2025 Form 1040** PDF. 88 tests pass. Next up is iteration 03 (deploy + the two stretch features).

## Iterations

| # | Iteration | Status | Build batch | Notes |
|---|-----------|--------|-------------|-------|
| 01 | Skeleton | **Shipped (local) on main** | A | F-01: graph-state + ObservationEvent + web/cookie/SSE contracts. |
| 02 | Core filing | **Shipped (local) on main** | B | F-02 extraction, F-03 engine (built in parallel worktrees), F-04 conversation+budget, F-05 filled 1040 PDF. Convergence found + fixed two bugs (lazy session persistence; "none" vs "one" parsing) and moved intent parsing to the LLM. 88 tests; verified end-to-end. |
| 03 | Deploy & stretch | **In progress** | C | **F-06 deployed & verified live** at https://ontoit.onrender.com (Render free tier, Docker, Blueprint from kmazanec/ontoit). Full smoke test passes 6/6 against the public URL incl. the 501 KB filled 1040 download; UI renders for a real visitor; keep-alive (`KEEP_ALIVE_URL`) set. Stretch features F-07 (correction) + F-08 (trace panel) next. |

The three iterations are a genuine linear chain (02 needs 01's shipped plumbing; 03 deploys 01–02), so they build in sequence — no independent-iteration batch to collapse here. The concurrency lives *within* iteration 02 (F-02 ⟂ F-03).

## What's next

Run `kmaz-plan-iteration` on `docs/iterations/01-skeleton/` to produce its BUILD-PLAN for approval, then `kmaz-build-iteration` once approved. After 01 ships, plan 02 (where the F-02/F-03 concurrency pays off).
