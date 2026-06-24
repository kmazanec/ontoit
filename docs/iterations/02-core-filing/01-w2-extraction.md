# Feature: W-2 extraction (pdfplumber → Claude Vision, validated)

**ID:** F-02 · **Iteration:** 02-core-filing · **Status:** Not started

## What this delivers (before → after)
**Before:** An uploaded W-2 is an opaque file; only the bundled sample's figures are known.
**After:** The agent reads Box 1 wages, Box 2 federal withholding, and Box 12 code/amount pairs out of an uploaded W-2 (PDF text first, Claude Vision fallback for scans), validates them, and shows the captured values in the observation trail.

## How it fits the roadmap
First feature of iteration 02. Turns the upload surface from F-01 into real extracted data the rest of the flow consumes. Builds concurrently with F-03 (no hard dep between them — see below).

## Requirements traced (from the PRD)
R2 (W-2 upload & extraction), R15 (input validation), R16 (observable). Acceptance: AC3 (sample extraction captures wages 44629.35 / withholding 7631.62 / Box 12 D & W), partial AC15.

## Dependencies (must exist before this starts)
- **F-01 (walking skeleton)** — HARD dep: consumes the graph, the upload surface, the cookie state, and the ObservationEvent emitter to run the extraction tool and surface results.
- External: Anthropic API key (Vision fallback).

## Unblocks (what waits on this)
- F-04 (conversation) — consumes extracted values to confirm/correct and to drive the computation.

## Contracts touched
- **TaxResult / W2 / Answers** (source of truth: ADR-006) — extends the `W2` value object (the shape extraction populates). Reconciled with F-03, which introduces the type. The planner freezes `W2` so both build against it.
- **ObservationEvent** (source of truth: ADR-004) — emits an extraction event carrying the captured values and their source (text vs. vision).
- **Agent graph state** (source of truth: ADR-001) — writes `w2_data`; may add an `extraction` phase.

## Acceptance criteria (product behavior)
1. Given the bundled sample W-2 (digital PDF), when extraction runs, then it captures Box 1 = 44629.35, Box 2 = 7631.62, Box 12 D = 4107.00, Box 12 W = 1500.00, via pdfplumber text extraction (no Vision call needed), and these appear in the observation trail (AC3).
2. Given an image-only/scanned W-2 (no text layer), when extraction runs, then it falls back to Claude Vision with a strict JSON schema and a per-field confidence, nulling low-confidence fields.
3. Given an extracted value that fails validation (e.g. Box 2 ≥ Box 1, a malformed Box 12 entry, non-positive wages), when detected, then the value is rejected and the agent re-confirms/re-asks rather than computing on it (partial AC15) — without consuming a user question.
4. Box 12 entries are parsed as exactly one alpha code (1–2 chars) + one decimal amount each (guards the most common OCR failure).

## Testing requirements
- Unit: pdfplumber extraction of the sample PDF returns the exact figures; the Box 12 parser splits code/amount pairs correctly; validation rejects the named bad cases.
- Integration: upload sample → extraction event with correct values appears via SSE; a no-text-layer input routes to the Vision path (Vision mockable).
- Contract: populated `W2` matches the frozen shape.

## Manual setup required
None (the sample W-2 ships with the repo; the API key is already provisioned in F-01).

## Implementation notes (filled in by the building agent)


## Implementation notes (build outcome)

**Shipped on main, verified locally (2026-06-24).**
