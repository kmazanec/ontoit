# Domain Research: 2025 Federal Income Tax Rules for the OntoIt Tax Assistant

**Confidence summary:** High confidence on all core tax numbers (standard deduction, brackets, credits, W-2 box mechanics); medium confidence on OCR failure characterizations and UX/disclaimer claims where only one or two non-IRS sources could be found.

---

## 1. The 2025 Standard Deduction — Critical Correction

The project brief states the Single standard deduction is $14,600. That figure is wrong for 2025 returns. **$14,600 is the 2024 amount.**

For tax year 2025 (returns filed in 2026), the IRS originally set the Single standard deduction at $15,000 via routine inflation adjustment under Rev. Proc. 2024-40. The One Big Beautiful Bill Act (OBBBA), enacted July 4, 2025, then added $750, bringing the final figure to **$15,750 for Single filers and $31,500 for Married Filing Jointly (MFJ)**. The IRS 2025 Form 1040 instructions (published February 25, 2026) explicitly confirm "$15,750 — Single or Married filing separately." Using the wrong $14,600 figure produces a measurably incorrect refund.

Sources: [IRS 1040 Instructions](https://www.irs.gov/instructions/i1040gi), [Tax Foundation 2025 Brackets](https://taxfoundation.org/data/all/federal/2025-tax-brackets/), [IRS OBBBA guidance](https://www.irs.gov/newsroom/new-and-enhanced-deductions-for-individuals)

---

## 2. 2025 Federal Income Tax Brackets (Single Filers)

The 2025 brackets for Single filers, set by Rev. Proc. 2024-40, are:

| Rate | Income range |
|------|-------------|
| 10% | $0 – $11,925 |
| 12% | $11,925 – $48,475 |
| 22% | $48,475 – $103,350 |
| (higher brackets omitted — not relevant to target profile) |

The sample filer's taxable income of $28,879 falls entirely within the 10% and 12% brackets. The 22% bracket is not reached even by the gross wages of $44,629.

Sources: [IRS Brackets](https://www.irs.gov/filing/federal-income-tax-rates-and-brackets), [Tax Foundation](https://taxfoundation.org/data/all/federal/2025-tax-brackets/)

---

## 3. Tax Calculation for the Sample Single Filer

The sample filer's profile: W-2 Box 1 wages $44,629.35, federal withholding (Box 2) $7,631.62, Single filing status, standard deduction.

**Step 1 — Taxable income:**
$44,629.35 wages minus $15,750 standard deduction = **$28,879.35 taxable income**.

No Schedule 1 adjustments are needed for this profile. The Box 12-D 401(k) deferral and Box 12-W HSA contributions are already excluded from Box 1 wages at the payroll level — they do not appear as additional deductions on the 1040 (see Section 5 below).

**Step 2 — Tax on $28,879.35:**
- 10% on $11,925.00 = $1,192.50
- 12% on $16,954.35 ($28,879.35 − $11,925.00) = $2,034.52
- **Total federal income tax: $3,227.02**

Three independent calculators (SmartAsset: $3,227.02; TurboTax bracket tool: $3,226.98; IRS bracket table: $3,227) agree within rounding. Effective rate: ~7.23%. Marginal rate: 12%.

**Step 3 — Refund:**
$7,631.62 withholding − $3,227.02 tax = **$4,404.60 refund** (before credits; credits are $0 for this profile — see Section 4).

For comparison: if the project had used the incorrect 2024 standard deduction of $14,600, taxable income would be $30,029.35, tax would be $3,365.02, and the refund would be $4,266.60 — a $138 understatement.

Sources: [IRS Brackets](https://www.irs.gov/filing/federal-income-tax-rates-and-brackets), [SmartAsset](https://smartasset.com/taxes/income-taxes), [TurboTax](https://turbotax.intuit.com/tax-tools/calculators/tax-bracket/)

---

## 4. Credits for the Sample Profile: Both Are $0

### 4a. Saver's Credit (Form 8880)

The Saver's Credit rewards lower-income workers for contributing to retirement accounts (401(k), IRA, etc.). The 2025 AGI thresholds for Single filers are:

| Credit rate | AGI range |
|-------------|-----------|
| 50% | $0 – $23,750 |
| 20% | $23,751 – $25,500 |
| 10% | $25,501 – $39,500 |
| 0% | Above $39,500 |

The maximum eligible contribution for a Single filer is $2,000, making the maximum credit $1,000. For MFJ, the $0 threshold is above $79,000 (max credit $2,000 on $4,000 of contributions).

**For the sample filer at AGI $44,629.35 (Single): credit = $0.** The income exceeds the $39,500 Single cutoff.

Three mandatory disqualifiers exist regardless of income: (1) filer under age 18, (2) filer enrolled as a full-time student for any part of 5 calendar months of the year (months need not be consecutive), (3) filer claimed as a dependent on another person's return. For the target working-adult profile, these disqualifiers are unlikely to apply, but the system should document the assumption.

Note on the 2024 vs. 2025 threshold distinction: some sources still publish the 2024 figures ($23,000/$38,250). The 2025 amounts above come from Rev. Proc. 2024-40.

Sources: [IRS Saver's Credit](https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-savings-contributions-credit-savers-credit), [nationaltaxtools.com](https://nationaltaxtools.com/guides/savers-credit/), [Fidelity](https://www.fidelity.com/learning-center/smart-money/savers-credit)

### 4b. Earned Income Tax Credit (EITC)

The 2025 EITC maximum credits and income limits are:

| Qualifying children | Max credit | Single/HOH income limit | MFJ income limit |
|--------------------|------------|------------------------|-----------------|
| 0 | $649 | $19,104 | $26,214 |
| 1 | $4,328 | $50,434 | $57,554 |
| 2 | $7,152 | $57,310 | $64,430 |
| 3+ | $8,046 | $61,555 | $68,675 |

Additional constraints: investment income must be $11,950 or less. Childless filers must be age 25–64 at year-end. Married Filing Separately (MFS) filers are categorically ineligible — there is no exception.

**For the sample Single filer at AGI $44,629.35 with 0 qualifying children: EITC = $0.** The income limit for 0-child Single filers is $19,104; the sample filer exceeds that by more than $25,000.

**Even under MFJ at the same AGI, EITC = $0** for 0 qualifying children: the MFJ limit is $26,214, still far below $44,629.35. EITC with children could apply at MFJ ($44,629 is well below the 1-child MFJ limit of $57,554), but that scenario is outside the sample profile.

Sources: [IRS EITC Tables](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/earned-income-and-earned-income-tax-credit-eitc-tables), [nationaltaxtools.com](https://nationaltaxtools.com/guides/eitc-income-limits/)

---

## 5. W-2 Box 12 Mechanics

Understanding what Box 12 codes do — and do not — require on the 1040 is essential for computing the right taxable income and credits.

### Code D — Traditional 401(k) Elective Deferrals

Pre-tax 401(k) contributions reduce the employee's Box 1 (taxable wages) at the payroll level before the W-2 is printed. The deferral amount appears in Box 12 with Code D as an informational item only, and also in Boxes 3 and 5 (Social Security and Medicare wages, which are not reduced). **There is no separate Schedule 1 deduction line for a standard W-2 employee's 401(k) deferral** — it was already excluded from Box 1.

Box 12-D is an explicitly qualifying contribution type for the Saver's Credit (Form 8880). IRS Publication lists "elective deferrals to a 401(k)" as the canonical qualifying contribution; tax software documentation confirms Codes D, E, F, G, H, S, AA, BB, and EE all feed Form 8880. Two disqualifiers to check: (1) rollover contributions do not qualify, (2) the full-time student exclusion applies.

Sources: [IRS Topic 424](https://www.irs.gov/taxtopics/tc424), [IRS Saver's Credit](https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-savings-contributions-credit-savers-credit), [TaxSlayer Pro Form 8880](https://support.taxslayerpro.com/hc/en-us/articles/360033760274-Desktop-Form-8880-Retirement-Savings-Credit)

### Code W — HSA Contributions

Box 12 Code W captures all pre-tax HSA contributions made through payroll — both employer contributions and employee salary-reduction (cafeteria plan) elections. Because these are excluded from Box 1 wages, they do not appear as income on 1040 Line 1a.

For Form 8889 (HSA), per IRS instructions, Code W amounts go on **Line 9 (employer contributions)**, not Line 2 (employee contributions). Employee payroll HSA deductions via a cafeteria plan are treated as employer contributions for Form 8889 purposes. The Code W amount is checked to ensure it does not exceed the annual HSA contribution limit; any excess is taxable. **No additional Schedule 1 deduction is available** for amounts already excluded from Box 1.

**LOW-CONFIDENCE NOTE:** The specific routing of Code W to Form 8889 Line 9 is confirmed by IRS Form 8889 instructions and one secondary source, but could not be independently verified against a third source. The conclusion is consistent with IRS guidance and should be correct, but flag this for double-checking against the actual 2025 Form 8889 instructions.

Sources: [IRS Form 8889 Instructions](https://www.irs.gov/instructions/i8889), [ustax.tools](https://ustax.tools/w2-box/12/)

---

## 6. W-2 OCR Extraction: Common Failure Modes and Validation Rules

### Most Common Failure: Box 12 Code-Amount Pairing

Box 12 can hold up to four separate entries, each consisting of a one- or two-letter code plus a dollar amount. Generic OCR systems frequently collapse all Box 12 text into a single unstructured blob, losing the code-to-amount pairing. This directly breaks Saver's Credit and HSA computation. Validation rule: each extracted Box 12 entry must have exactly one alphabetic code (one to two characters) plus one decimal dollar amount.

**LOW-CONFIDENCE NOTE:** The characterization of Box 12 as "the single most common OCR failure mode" and the specific description of codes being collapsed into one cell come from two industry sources and a developer blog post, not from a formal published study. The structural claim is well-corroborated; the specific failure-rate statistics are not independently verifiable.

Sources: [invoicedataextraction.com](https://invoicedataextraction.com/blog/w2-data-extraction), [apspayroll.com](https://apspayroll.com/blog/how-to-avoid-w2-errors/)

### Cross-Field Math Validation

These relationships hold by IRS construction and can catch OCR gross misreads:

- Box 4 (Social Security tax withheld) = 6.2% of Box 3 (SS wages), up to the SS wage base
- Box 6 (Medicare tax withheld) = 1.45% of Box 5 (Medicare wages); can exceed 1.45% for wages over $200,000 due to the 0.9% Additional Medicare Tax
- Box 2 (federal income tax withheld) must be less than Box 1 (wages); as a rough plausibility check, Box 2 as a fraction of Box 1 should fall within roughly 10–37% (matching the marginal bracket range)

For the sample filer: Box 2 ($7,631.62) / Box 1 ($44,629.35) = 17.1% — within the plausible range, passing validation.

**Note:** The "10–37% range" is a marginal-bracket heuristic for plausibility screening, not an empirically derived effective-rate band. Very low-income or high-credit filers may legitimately fall outside it.

Sources: [invoicedataextraction.com](https://invoicedataextraction.com/blog/w2-data-extraction), [developer blog](https://dev.to/romdevin/addressing-w-2-and-1099-nec-data-extraction-challenges-with-a-scalable-backend-solution-2mel)

### SSN and EIN Identifier Errors

A single transposed digit in the SSN causes IRS name/TIN mismatch rejection. OCR commonly confuses: '0' with 'O', '1' with 'l' or 'I', '5' with 'S', '8' with 'B'. Heuristic validation: SSN must match ###-##-#### with exactly 9 digits; EIN must match ##-####### with exactly 9 digits; SSN must not start with 000 or 9.

Sources: [invoicedataextraction.com](https://invoicedataextraction.com/blog/w2-data-extraction), [Patriot Software](https://www.patriotsoftware.com/blog/payroll/avoid-these-common-errors-on-the-w-2-form/)

### Multi-State W-2s (Lower Priority)

Boxes 15–20 repeat per state in a grid. Linear OCR can merge rows or swap withholding amounts between states. For the target single-employer, single-state profile this failure mode can be deprioritized, but it should be noted for future multi-state support.

**LOW-CONFIDENCE NOTE (single source):** This finding comes from a single industry source and could not be independently verified.

Sources: [invoicedataextraction.com](https://invoicedataextraction.com/blog/w2-data-extraction)

### Common User-Introduced Errors

IRS identifies: missing or inaccurate SSNs (each digit must match the Social Security card exactly), filing before all W-2/1099 documents arrive, and incorrect income figures that trigger automated matching notices. Tax software eliminates arithmetic errors but not data-entry errors — accurate user input is the primary quality dependency for a W-2 interview tool.

Sources: [IRS errors guidance](https://www.irs.gov/newsroom/errors-taxpayers-should-watch-out-for-when-preparing-a-tax-return), [IRS common mistakes](https://www.irs.gov/newsroom/common-tax-return-mistakes-that-can-cost-taxpayers)

---

## 7. Competitor UX: TurboTax and FreeTaxUSA

### TurboTax

TurboTax uses an interview-style UX with one question at a time, milestone-based section structure, expectation-setting ("Here's what's coming up"), and W-2 import via phone camera or PDF upload. This approach works well for simple W-2 filers conceptually.

**The primary pain point is not tax complexity — it is commercial friction.** User reviews and the FTC's January 2024 Final Order against Intuit document: (1) price hidden until filing is nearly complete; (2) automatic add-ons raising costs from $69 to $172 without explicit consent; (3) Audit Defense pop-ups requiring dismissal on every session; (4) dashboard ad walls before reaching tax data. The FTC found TurboTax's "free" advertising deceptive.

**LOW-CONFIDENCE NOTE:** The specific UX mechanics (milestone structure, one-task-at-a-time framing) are drawn from a single UX analysis blog (Appcues). The FTC enforcement action is well-documented; the specific user-friction characterizations rely on community forum posts and review aggregators.

Sources: [financer.com TurboTax review](https://financer.com/review/turbotax/), [SmartAsset comparison](https://smartasset.com/taxes/freetaxusa-vs-turbotax), [TurboTax community forum](https://ttlc.intuit.com/community/taxes/discussion/major-usability-issues-in-turbotax-2025-feedback-from-a-20-year-customer/00/3848047), [Appcues UX analysis](https://www.appcues.com/blog/how-turbotax-makes-a-dreadful-user-experience-a-delightful-one)

### FreeTaxUSA

FreeTaxUSA is transparent about fees upfront (free federal, $14.99 state) and is noted positively in comparison reviews for that reason. The primary pain point is limited import capability — W-2 data from some employers can be imported, but not from all; users frequently must type information manually from paper or PDF documents. This creates transcription error risk. There is no live tax expert.

**LOW-CONFIDENCE NOTE (medium confidence):** FreeTaxUSA's import limitations are characterized based on two sources (a review blog and FreeTaxUSA's own marketing page). The exact set of supported import providers was not independently verified.

Sources: [The College Investor FreeTaxUSA review](https://thecollegeinvestor.com/20918/freetaxusa-review/), [FreeTaxUSA switch page](https://www.freetaxusa.com/switch/)

---

## 8. Disclaimers and Legal Guardrails

### "Not Tax Advice" Disclaimer — Industry Standard, Not Mandated

No statute or regulation mandates specific disclaimer language for software that fills out a 1040 but does not e-file. IRS Publication 1345 governs authorized e-file providers (not applicable to a form-filling assistant). The FTC Safeguards Rule covers data security, not disclaimer language. IRS Circular 230 covered-opinion requirements were eliminated in 2014.

However, both major competitors use functionally identical disclaimers: TurboTax's Terms of Service state "Intuit is not in the business of providing tax professional service or advice" unless specifically disclosed; FreeTaxUSA's Terms of Use state the service is "not intended to provide specific tax advice to any individual" and recommend consulting a tax professional. The standard pattern the system should follow: the tool is informational only, it is not a substitute for professional advice, and results depend on the accuracy of information the user provides.

**LOW-CONFIDENCE NOTE (medium confidence):** The conclusion that no statutory disclaimer mandate exists relies on a search of regulatory sources; the absence of a finding is not a guarantee. Consult a licensed attorney before commercial deployment.

Sources: [Intuit ToS](https://www.intuit.com/legal/terms/en-us/turbotax/online-license/), [FreeTaxUSA ToS](https://www.freetaxusa.com/terms/), [fynk.com clause library](https://fynk.com/en/clauses/tax-disclaimer/), [CAMICO Circular 230 update](https://www.camico.com/blog/alert-revised-circular-230-regulations-now-effective/)

### Tax Return Preparer Status Under 26 CFR §301.7701-15

Any person who "prepares for compensation... all or a substantial portion of any return of tax" is a tax return preparer under federal regulation and is subject to Circular 230 and PTIN requirements. For a free hackathon tool, the "for compensation" element is not met, so the preparer rules do not apply. The safe design pattern is: (1) the system is offered free of charge, (2) it produces a reviewable output the user must personally review and sign, (3) the disclaimer states the user is self-preparing and the tool is an aid only.

If the system is ever monetized or produces a completed signed return, preparer-status analysis becomes mandatory.

Sources: [26 CFR §301.7701-15](https://www.law.cornell.edu/cfr/text/26/301.7701-15), [Intuit Accountants Circular 230 overview](https://accountants.intuit.com/taxprocenter/tax-law-and-news/practicing-before-the-irs-what-you-need-to-know/)

---

## References

All sources cited inline above. Key primary sources:

- IRS 2025 Form 1040 Instructions: https://www.irs.gov/instructions/i1040gi
- IRS 2025 Tax Brackets: https://www.irs.gov/filing/federal-income-tax-rates-and-brackets
- IRS Saver's Credit: https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-savings-contributions-credit-savers-credit
- IRS EITC Tables: https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/earned-income-and-earned-income-tax-credit-eitc-tables
- IRS Form 8889 Instructions (HSA): https://www.irs.gov/instructions/i8889
- IRS W-2 Instructions: https://www.irs.gov/instructions/iw2w3
- IRS Topic 424 (401k): https://www.irs.gov/taxtopics/tc424
- Tax Foundation 2025 Brackets: https://taxfoundation.org/data/all/federal/2025-tax-brackets/
- 26 CFR §301.7701-15 (preparer definition): https://www.law.cornell.edu/cfr/text/26/301.7701-15
