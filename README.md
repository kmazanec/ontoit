# OntoIt — Agentic Tax-Filing Assistant

A warm, conversational web chat that turns a single W-2 into a completed
**2025 IRS Form 1040** you can download — built as an agentic harness whose four
pillars (stateful chat loop, real tools, code-enforced guardrails, live
observability) are enforced by a [LangGraph](https://langchain-ai.github.io/langgraph/)
graph, not by the prompt.

See [`docs/`](./docs) for the PRD, architecture (ADRs), and roadmap.

## Run locally (one command)

```bash
cp .env.example .env          # then put your Anthropic API key in .env
docker compose up
```

Open <http://localhost:8000>. The only required setting is `ANTHROPIC_API_KEY`.

### Without Docker

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app.main:app --reload
```

## What works today (iteration 01 — walking skeleton)

- A minimal web chat with a **live observation panel** beside it.
- One-click **"Use the sample W-2"** (a realistic fake W-2 ships in `assets/`).
- A warm greeting from the agent, streamed over **SSE**, with each step shown as
  a structured **observation event** in the UI.
- Session state lives entirely in a **signed cookie** — nothing is stored
  server-side, so no real PII is persisted and the app survives a host restart.

Later iterations add W-2 extraction, the deterministic tax engine, the
≤5-question conversation, the filled 1040 PDF, deployment, and two stretch
panels (mid-conversation correction, a "show your work" tax trace).

## Not tax advice

This is an educational prototype. It uses fake test data only, does not file or
e-file anything, and is not a substitute for professional tax advice.
