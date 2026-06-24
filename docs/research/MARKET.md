# Market Research: Tax Filing Software Landscape

**Confidence summary:** Core competitive, pricing, and regulatory findings are high-confidence with multiple corroborating sources; incumbent AI architecture findings are high-confidence from primary documentation; UX complaint patterns are high-confidence from primary sources and confirmed enforcement actions; one synthesized regulatory conclusion (AI-generated PDF as "tool not preparer") is explicitly low-confidence.

---

## The Free Filing Landscape

### IRS Free File

For tax year 2024 (filed in 2025), IRS Free File covered filers with AGI at or below $84,000. For tax year 2025 (filed in 2026), the threshold rose to $89,000 — one of the largest annual increases in the program's history. Eight partners participate in the 2026 season: 1040.com, 1040Now, EzTaxReturn, FileYourTaxes.com, FreeTaxUSA, OnLine Taxes, TaxAct, and TaxSlayer. TurboTax and H&R Block are not on the list; both withdrew in 2021. A W-2 filer earning around $44,600 easily qualifies, though each partner sets its own additional eligibility criteria (age, resident state, etc.). The $89,000 limit covers roughly 70% of all US taxpayers. [IRS.gov Free File; CNBC, Jan 2025; taxspecialty.com; money.com; apps.irs.gov]

### IRS Direct File — Eliminated

IRS Direct File launched for the 2024 filing season as a government-operated free tool targeted directly at simple W-2 filers. By 2025 it had reached 30 million eligible taxpayers across 25 states and earned a 98% user satisfaction rating. The 2025 budget reconciliation bill mandated its elimination; DOGE disbanded the 18F team that built it. Taxpayers who relied on it now must use IRS Free File (private partners) or paid software for the 2026 season. [Yahoo Finance; Nextgov; indexbox.io]

---

## Who Charges What

### TurboTax

TurboTax Free Edition is $0 federal and $0 state, but only roughly 37% of all filers qualify. Eligibility is restricted to simple Form 1040 returns with no schedules beyond EITC, Child Tax Credit, and student loan interest. W-2 filers with Box 12-D (retirement deferrals) or Box 12-W (HSA contributions) — like the OntoIt sample filer — are pushed to TurboTax Deluxe, which runs approximately $129 federal for tax year 2025. Filers needing the Saver's Credit (Form 8880, directly relevant to Box 12-D retirement savers) cannot use the Free Edition and must upgrade. The remaining 63% of filers encounter a forced upgrade prompt after entering sensitive personal data, mid-filing. [TurboTax.intuit.com; financeauthorityhub.com; CNBC; The College Investor]

### H&R Block

H&R Block's Free Online tier covers a broader set of situations than TurboTax — roughly 52% of filers qualify — and includes student loan interest, retirement income, and some HSA situations that TurboTax reserves for paid tiers. However, the Saver's Credit is not included in the free tier; H&R Block presents the credit amount mid-flow and then requires a Deluxe upgrade to actually claim it, a pattern multiple users describe as a bait-and-switch. Current Deluxe pricing is approximately $35 federal (not $49.99 as cited in some older sources — **medium confidence; pricing varies by source and season**). H&R Block AI Tax Assist is available only in paid Deluxe and above. [moneydoneright.com; flavor365.com — pricing figures medium confidence]

### FreeTaxUSA

FreeTaxUSA charges $0 for all federal returns with no income limit and no form restrictions. State filing costs $15.99. An optional Deluxe tier ($7.99) adds live chat support; a Pro Support tier ($44.99) provides CPA/EA access. There are no forced upgrades. FreeTaxUSA participates in IRS Free File, so filers with AGI at or below $89,000 may also get state filing free through that program. Multiple independent reviewers consistently name FreeTaxUSA the best value for any return more complex than the simplest W-2 scenario. For the OntoIt sample filer (Box 12-D, Box 12-W, Saver's Credit), FreeTaxUSA is the lowest-cost compliant option at $0 federal / $15.99 state — or potentially $0/$0 via Free File. [freetaxusa.com; CNBC; Yahoo Finance]

### Cash App Taxes

Cash App Taxes is $0 for both federal and state with no paid tiers, no income limit, and no upsells. It covers W-2, EITC, Child Tax Credit, Schedule C, Schedule D, and Schedule E, all at no cost. It covers 40 states plus DC; multi-state returns are not supported. Audit defense is included at no charge. Cash App Taxes does not participate in IRS Free File and operates independently. **Low-confidence caveat:** user reports indicate possible HSA form limitations (relevant to Box 12-W), but exact supported form boundaries were not confirmed against Cash App's current help documentation. [cash.app/taxes; CNBC; The College Investor; wealthvieu.com — HSA limitation flagged as medium confidence, single-source]

### Pricing Tier Summary

The market splits into three pricing models:

1. **Genuinely free (federal and state):** Cash App Taxes — $0/$0, no tiers, no upsells.
2. **Free federal / paid or upsell state:** TurboTax (Free Edition for ~37% of filers, Deluxe ~$129), H&R Block (Free for ~52%, Deluxe ~$35), FreeTaxUSA ($0 federal / $15.99 state).
3. **B2B SaaS / API:** April and Column Tax/Aiwyn — priced to institutional partners, not consumers; no publicly listed per-return consumer price exists for either.

No AI-first company has yet published a per-return consumer price. [getapril.com; alleywatch.com; prnewswire.com]

---

## Enforcement Actions and Regulatory History

### Intuit (TurboTax) — $141 Million Settlement

In May 2022, Intuit settled with all 50 states and DC for $141 million after being found to have deliberately steered IRS Free File-eligible users toward paid TurboTax products. The company had internally identified eligible users but hidden the free path; fewer than 3% of eligible taxpayers used IRS Free File in 2020. Approximately 4.4 million customers received refund checks averaging around $30. A separate FTC cease-and-desist order issued in January 2024 bars deceptive "free" advertising going forward. [PBS NewsHour; CNBC Jan 2024; California AG press release]

### H&R Block — $7 Million FTC Settlement

The FTC filed a complaint in February 2024 and finalized a $7 million settlement in January 2025 after finding that H&R Block deleted users' previously entered tax data when they attempted to downgrade from a paid tier to the free tier — requiring a call to customer service to downgrade at all. H&R Block was ordered to stop this practice by February 15, 2025, to restore user data on downgrades by the 2026 filing season, and to disclose in "free" advertising what percentage of taxpayers actually qualify. [FTC press release Jan 2025; Kiplinger; Yahoo Finance]

---

## User Frustrations with Incumbent Software

### TurboTax UX Complaints

The most-cited pattern for TurboTax's simple W-2 filers:

- **Aggressive upsell loops** that require active dismissal multiple times (Audit Defense re-prompted after explicit rejection, advertisement screens required on login before accessing the tax return).
- **Mid-filing forced upgrades** triggered by common situations — student loan interest, Saver's Credit, HSA — revealed only after the user has entered personal data.
- **Usability regressions** paired with price increases: the donations calculator was removed, W-2 Box 14 handling requires extra steps, employer state tax IDs are cleared and re-prompted each year.
- **Total time burden:** multiple users report tasks that should take under an hour consuming 3–4.5 hours.

ProPublica documented Intuit's lobbying against free IRS filing and deliberate obscuring of the free-tier access. [TurboTax community forum 2025; Hacker News; Slashdot]

### H&R Block UX Complaints

H&R Block's primary complaint pattern:

- **Data deletion as a sales tactic** — confirmed by the FTC enforcement action and now prohibited.
- **Incorrect computed values** despite correct user input: independent consumer reviews document cases where H&R Block computed an incorrect Federal Income Tax Withheld from properly entered W-2 data.
- **Bait-and-switch on credits:** the interface shows the Saver's Credit amount and then requires an upgrade to claim it.

[FTC press release Nov 2024; ConsumerAffairs.com; Yahoo Finance]

### Industry-Wide Complaint Pattern

A SmartCustomer analysis of hundreds of user reviews identified the top three complaints across tax software: (1) technical errors during filing (53%), (2) hidden fees up to $130 revealed only at submission (36%), and (3) refund miscalculations (19%). **Medium confidence — single source; methodology not independently verified.** The hidden-fee pattern is structurally corroborated by the FTC enforcement actions against both Intuit and H&R Block. [smartcustomer.com — flagged medium confidence, single source]

---

## Who Incumbents Are Actually Targeting

### Intuit's Strategic Retreat from Low-Income Filers

Intuit's FY2025 earnings confirm the company is deliberately yielding share in the low-revenue segment: TurboTax Online units declined 1% and total TurboTax units declined 2% due to "yielding share with lower ARPR customers." Free-tier (zero-pay) customers fell from approximately 8 million to approximately 7 million. **Medium confidence — the directional shift is confirmed; the specific customer count figures come from a single earnings press release and have not been cross-verified.** Intuit is steering investment toward TurboTax Live (assisted filing at $150–$500+) and higher-ARPR filers. This creates a genuine market gap for a low-friction free option targeting the $40k W-2 segment the incumbents are intentionally abandoning. [Intuit FY2025 investor press release]

### H&R Block's Adjacent Revenue Strategy

H&R Block's off-season revenue from the $40–50k W-2 filer segment comes primarily from adjacent financial products (Spruce prepaid card, MyBlock, Wave small business), not from filing fees. For both incumbents, a $44k single W-2 filer with no itemized deductions is a customer-acquisition target for upsells, not a primary revenue source. [PBS NewsHour; portersfiveforce.com; report.woodard.com]

---

## How Incumbents Are Using AI

### Intuit's Architectural Guardrail

Intuit explicitly separates LLM-generated explanations from tax calculations. All numerical computations run through Intuit's deterministic, rule-based tax engine; the LLM layer (Intuit Assist) wraps around it to provide conversational explanations, surface relevant questions, and guide the user through the flow. The LLM never touches the underlying math. Intuit's internal GenOS platform uses a dual-query approach (static pre-engineered explanations plus dynamic ad-hoc queries), and content-filtering ML models detect hallucinated numbers and inappropriate advice before they reach users. Internal systems GenEval and GenSRF monitor hallucination rates in production. This is documented in Intuit's own engineering materials, not just marketing claims. [ZenML LLMOps Database; TurboTax blog; AARP]

Intuit Assist is available within TurboTax as part of the product. Intuit monetizes further through "Expert Assist" — live CPA/EA access — which the AI is designed to escalate to when questions exceed its scope. The Expert Assist price point is approximately $89–$209 federal depending on tier. **Medium confidence on specific Expert Assist pricing — the $159 figure cited in some sources is not confirmed; the range comes from user-reported charges.** [AARP; TurboTax community forum]

In early 2026, TurboTax launched connector apps for Claude and ChatGPT, offering real-time tax estimates and refund projections as a new front-end distribution channel while leaving the backend tax engine unchanged. **Medium confidence — announced by TurboTax blog; independently corroborated sources limited.** [TurboTax blog Jan 2026]

### H&R Block AI Tax Assist

H&R Block's AI Tax Assist is powered by Azure OpenAI and trained on content from The Tax Institute (H&R Block's in-house CPAs, tax attorneys, and enrolled agents). By the 2025–2026 tax season, it had handled 1.91 million client messages at a 2.2-second average response time. The feature is explicitly restricted to paid Deluxe and above tiers — it is not available in the free tier. H&R Block positions it as guidance informed by experts, not as tax advice, and the system uses guardrails and inline limitations (e.g., "Sorry, I'm not trained on that content yet") rather than claiming comprehensive coverage. **Medium confidence on the inline disclaimer wording — reported by a single product review, not confirmed by primary H&R Block documentation.** [H&R Block newsroom; H&R Block AI recognition press release; AARP; maa1.medium.com — disclaimer wording flagged as medium confidence, single source]

### Why LLMs Cannot Do Tax Math Alone

Column Tax's TaxCalcBench (2025) tested four frontier models — Gemini 2.5 Pro, Gemini 2.5 Flash, Claude Opus 4, and Claude Sonnet 4 — on 51 synthetic Form 1040 scenarios. Strict accuracy (exact match on the computed return) ranged from 23% (Claude Sonnet 4) to 32% (Gemini 2.5 Pro). With a ±$5 tolerance, accuracy rose to 38–52%. Primary failure modes were misusing percentage-based bracket calculations instead of IRS lookup tables (15–20% of errors) and cascading arithmetic errors on credits like EITC. Column Tax's published conclusion: "AI can't do your taxes on its own (yet) — reliable tax computation requires additional scaffolding and orchestration beyond raw LLM calls." This benchmark is the empirical basis for the industry-wide practice of keeping LLMs out of the calculation engine. **Note: this benchmark comes from a single source (Column Tax itself, a competitor in this space); the methodology has not been independently replicated as of mid-2026.** [columntax.com/blog/taxcalcbench — primary source is the company itself; treat with appropriate skepticism on exact numbers]

---

## Emerging AI-Native Competitors

### April

April is a B2B2C embedded tax platform that sells flat-rate SaaS licenses to institutional partners — banks, fintechs, payroll providers — who white-label the filing experience for their customers. April raised a $38 million Series B in July 2025 (led by QED Investors), bringing total funding to $78 million, and became the first new company in more than 15 years to achieve national e-file coverage across all 50 states. Partners include PayPal. Median filing time on April's platform is 22 minutes versus the IRS average of 13 hours. April is infrastructure for financial institutions, not a direct-to-consumer competitor. [Yahoo Finance; alleywatch.com; businesswire.com; pymnts.com]

### Column Tax (acquired by Aiwyn)

Column Tax built what it describes as the first modern personal income tax engine in two decades and has filed 1+ million returns through its B2B2C model (embedded in banks, brokerages, and financial apps). Column Tax was acquired by Aiwyn, which is targeting accounting firms at enterprise pricing. Column Tax's "Iris" AI development agent expands edge-case coverage, but Column Tax's own roadmap states complete tax automation is multiple years away. [columntax.com blog; prnewswire.com]

---

## Regulatory Framework

### What Does and Does Not Require IRS Registration

Tax return preparation is not "practice before the IRS" under current law and therefore falls outside IRS Circular 230 registration requirements. Generating a filled-out 1040 PDF does not by itself require a PTIN (Preparer Tax Identification Number) or EFIN (Electronic Filing Identification Number). Specifically:

- **EFIN** is required only if a party electronically transmits returns to the IRS on behalf of clients (i.e., acts as an e-file provider). The EFIN application requires a suitability check including criminal history and tax compliance review, taking 30–45 days minimum. A product that outputs a PDF for the user to download, sign, and self-file bypasses this requirement entirely.
- **PTIN** is required only for compensated preparers who actually prepare returns for others. A free software tool that produces a PDF for user review and self-submission is not a compensated preparer.
- **§7216 privacy obligations** apply to any software developer with access to taxpayer data gathered through the software. This imposes criminal penalties for unauthorized disclosure or use of that data. It does not require PTIN or EFIN, but it does require privacy disclosures to users.

[IRS.gov EFIN FAQ; IRS e-file provider pages; ultimatetax.com; law.cornell.edu CFR §301.7216-1 and -2]

### The "Tool vs. Preparer" Line

The key regulatory boundary is whether a system makes substantive determinations affecting tax liability (regulated practice, requiring Circular 230 compliance) versus transparently computing results from IRS rules based on user-confirmed inputs (technical facilitation). An AI that computes credits and explains them steps toward substantive territory; one that fills in values the user has confirmed and shows the underlying IRS rule being applied steps back from it.

**Low-confidence caveat: IRS has not issued explicit guidance for AI-generated PDFs. The analysis above is based on analogies to existing rulings on software developers and e-file providers. A product launched in this space should obtain qualified tax counsel's opinion before deployment.** [IRS.gov e-file mandate FAQ; law.cornell.edu CFR §301.7216-2 — regulatory synthesis flagged as low confidence; no direct IRS guidance on AI-generated PDFs exists]

---

## Strategic Implications for OntoIt

A conversational agent that produces a completed 1040 PDF for user self-filing occupies a specific and currently underserved position:

- **The $40k W-2 filer is a segment incumbents are actively abandoning** (Intuit FY2025 earnings, confirmed above) while simultaneously being their historic captive audience for upsell revenue.
- **The two most common W-2 filer complaints** — hidden upgrade fees revealed after data entry, and forced upsell loops requiring repeated dismissal — are solvable by a product with no upgrade path and a strict question budget.
- **FreeTaxUSA and Cash App Taxes** already offer $0-or-near-$0 federal filing with no upsells. The competitive differentiation for an AI agent is not price (incumbents have matched $0) but experience: no upsell friction, transparent computation, conversational interface, and a clear paper trail of how each line was computed.
- **The PDF-output architecture** is the correct regulatory choice for a hackathon build. It avoids EFIN requirements entirely while staying within the §7216 data-privacy framework (which requires disclosure, not registration).
- **LLMs should not perform tax calculations directly** (Column Tax benchmark: 23–32% strict accuracy). Any credible implementation must pair conversational guidance with a deterministic computation layer, matching the Intuit architectural pattern.

---

## References

1. IRS.gov — Free File general info: https://www.irs.gov/newsroom/file-for-free-with-irs-free-file
2. CNBC — IRS Free File 2025 qualifications: https://www.cnbc.com/2025/01/21/irs-free-file-who-qualifies-for-2025-taxes.html
3. taxspecialty.com — IRS Free File 2026: https://taxspecialty.com/irs-free-file-2026/
4. money.com — IRS Free File income limit 2026: https://money.com/irs-free-file-income-limit-2026/
5. apps.irs.gov — Free File partner list: https://apps.irs.gov/app/freeFile/general/
6. TurboTax — pricing page: https://turbotax.intuit.com/personal-taxes/online/
7. financeauthorityhub.com — TurboTax Free 2026 real limits: https://financeauthorityhub.com/turbotax-free-2026-real-limits/
8. CNBC — TurboTax review: https://www.cnbc.com/select/turbotax-review/
9. The College Investor — TurboTax vs H&R Block vs TaxAct: https://thecollegeinvestor.com/15201/comparing-prices-turbotax-hr-block-tax-act/
10. moneydoneright.com — H&R Block review: https://moneydoneright.com/taxes/personal-taxes/hr-block-review/
11. flavor365.com — H&R Block pricing breakdown 2025: https://flavor365.com/h-r-block-pricing-a-complete-breakdown-of-2025-costs/
12. FreeTaxUSA — pricing: https://www.freetaxusa.com/pricing/
13. FreeTaxUSA — Saver's Credit: https://www.freetaxusa.com/credit/savers/
14. FreeTaxUSA — Free File 2025: https://www.freetaxusa.com/freefile2025/
15. CNBC — FreeTaxUSA review: https://www.cnbc.com/select/freetaxusa-review/
16. Yahoo Finance — FreeTaxUSA 2026 review: https://finance.yahoo.com/news/freetaxusa-2026-tax-2025-210816199.html
17. cash.app — Cash App Taxes: https://cash.app/taxes
18. CNBC — Best free tax software (Cash App Taxes): https://www.cnbc.com/select/best-free-tax-software/
19. wealthvieu.com — Cash App Taxes review: https://wealthvieu.com/cash-app-taxes-review/
20. The College Investor — Cash App Taxes review: https://thecollegeinvestor.com/39045/cash-app-taxes-review/
21. Yahoo Finance — IRS Direct File eliminated: https://finance.yahoo.com/news/the-irss-free-direct-online-tax-filing-tool-is-being-eliminated-heres-what-you-need-to-know-174646192.html
22. Nextgov — Senators demand IRS path forward after Direct File: https://www.nextgov.com/digital-government/2026/02/senators-demand-know-irs-path-forward-following-end-direct-file/411421/
23. indexbox.io — IRS Direct File discontinued 2026: https://www.indexbox.io/blog/irs-direct-file-program-discontinued-for-2026-tax-season-1/
24. AARP — Tax return AI overview: https://www.aarp.org/money/taxes/tax-return-ai/
25. H&R Block — AI power newsroom: https://www.hrblock.com/tax-center/newsroom/company-news/ai-power-combined-with-digital-enhancements/
26. H&R Block — AI recognition press release: https://www.hrblock.com/tax-center/newsroom/company-news/ai-powered-tax-platform-earns-industry-recognition/
27. maa1.medium.com — H&R Block AI Tax Assist product review: https://maa1.medium.com/h-r-block-ai-tax-assist-product-review-dce8ce9b6e77
28. hrtech-pulse.com — H&R Block AI tools 2026: https://www.hrtech-pulse.com/news/hr-block-leverages-ai-and-digital-tools-to-lead-tax-season-2026/
29. ZenML — Intuit/TurboTax LLMOps case study: https://www.zenml.io/llmops-database/large-scale-tax-ai-assistant-implementation-for-turbotax
30. TurboTax blog — GenAI tax preparation: https://blog.turbotax.intuit.com/breaking-news/tax-preparation-powered-by-gen-ai-59318/
31. TurboTax blog — Claude/ChatGPT connectors: https://blog.turbotax.intuit.com/tax-help/turbotax-on-claude-chatgpt-for-ai-tax-help-144205/
32. TurboTax community forum — Expert Assist charges: https://ttlc.intuit.com/community/taxes/discussion/i-was-charged-for-turbotax-online-expert-assist-premium-2025-i-didn-t-request-these-services-nor-was/00/3749691
33. Column Tax — TaxCalcBench blog: https://www.columntax.com/blog/taxcalcbench
34. Column Tax — Master plan blog: https://www.columntax.com/blog/our-secret-master-plan-to-automate-tax-filing
35. getapril.com — April for developers: https://www.getapril.com/for-developers
36. alleywatch.com — April Series B profile: https://www.alleywatch.com/2025/07/april-embedded-b2b2c-tax-ai-powered-embedded-planning-infrastructure-platform-ben-borodach/
37. businesswire.com — April Series B press release: https://www.businesswire.com/news/home/20250723253218/en/april-Raises-38M-Series-B-to-Embed-Tax-into-Every-Financial-Decision
38. Yahoo Finance — April funding news: https://finance.yahoo.com/news/ai-powered-tax-platform-april-105700248.html
39. pymnts.com — PayPal and April: https://www.pymnts.com/taxes/2026/paypal-and-april-team-on-faster-tax-filing/
40. fintech.global — April raises $38M: https://fintech.global/2025/07/24/ai-tax-platform-april-raises-38m-to-expand-embedded-services/
41. prnewswire.com — Aiwyn/Column Tax pilot: https://www.prnewswire.com/news-releases/aiwyn-seeks-100-firms-for-groundbreaking-tax-pilot-following-column-tax-acquisition-302642515.html
42. Intuit — FY2025 investor press release: https://investors.intuit.com/news-events/press-releases/detail/1266/intuit-reports-strong-fourth-quarter-and-full-year-fiscal-2025-results-sets-fiscal-2026-guidance-with-double-digit-revenue-growth-and-continued-operating-margin-expansion
43. PBS NewsHour — TurboTax $141M settlement: https://www.pbs.org/newshour/economy/turbotax-customers-to-receive-restitution-checks-for-141m-settlement
44. CNBC — FTC bans TurboTax deceptive ads: https://www.cnbc.com/2024/01/23/ftc-bans-deceptive-advertising-for-free-filing-from-turbotax-.html
45. California AG — TurboTax settlement: https://oag.ca.gov/news/press-releases/attorney-general-bonta-announces-distribution-141-million-settlement-millions
46. FTC — H&R Block final order: https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-finalizes-order-hr-block-requiring-them-pay-7-million-overhaul-advertising-customer-service
47. Kiplinger — H&R Block FTC order: https://www.kiplinger.com/taxes/ftc-orders-h-and-r-block-to-revamp-practices-and-pay-millions
48. Yahoo Finance — H&R Block data deletion: https://finance.yahoo.com/news/customers-spent-hours-inputting-their-info-hr-block-deleted-it-as-a-sales-tactic-ftc-says-172513299.html
49. FTC — H&R Block downgrading practices Nov 2024: https://www.ftc.gov/news-events/news/press-releases/2024/11/ftc-action-stops-hr-blocks-unfair-downgrading-practices-deceptive-promises-free-filing
50. ConsumerAffairs — H&R Block: https://www.consumeraffairs.com/finance/hr-block.html
51. TurboTax community forum — 20-year customer feedback 2025: https://ttlc.intuit.com/community/taxes/discussion/major-usability-issues-in-turbotax-2025-feedback-from-a-20-year-customer/00/3848047
52. Hacker News — TurboTax dark patterns: https://news.ycombinator.com/item?id=31073944
53. Slashdot — TurboTax dark patterns: https://news.slashdot.org/story/19/04/22/2139215/turbotax-uses-dark-patterns-to-trick-you-into-paying-to-file-your-taxes
54. SmartCustomer — Top three tax filing complaints: https://www.smartcustomer.com/resources/the-taxing-truth-the-top-three-complaints-about-online-tax-filing-services
55. SmartAsset — H&R Block vs TurboTax: https://smartasset.com/taxes/hr-block-vs-turbotax
56. refundatlas.com — TurboTax vs H&R Block 2026: https://refundatlas.com/blog/turbotax-vs-hr-block-2026
57. trendharvest.blog — TurboTax vs H&R Block vs FreeTaxUSA 2026: https://trendharvest.blog/blog/turbotax-vs-hr-block-vs-freetaxusa-2026
58. IRS.gov — Become an authorized e-file provider: https://www.irs.gov/e-file-providers/become-an-authorized-e-file-provider
59. IRS.gov — How tax prep software is approved for e-filing: https://www.irs.gov/e-file-providers/how-tax-preparation-software-is-approved-for-electronic-filing
60. IRS.gov — EFIN FAQ: https://www.irs.gov/e-file-providers/faqs-about-electronic-filing-identification-numbers-efin
61. IRS.gov — E-file mandate FAQ: https://www.irs.gov/e-file-providers/frequently-asked-questions-e-file-requirements-for-specified-tax-return-preparers-sometimes-referred-to-as-the-e-file-mandate
62. IRS.gov — Software developers technical fact sheet: https://www.irs.gov/e-file-providers/software-developers-technical-fact-sheet
63. ultimatetax.com — EFIN and PTIN for new preparers: https://ultimatetax.com/blog/understanding-efin-and-ptin-for-new-tax-preparers/
64. law.cornell.edu — 26 CFR §301.7216-1: https://www.law.cornell.edu/cfr/text/26/301.7216-1
65. law.cornell.edu — 26 CFR §301.7216-2: https://www.law.cornell.edu/cfr/text/26/301.7216-2
66. cpatrendlines.com — Circular 230 changes: https://cpatrendlines.com/2025/01/17/major-changes-to-circular-230-implications-for-tax-professionals-cornerstone-report/
67. portersfiveforce.com — H&R Block business model: https://portersfiveforce.com/blogs/how-it-works/hrblock
68. report.woodard.com — H&R Block $7M settlement context: https://report.woodard.com/articles/hr-blocks-7-million-settlement-reminiscent-of-recent-tax-cases-fpwr
