# Feature: Deploy to a public URL + one-command local run

**ID:** F-06 · **Iteration:** 03-deploy-and-stretch · **Status:** Not started

## What this delivers (before → after)
**Before:** The working filer runs only on the developer's machine.
**After:** A judge reaches the system at a public URL and completes a full filing end to end; anyone can run it locally with a single documented command. The deployed instance stays reachable through a judging window despite free-tier spin-down.

## How it fits the roadmap
First feature of iteration 03; makes the working product (iterations 01–02) publicly demonstrable — the brief's hard deliverable. Hard-depends on the complete core filer.

## Requirements traced (from the PRD)
R18 (public deployment), R19 (one-command local run). Acceptance: AC1 (public URL works), AC2 (one-command local run).

## Dependencies (must exist before this starts)
- **F-01, F-02, F-03, F-04, F-05** — HARD deps: deploys the complete working filer; everything it serves must already work locally.
- External: a Render (or comparable free host) account; the Anthropic API key configured as a host environment variable.

## Unblocks (what waits on this)
- Nothing in scope (F-07, F-08 enhance the deployed app but do not consume deploy behavior; they hard-depend on F-03/F-04/F-01, not F-06).

## Contracts touched
- None new. Consumes the operability decisions (ADR-011): single instance, Docker one-command run, `/health`, keep-alive.

## Acceptance criteria (product behavior)
1. Opening the public URL in a browser loads a usable chat with no authentication, and a third party can complete a full filing (select sample → ≤5 questions → download the 1040) (AC1).
2. Given a clean checkout and the one documented command (`docker compose up`), the system starts and the chat is reachable locally (AC2).
3. A `/health` endpoint returns healthy; structured logs and the observation stream are available to the operator.
4. The deployed instance is reachable during a judging window — the keep-alive approach prevents (or recovers gracefully from) free-tier spin-down; the README documents the cold-start behavior.
5. The Anthropic API key is supplied via host env var; no secret is committed or logged.

## Testing requirements
- Smoke (deployed): against the live public URL, a scripted end-to-end run (sample → questions → download) succeeds; `/health` returns healthy.
- Integration (local): `docker compose up` from a clean checkout reaches the chat.
- Verify Render spin-down/cold-start timing against the live deploy and confirm the keep-alive holds.

## Manual setup required
- Create the free-host account, connect the repo, and set the Anthropic API key as a host environment variable. Configure the keep-alive ping (in-app tab ping or external uptime cron). Confirm the public URL.

## Implementation notes (filled in by the building agent)


## Implementation notes (build outcome)

**Shipped & verified live (2026-06-24).** Deployed to Render free tier as a Docker web service via the `render.yaml` Blueprint from `kmazanec/ontoit`. Live at **https://ontoit.onrender.com**. `ANTHROPIC_API_KEY` set by the owner in the dashboard; `SESSION_SECRET` auto-generated; `KEEP_ALIVE_URL` set to the service's own /health for spin-down resistance. Full end-to-end smoke test passes 6/6 against the public URL (health, sample, greeting via live Claude, conversation, and the 501,751-byte filled 1040 download); the chat UI + live observation panel render for a real browser visitor. AC1 (public URL) and AC2 (one-command `docker compose up`) both met. Note: a brief 200/404 flap during the deploy swap window resolves once the deploy settles — documented as expected free-tier rollout behavior, not an app bug.
