# Agentic Tax-Filing Assistant — Product Requirements Document

## 1. Problem Statement

A person with a single, straightforward W-2 (roughly $40,000/year in wages) needs to produce a correct, downloadable 2025 U.S. Federal Form 1040, but consumer tax software is tedious, form-shaped, and impersonal. This product replaces that experience with a warm, conversational agent: the user uploads their W-2, answers no more than five friendly questions, and downloads a completed, correct 2025 Form 1040. The product is built and judged primarily as an **agentic harness** — a system in which four capabilities (a stateful chat loop, real tool use, enforced guardrails, and observable behavior) are demonstrably real and enforced rather than merely described. The conversation experience and the correctness of the resulting return are the user-facing proof that the harness works end to end.

## 2. Users & Stakeholders

- **Primary user — the filer.** A working adult with a single W-2 around $40k/year and a simple tax situation (e.g. the sample filer: wages $44,629.35, federal withholding $7,631.62, a retirement deferral and an HSA in Box 12). They are not a tax expert, want the task to feel easy and human, and expect a downloadable completed form at the end. They may file as Single or Married Filing Jointly.
- **The judge / evaluator.** Reaches the system at a public URL, uploads a W-2 (or uses the built-in sample), holds a short conversation, downloads the 1040, and inspects whether the four pillars are genuinely enforced and observable. The judge is a first-class user of the *observation* surface, not just the chat.
- **The operator (builder/owner).** Deploys the system to a public host and runs it locally via a single command. Relies on structured logs and the observation trail to confirm correct behavior.

## 3. Desired Outcome

Success is a working, publicly reachable system where:

1. A user uploads a realistic W-2 (or selects the bundled sample) and the agent correctly extracts the figures it needs.
2. The agent conducts a warm, human-feeling conversation that asks **no more than five questions** and gathers exactly what it needs to file.
3. The agent computes a **correct 2025 Form 1040** for the core W-2 path — including the common credits a ~$40k filer plausibly qualifies for (Saver's Credit, Earned Income Tax Credit) — for filing status Single or Married Filing Jointly.
4. The user downloads a **completed, filled official IRS 2025 Form 1040** as a file.
5. Throughout, a judge can *see* the harness working: the stateful chat loop, each tool call, the values extracted, the decisions made, the running question count, and the guardrails firing — surfaced live in the UI, not only in server logs.
6. The system is reachable at a public URL and runnable locally with one command.

The behavioral bar for "feels human": responses are warm, plain-language, and conversational; the agent never interrogates with a bare list of questions, acknowledges the user's answers, and explains what it's doing in friendly terms. Communication quality is an explicit acceptance dimension, not a nicety.

## 4. Scope

### In Scope

1. A web-based chat interface in which the user converses with the agent across multiple turns, with conversation/session state carried across turns.
2. W-2 ingestion by **file upload** (PDF or image, e.g. the sample format), with the agent extracting the boxes it needs (at minimum Box 1 wages, Box 2 federal withholding, Box 12 codes/amounts, filing-relevant state boxes ignored for the federal return).
3. A **bundled sample W-2** the user can select with one click, guaranteeing a clean end-to-end run even if an upload is unreadable.
4. A conversation that asks **at most five questions**, spent on essentials: filing status, number of dependents/qualifying children, and confirming or correcting key extracted W-2 figures.
5. Correct 2025 Form 1040 computation for the **core W-2 path**: total wages (Form 1040 line 1a), federal income tax withheld, standard deduction by filing status (2025 values), taxable income, tax via the 2025 tax tables/brackets, total payments, and resulting **refund or amount owed**.
6. **Common credits, computed correctly across cases, inferred from already-gathered data (never a sixth question).** Research (docs/research/DOMAIN.md, high confidence) established that for the sample profile (Single, AGI $44,629, no children) **both credits correctly compute to $0** (Saver's Credit phases out at $39,500 Single; EITC's childless limit is $19,104). The credits are therefore built as deterministic functions that return the **correct value across cases** — $0 when not earned, and a correct non-zero amount when the filer qualifies (e.g. MFJ with a qualifying child makes EITC non-zero, since $44,629 < the $57,554 one-child MFJ limit). The $0 result is surfaced *with its reason* in the observation/trace output.
   - **Saver's Credit (Retirement Savings Contributions Credit)** — derived from the Box 12 code-D retirement deferral, AGI, and filing status (2025 tiers).
   - **Earned Income Tax Credit (EITC)** — derived from earned income, AGI, filing status, and number of qualifying children (2025 parameters).
7. Support for two filing statuses, both fully correct: **Single** and **Married Filing Jointly** — with status-correct standard deduction, brackets, and credit thresholds.
8. Generation of a **filled official IRS 2025 Form 1040 PDF** populated with the computed values, downloadable as a file.
9. **Four enforced pillars**, each observable:
   - **Chat loop** — a multi-turn conversational loop holding state across turns.
   - **Tools** — the agent performs real actions via defined tools, at minimum: extract W-2 data, compute the tax result, and produce the filled 1040 file.
   - **Guardrails** — (a) stays on-task (tax filing only); (b) refuses to give tax advice and never claims to e-file, stating it is educational; (c) validates inputs (extracted/entered W-2 figures and answers) and re-asks rather than computing on invalid data; (d) the ≤5-question limit is enforced in code (a counter/state machine), not merely requested in the prompt.
   - **Observation** — every turn, tool call, extracted value, decision, and the running question count are logged in a structured, inspectable way **and surfaced live in the chat UI**.
10. Deployment to a **public URL** on a free, easy host (Render or comparable), plus a documented **one-command local run**.
11. A short **DECISIONS note** capturing the key open-item choices and their rationale.

### Out of Scope

1. Itemized deductions (Schedule A) and any optimization of itemize-vs-standard.
2. Tax schedules and forms beyond those required by the core + Saver's Credit + EITC path.
3. Income types other than a single W-2 (no 1099s, self-employment, investment, multiple W-2s).
4. State or local tax returns (state W-2 boxes are read but not filed).
5. Filing statuses other than Single and Married Filing Jointly (no MFS, Head of Household, or Qualifying Surviving Spouse).
6. Real e-filing, submission to the IRS, or handling of any real PII / real taxpayer data.
7. Giving tax advice or representing the output as professional tax preparation.
8. Visual/UI polish beyond what is needed to make the chat and the observation trail legible.

### Committed stretch features (v2 — folded in from the architecture stage)

1. **Mid-conversation answer correction.** The user may change an earlier answer (e.g. switch filing status to MFJ, add a child); the agent updates state and re-runs the deterministic computation without re-asking answered items and without consuming a question. (Was deferred in v1; committed in v2. See ADR-012.)
2. **"Show your work" tax-trace panel.** The completed 1040 is presented line-by-line with reasoning (e.g. "Saver's Credit $0 because AGI $44,629 exceeds the $39,500 cutoff"; "tax from the IRS 2025 Tax Table"). (Committed in v2. See ADR-013.)

### Deferred

1. **Additional filing statuses (HoH, MFS, QSS).** Rationale: they add qualifying-person edge cases without serving the target $40k filer; the design should not preclude adding them later.
2. **Richer messy-W-2 recovery** (partial/garbled OCR repair beyond basic validation + re-ask). Rationale: a stretch goal; the sample fallback already protects the demo.
3. **A dedicated prompt-injection classifier** on uploaded W-2 text. Rationale: enforcement already runs outside the LLM's decision path and data is fake; deferred unless real PII is ever handled (see ADR-010).

## 5. Requirements

Requirements describe behavior and outcomes only; they are technology- and framework-agnostic.

1. **R1 — Stateful chat.** The system SHALL present a web-based chat where the user and agent exchange messages over multiple turns, and SHALL retain conversation state (prior answers, extracted W-2 data, question count) across turns within a session.
2. **R2 — W-2 upload & extraction.** The system SHALL accept a W-2 uploaded as a PDF or image and SHALL extract the figures needed to file: total wages, federal income tax withheld, and Box 12 codes/amounts relevant to credits.
3. **R3 — Sample fallback.** The system SHALL offer a one-click option to use a bundled sample W-2, producing a complete end-to-end run without any upload.
4. **R4 — Five-question budget.** The agent SHALL ask the user no more than five questions in total across a session, and the limit SHALL be enforced by the system's control logic (not solely by prompt instruction).
5. **R5 — Essential questions.** The agent SHALL use its questions to establish filing status, number of dependents/qualifying children, and to confirm or correct key extracted W-2 figures. It SHALL NOT ask separate questions to determine credit eligibility; credits SHALL be inferred from data already gathered.
6. **R6 — Correct core computation.** For a valid W-2 and the gathered answers, the system SHALL compute, using 2025 figures, the standard deduction for the chosen filing status, taxable income, the tax owed via the 2025 tax tables/brackets, total payments (withholding), and the resulting refund or amount owed.
7. **R7 — Saver's Credit.** When the filer has a qualifying retirement contribution (Box 12 code D) and an AGI within the 2025 Saver's Credit thresholds for their filing status, the system SHALL compute and apply the Saver's Credit at the correct rate.
8. **R8 — EITC.** When the filer qualifies under 2025 EITC rules given earned income, AGI, filing status, and number of qualifying children, the system SHALL compute and apply the correct EITC amount.
9. **R9 — Filing-status correctness.** The system SHALL produce a correct return for both Single and Married Filing Jointly, applying status-specific standard deductions, brackets, and credit thresholds.
10. **R10 — HSA handling.** The system SHALL treat a Box 12 code-W (employer/HSA) amount as already excluded from Box 1 wages and SHALL NOT add a 1040 line or a question for it (no double-counting).
11. **R11 — Filled official form.** The system SHALL produce a downloadable file that is the **official IRS 2025 Form 1040** populated with the computed values.
12. **R12 — Real tool actions.** Extracting W-2 data, computing the tax result, and producing the filled 1040 file SHALL each be performed as a discrete, defined tool action the agent invokes — not as free-text the model merely asserts.
13. **R13 — On-task guardrail.** The agent SHALL decline off-topic or out-of-scope requests and SHALL redirect warmly back to tax filing.
14. **R14 — No-advice / no-filing guardrail.** The agent SHALL decline to give tax advice and SHALL NOT claim to file or e-file the return; it SHALL state that it is an educational tool.
15. **R15 — Input-validation guardrail.** The system SHALL validate extracted and user-provided values (e.g. wages a positive number; filing status one of the allowed set; dependents a non-negative integer) and SHALL re-ask or reject rather than compute on invalid data, without consuming an extra user question for a re-ask of the same item.
16. **R16 — Observable behavior.** The system SHALL record, in a structured and inspectable form, each turn, each tool call and its result, each extracted value, each material decision, and the running question count; and SHALL surface this trail live in the chat UI.
17. **R17 — Warm communication.** Agent messages SHALL be friendly, plain-language, and conversational; SHALL acknowledge the user's prior answer; and SHALL NOT present questions as a bare interrogative list.
18. **R18 — Public deployment.** The system SHALL be reachable by a third party at a public URL hosted on a free, easy service (Render or comparable).
19. **R19 — One-command local run.** The system SHALL be runnable locally via a single documented command.
20. **R20 — Fake data only.** The system SHALL operate only on fake/test data and SHALL NOT request, store, or transmit real PII or perform any real filing.

## 6. Acceptance Criteria

Each criterion is written so it maps near-1:1 onto a test.

1. **AC1 — Public URL works.** Given the deployed system, when a third party opens its public URL in a browser, then a usable chat interface loads and accepts input without authentication.
2. **AC2 — One-command local run.** Given a clean checkout and the documented command, when the operator runs that single command, then the system starts and the chat is reachable locally.
3. **AC3 — Upload extraction.** Given the sample W-2 file uploaded via the chat, when extraction completes, then the system has captured Box 1 wages = 44629.35 and Box 2 federal withholding = 7631.62 (and the Box 12 D and W amounts), and these values are visible in the observation trail.
4. **AC4 — Sample fallback.** Given a fresh session, when the user selects "use the sample W-2," then the system proceeds to the conversation with the sample figures loaded and no upload required.
5. **AC5 — Question cap enforced.** Given any complete session, when the conversation ends, then the agent has asked at most five questions; and given a fifth question already asked, when the agent would ask a sixth, then the control logic prevents it (verifiable by the enforced counter, not only by observed wording).
6. **AC6 — Single, core path correctness.** Given the sample W-2 (wages 44629.35, withholding 7631.62) and filing status Single with zero dependents, when the return is computed, then taxable income = 28879.35 (44629.35 − 15750 standard deduction), tax = 3227 (from the IRS 2025 Tax Table, not bracket arithmetic), total payments = 7631.62, and refund = 4405 (to the nearest dollar), and the computed values are shown in the observation/trace output. (Source: docs/research/DOMAIN.md.)
7. **AC7 — MFJ changes the result.** Given the same W-2 and filing status Married Filing Jointly, when the return is computed, then the standard deduction, brackets, and any credit thresholds used are the MFJ 2025 values and the resulting refund/owed differs from the Single result accordingly.
8. **AC8 — Saver's Credit correct across cases.** Given the sample Single filer (AGI 44629.35, Box 12-D present), when computed, then the Saver's Credit = $0 (AGI exceeds the $39,500 Single cutoff), shown with that reason; and given a filer with AGI within the 2025 Saver's Credit range for their status, when computed, then a non-zero credit at the correct 2025 rate appears.
9. **AC9 — EITC correct across cases.** Given the sample Single filer with 0 qualifying children (AGI 44629.35), when computed, then EITC = $0 (exceeds the $19,104 childless limit), shown with that reason; and given a qualifying filer (e.g. MFJ at this AGI with 1 qualifying child, below the $57,554 limit), when computed, then the correct non-zero 2025 EITC amount appears.
10. **AC10 — No sixth question for credits.** Given a complete session in which Saver's Credit and/or EITC are applied, when the transcript is inspected, then no question beyond the five essentials was asked to determine credit eligibility (credits were inferred from W-2 + status + dependents).
11. **AC11 — HSA not double-counted.** Given the sample W-2 with Box 12 code-W = 1500.00, when the return is computed, then the HSA amount is not added to income and produces no extra 1040 line.
12. **AC12 — Downloadable filled official 1040.** Given a completed conversation, when the user requests the form, then the system returns a downloadable file that is the official IRS 2025 Form 1040 with the computed line values populated (wages, withholding, standard deduction, taxable income, tax, credits, refund/owed).
13. **AC13 — On-task guardrail.** Given an off-topic request (e.g. "write me a poem"), when sent to the agent, then the agent declines and redirects to tax filing, and the refusal is recorded in the observation trail.
14. **AC14 — No-advice / no-filing guardrail.** Given a request for tax advice or to actually file the return, when sent to the agent, then the agent declines, states it is educational and does not file, and the event is recorded in the observation trail.
15. **AC15 — Input validation.** Given an invalid value (e.g. negative wages, an unrecognized filing status, or a non-integer dependents count), when it is extracted or entered, then the system rejects it and re-asks/re-confirms without computing on it, and without consuming one of the five questions for re-asking the same item.
16. **AC16 — Live observation trail.** Given an active session, when a tool is called or a decision is made, then the chat UI shows a corresponding entry (tool name, inputs/outputs or decision, and the current question count) without the operator needing to read server logs.
17. **AC17 — Tone.** Given any agent turn that asks a question, when the message is inspected, then it acknowledges the prior answer and reads as warm, plain-language conversation rather than a bare list of questions (assessed against a documented tone rubric).
18. **AC18 — Fake-data safety.** Given any session, when network and storage are inspected, then no real PII is requested or persisted and no real filing/e-file call is made.
19. **AC19 — Mid-conversation correction (stretch).** Given a completed or in-progress session, when the user changes a prior answer (e.g. "make it Married Filing Jointly" or "I have 1 child"), then the system updates that field, re-runs the computation, reflects the new refund/owed, does **not** re-ask already-answered items, and does **not** increment the question counter for the correction.
20. **AC20 — Tax-trace panel (stretch).** Given a computed return, when the trace is inspected, then it presents the 1040 line-by-line with reasoning for each load-bearing line (taxable income, the Tax Table lookup, tax, each credit with its eligibility reason, refund/owed), and each trace value matches the corresponding value on the filled 1040.

## 7. Dependencies

1. A correct, citable source of **2025 federal tax parameters** — now sourced (docs/research/DOMAIN.md, high confidence, IRS primary sources): standard deduction **$15,750 Single / $31,500 MFJ** (the 2025 figure per OBBBA; the brief's $14,600 is the stale 2024 value); the **IRS 2025 Tax Table** (required for incomes under $100k — not bracket arithmetic); 2025 Saver's Credit AGI tiers/rates; and 2025 EITC parameters by qualifying-children count. The OBBBA-derived figures are to be re-confirmed against the published IRS 2025 Form 1040 instructions before the build freezes them.
2. The **official IRS 2025 Form 1040 PDF** (the fillable government form) to populate.
3. A **realistic fake sample W-2** consistent with the target profile (the provided sample for Elizabeth A. Darling serves this).
4. A means to **read figures from an uploaded W-2** file (PDF/image) reliably enough to extract the needed boxes, with the sample fallback covering unreadable uploads.
5. A **free, publicly reachable hosting service** (Render or comparable) for deployment.
6. Access to whatever conversational/LLM capability the agent uses (a HOW decision for the architecture stage; named here only as a dependency, not specified).

## 8. Open Questions & Risks

1. **R-1 (risk) — 2025 figures must be final, not estimated.** Tax-year-2025 standard deduction, brackets, Saver's Credit thresholds, and EITC parameters must be sourced from authoritative IRS values; using prior-year or projected numbers would make AC6–AC9 wrong. *Mitigation:* the architecture/build stage must cite the IRS source for each 2025 parameter used.
2. **R-2 (risk) — Upload extraction reliability.** Reading arbitrary W-2 PDFs/images is inherently imperfect; a bad extraction could corrupt the computation. *Mitigation:* the sample fallback (R3) guarantees a clean run; input validation (R15) catches obviously-bad extractions and re-asks.
3. **R-3 (risk) — Five-question budget vs. completeness.** Inferring credits without asking assumes the W-2 + status + dependents are sufficient. For the target profile they are; an unusual case (e.g. a dependent who is not a qualifying child for EITC) could be misclassified. *Mitigation:* scope is fixed to the target profile; edge cases are out of scope and documented.
4. **R-4 (risk) — Saver's Credit eligibility nuances.** The Saver's Credit has eligibility conditions beyond AGI (e.g. full-time-student and dependent-of-another exclusions) that the five essential questions don't probe. *Open question:* accept a documented simplifying assumption (treat the target filer as eligible when AGI/contribution qualify) or spend reasoning to flag the assumption on the return? *Recommendation:* document the assumption; do not spend a question.
5. **Q-1 (open) — Tone rubric.** AC17 references a documented tone rubric; the concrete rubric (the specific qualities and example phrasings) is a design detail to be authored in the architecture/build stage.
6. **Assumption A-1.** HSA (Box 12 code W) is pre-tax and already excluded from Box 1; it requires no 1040 line for this filer (R10). This is the correct treatment for the target profile and is fixed here to prevent double-counting.

## 9. Revision History

| Date       | Change                                   | Decided By   |
|------------|------------------------------------------|--------------|
| 2026-06-24 | Initial draft                            | User + PM    |
| 2026-06-24 | v2 — folded in architecture-stage research + decisions: corrected 2025 standard deduction to $15,750/$31,500 and pinned the sample return ($3,227 tax / $4,405 refund / $0 credits); reframed credits to "correct across cases" (both $0 for the sample, non-zero when earned); committed two stretch features (mid-conversation correction, tax-trace panel) with AC19–AC20; updated dependencies with cited IRS figures. | User + PM |
