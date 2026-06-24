# ADR-008: Two-step W-2 extraction — pdfplumber text first, Claude Vision fallback, with per-field confidence

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The system reads a W-2 uploaded as PDF or image and extracts the figures it needs (R2, AC3): Box 1 wages, Box 2 federal withholding, and Box 12 code/amount pairs (D feeds Saver's Credit; W is acknowledged but not used per R10). The sample W-2 is a digital PDF. Bad extraction corrupts the computation (PRD R-2), mitigated by the bundled-sample fallback (R3) and input validation (R15).

## Options considered

- **pytesseract (Tesseract OCR).** ~80% accuracy, degrades badly under 200 DPI, no structure detection — brittle exactly on Box 12 code/amount pairing (the most common W-2 extraction failure). Worst tradeoff for a one-day build. Rejected.
- **Claude Vision only.** One uniform path, ~$0.001–0.004/doc, best JSON-schema consistency, handles scans. Slightly less deterministic than text extraction for digital PDFs, and pays an LLM call on every upload.
- **Two-step: pdfplumber then Claude Vision (chosen).** pdfplumber extracts the text layer of digital PDFs near-deterministically; if no text layer, fall back to Claude Vision with a strict JSON schema.

## Decision

Extract in two steps: **(1)** attempt **pdfplumber** text extraction (deterministic, near-100% for the digital sample and most machine-generated W-2s); **(2)** if no text layer is present (scan/image), fall back to **Claude Vision** with a strict JSON schema and a **per-field `confidence`** value, substituting null for low-confidence fields. Extracted values then pass through the validation node (ADR-002) before any use.

## Rationale

The sample W-2 — and most digital W-2s — parse deterministically with no LLM call, which is faster, free, and reproducible (helping the "works on the first run" demo). Scans still work via Vision, which has the best schema compliance of the frontier models (matters when output feeds a computation pipeline). The confidence field plus downstream validation catches the classic Box 12 code/amount mispairing rather than silently computing on garbage.

## Tradeoffs & risks

- **Gave up:** the simplicity of a single path; we maintain two extractors and a branch.
- **Risk:** pdfplumber could extract text but mis-associate a Box 12 code/amount. *Mitigation:* validation requires each Box 12 entry to be exactly one alpha code (1–2 chars) + one decimal amount; cross-field sanity (Box 2 < Box 1, Box 2/Box 1 within ~10–37%) flags gross misreads and triggers a confirm/re-ask.
- **Risk:** Vision hallucination on edge fields. *Mitigation:* confidence-gated nulling + the sample fallback guarantees a clean run regardless (R3).
- **Revisit if:** real-world uploads show pdfplumber mis-parsing the fixed IRS layout — then prefer Vision-first.

## Consequences for the build

- **Policy:** never compute on unvalidated extracted values; validation (ADR-002) runs before the tax engine. A failed/low-confidence extraction routes to a confirm/re-ask or the sample fallback, never to a silent guess.
- **Policy:** extraction emits an ObservationEvent with the captured values and their source (text vs. vision) so the judge sees what was read (AC3, AC16).
