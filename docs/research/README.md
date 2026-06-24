# Research — OntoIt

OntoIt is a hackathon project to build an agentic tax-filing assistant: a web chat where a user with a single W-2 (~$40k/year wages) uploads their document, answers at most five friendly questions, and downloads a completed, correct 2025 IRS Form 1040 PDF.

---

## Research files

| File | Covers | Confidence |
|------|--------|------------|
| [DOMAIN.md](./DOMAIN.md) | 2025 tax rules: corrected standard deduction ($15,750 Single / $31,500 MFJ, not the brief's stale $14,600 figure), tax brackets, full sample-filer calculation ($3,227 tax / $4,405 refund), why both credits are $0 for the sample profile, W-2 Box 12 mechanics (Code D and Code W), OCR failure modes and validation rules, competitor UX patterns (TurboTax / FreeTaxUSA), and disclaimer / preparer-status legal analysis. | **High** — core numbers come from IRS primary sources; three low-confidence flags on Box 12-W routing, Box 12 OCR failure-rate statistics, and the statutory disclaimer analysis. |
| [TECHNOLOGY.md](./TECHNOLOGY.md) | PDF form-filling library selection (pdfrw vs PyMuPDF vs pypdf), IRS AcroForm field-name discovery, W-2 extraction approach (Claude Vision + pdfplumber two-step, Textract cost comparison, pytesseract rejection), why tax arithmetic must live in deterministic Python (TaxCalcBench: best LLM achieves only 32% strict accuracy), IRS Tax Table lookup requirement, SSE vs WebSocket tradeoffs for streaming, server-side guardrail enforcement pattern, Render free-tier ephemeral filesystem constraints and cookie-based session mitigation, and model selection rationale (Sonnet vs Haiku vs Gemini Flash). | **High** — architecture choices corroborated by multiple independent sources; four medium-confidence flags on pdfrw Adobe Reader compatibility scope, scanned-document extraction accuracy figures, Haiku ComplexFuncBench single-source finding, and early-Gemini function-calling weakness applicability to 2025/2026 versions. |
| [MARKET.md](./MARKET.md) | Free-filing landscape (IRS Free File $89k AGI threshold, IRS Direct File elimination), competitor pricing (TurboTax Deluxe ~$129 for sample filer profile, H&R Block ~$35 Deluxe, FreeTaxUSA $0/$15.99, Cash App Taxes $0/$0), FTC enforcement actions ($141M TurboTax settlement, $7M H&R Block settlement), incumbent AI architectures (Intuit's deterministic-engine / LLM-wrapper separation, H&R Block Azure OpenAI at 1.91M messages), TaxCalcBench LLM accuracy data, emerging B2B competitors (April $78M raised, Column Tax / Aiwyn), Intuit's deliberate retreat from low-ARPR filers, and regulatory framework (EFIN/PTIN not required for PDF-output tools, §7216 privacy obligations apply). | **High** — pricing, enforcement actions, and AI architecture details sourced from primary documents and confirmed enforcement orders; three medium-confidence flags on H&R Block exact pricing, incumbent AI inline-disclaimer wording, and TurboTax Claude/ChatGPT connector corroboration; one explicit low-confidence flag on the "tool vs. preparer" regulatory synthesis (no direct IRS guidance on AI-generated PDFs exists). |

---

## Caveats

The following questions could not be established with confidence and should be verified by a human before betting a decision on them.

**Tax law**

- The $15,750 Single standard deduction derives from the One Big Beautiful Bill Act (OBBBA), signed July 4, 2025. Verify against the published 2025 Form 1040 instructions (https://www.irs.gov/instructions/i1040gi) before hardcoding the figure — Congress could amend or phase figures differently for MFJ / HOH.
- W-2 Box 12 Code W routing to Form 8889 Line 9 (employer contributions) rather than Line 2 (employee contributions) is confirmed by IRS instructions but could only be cross-verified against two sources. Read the actual 2025 Form 8889 instructions before implementing.
- Both credits (Saver's Credit and EITC) compute to $0 for the sample Single filer. If the MFJ scenario is exercised and children are added, EITC eligibility changes significantly — the research covers the childless case only.

**Technology**

- pdfrw's Adobe Reader compatibility failure (GitHub issue #213) is reproduced but its scope across Reader versions and OS configurations is unknown. If the downloadable 1040 must open correctly in Adobe Reader on Windows, test PyMuPDF `bake()` as the default path before choosing pdfrw.
- IRS AcroForm field names (e.g., `f1_01[0]`) are discovered by inspection of the downloaded PDF, not from a published IRS schema. These names may change in the 2025 form revision — run the field-enumeration script against the live `https://www.irs.gov/pub/irs-pdf/f1040.pdf` before building the fill logic.
- Render free-tier spin-down behavior (15-minute idle, 30–60 second cold start) is documented in Render's own docs but specific timing figures come from a single third-party blog. Verify with a live Render deployment before the demo.

**Market and regulatory**

- The "tool vs. preparer" regulatory boundary (no PTIN / EFIN required for a free PDF-output assistant under 26 CFR §301.7701-15) is based on analogy to existing IRS guidance for software developers; the IRS has issued no direct guidance for AI-generated tax PDFs. Obtain qualified tax counsel's opinion before any commercial deployment.
- §7216 imposes criminal penalties for unauthorized disclosure of taxpayer data gathered through the software. The research confirms it applies to this product but does not constitute legal advice on what disclosures satisfy it. Verify with counsel before launch.
- Competitor pricing figures (TurboTax Deluxe, H&R Block Deluxe, Cash App Taxes HSA form support) are from mid-2026 secondary sources. Prices and supported form sets change each filing season — confirm at the start of each development cycle.
- The TaxCalcBench LLM accuracy figures (23–32% strict accuracy for frontier models on Form 1040 scenarios) come from a single source, Column Tax, which is itself a competitor in this space. The directional conclusion — LLMs cannot do tax math reliably without deterministic scaffolding — is corroborated by the separate LLM Agentic Tax Software paper and by Intuit's own published architecture; the specific percentages should be treated as indicative, not precise.
