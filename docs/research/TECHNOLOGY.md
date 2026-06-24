# Technology Research — OntoIt Tax Assistant

**Confidence summary:** Core architecture choices (PDF filling, W-2 extraction, deterministic tax computation, SSE streaming, guardrail enforcement, session state) are well-supported by multiple independent sources; two areas carry medium confidence and are flagged explicitly below.

---

## PDF Form Filling

### pdfrw and the NeedAppearances Flag

For filling the IRS 1040 AcroForm on a free-tier host without a headless browser, the most practical pure-Python approach is pdfrw with the `NeedAppearances` flag. pdfrw directly manipulates PDF AcroForm widget annotations: you iterate page annotations, match field names via the `/T` key, write the value as a `/V` PdfString, then call:

```python
pdf.Root.AcroForm.update(pdfrw.PdfDict(NeedAppearances=pdfrw.PdfObject('true')))
```

This tells every conforming PDF viewer to regenerate field appearance streams on open, so the filled values become visible. The library is pure Python with no system dependencies and runs on any free host. [westhealth.github.io, dev.to/pdffillr_ai, github.com/py-pdf/pypdf issue #546]

The confirmed failure mode: if a user prints the PDF directly from a download dialog — bypassing a viewer — fields may still appear blank. Flattening after fill eliminates this risk.

**Critical caveat — Adobe Reader compatibility:** GitHub issue #213 on the pdfrw repository documents that PDFs filled with pdfrw fail to open in Adobe Reader on Windows for at least one user class, while working correctly in Chrome, Edge, and Opera. Because the IRS explicitly recommends Adobe Reader for its forms, this is a meaningful risk for a downloadable 1040. This finding is flagged as **medium confidence** because the failure has been reproduced but the scope of affected configurations is not fully characterized. [github.com/pmaupin/pdfrw issue #213, irs.gov/help/downloading-and-printing]

### PyMuPDF as the More Robust Alternative

PyMuPDF (imported as `fitz`) fills fields via `widget.update()` and offers three finalization strategies: read-only flags (keeps fields extractable), `bake()` (converts fields to static searchable text), and image conversion at 300 DPI (eliminates interactivity entirely). The `bake()` method is the most reliable for a downloadable output PDF because it converts all field content to static text, eliminating NeedAppearances rendering inconsistencies and Adobe Reader version dependencies entirely. [artifex.com, pdf4.dev]

Documented IRS-specific caveat: checkbox fields on IRS tax forms use non-standard `'Yes'`/`'Off'` state names that can cause PyMuPDF to silently revert checkboxes to OFF in some PDF rendering engines. This requires explicit handling. [github.com/pymupdf/PyMuPDF issue #4055]

### Why pypdf (PyPDF2's Successor) Is Unsuitable

pypdf's `update_page_form_field_values()` has a documented defect: it does not regenerate appearance streams (AP streams) when writing field values. The result is that filled values display as visually blank until the user clicks the field or re-saves the document in Acrobat. For a download-and-print demo, the output must look correct without viewer intervention. This is not a performance issue or an edge case — it is the documented behavior of the library's writer. [dev.to/pdffillr_ai, github.com/py-pdf/pypdf issue #546, pypdf.readthedocs.io]

Additionally, pypdf silently produces blank output for fields with non-Latin characters or subset fonts, with no error raised — the library simply cannot regenerate glyphs for fonts it does not have full access to. For IRS 1040 name fields with diacritics this is a real failure mode. [dev.to/pdffillr_ai]

### IRS Form 1040 Field Name Discovery

The IRS does not publish a schema or field-name manifest for Form 1040's AcroForm annotations. Field names must be discovered by programmatic inspection of the downloaded PDF (`https://www.irs.gov/pub/irs-pdf/f1040.pdf`). The pattern: iterate `template.pages`, read `/Annots`, extract `/T` (field name) and `/Rect` (bounding box) from each widget. Field names follow patterns like `f1_01[0]`, `f1_02[0]`. The form also embeds an XFA stream that can complicate standard AcroForm extraction in some libraries. This enumeration step must be repeated each year when the IRS publishes a revised form. [westhealth.github.io, irs.gov/pub/irs-pdf/f1040.pdf]

Note: the IRS does publish MeF XML schemas, but these cover the electronic filing XML format, not the internal AcroForm field names of the fillable PDF.

---

## W-2 Data Extraction

### Claude Vision as the Primary Extraction Path

For a hackathon with a single known document layout, Claude vision (Sonnet-class) with a strict JSON schema via `tool_use` is the lowest-friction extraction approach. A head-to-head comparison of text-based PDF extraction shows GPT at 98%, Claude at 97%, Gemini at 96% (Koncile.ai study). For scanned W-2s, Gemini led at 94% due to native multimodal, with Claude at 90%. Claude produces the best consistency of format — JSON-schema-valid output in all circumstances — which is what matters when the extracted values feed a downstream computation pipeline. Claude structured outputs via `tool_use` have a less-than-0.2% schema non-compliance rate across 300,000 calls (TokenMix.ai). [koncile.ai, tokenmix.ai, anthropic-cookbook]

**Accuracy figures are flagged as medium confidence** for the scanned-document case: the 95–98% digital and 85–92% scanned figures are derived from third-party benchmarks (Koncile.ai, Intsurfing) that used invoice and document sets, not IRS W-2s specifically. The relative ranking (Claude near-top for digital, Gemini leading for scans) is consistent across sources. [intsurfing.com, claudeimplementation.com]

To guard against hallucination on low-confidence fields (email, website, unusual box values), include a `confidence` field in the extraction schema and substitute null for low-confidence results.

### Cost: Claude vs. AWS Textract

AWS Textract charges approximately $0.03 per two-page document ($0.015/page). Claude token-based pricing for a W-2 extraction is approximately $0.00125 per document, making Claude roughly 24x cheaper per document at baseline. With retries, the effective Claude cost rises to $0.003–$0.004 per document, still an order of magnitude cheaper. Beyond cost, Textract requires AWS SDK setup and IAM credentials — a full day's overhead for a one-day build. [intsurfing.com]

### pdfplumber for Native-Digital W-2s

pdfplumber extracts text from the vector/text layer of machine-generated PDFs with near-100% accuracy for structured forms with constant layouts. It supports coordinate-based field extraction — crop a bounding box around a known field region, extract the text. For the IRS W-2, which is a fixed-layout IRS-spec form, the coordinates are stable across employers. [jsvine/pdfplumber, woteq.com]

pdfplumber fails completely on image-only or scanned W-2s because it has no OCR. The recommended two-step strategy: attempt pdfplumber text extraction first; if no text layer is detected, fall back to Claude Vision. This gives deterministic accuracy for digital PDFs and vision-based accuracy for scans. [jsvine/pdfplumber]

### Why pytesseract Is Not Recommended

pytesseract (Tesseract OCR) averages approximately 80% real-world accuracy on structured forms, degrading to 12–18% character error rates below 200 DPI. It has no table or structure detection — output is raw text with no guaranteed reading order — making regex-based box extraction brittle. W-2 Box 12 sub-codes (D, W) require structural parsing that pytesseract cannot provide without heavy preprocessing. For a one-day hackathon, pytesseract is the worst tradeoff: low accuracy, high maintenance, and no upside over the pdfplumber + Claude Vision combination. [extend.ai, intsurfing.com]

---

## Tax Computation: Deterministic Python, Not LLM Arithmetic

### Why LLMs Must Not Compute Tax Values

Multiple independent sources converge on this conclusion. TaxCalcBench (2025) evaluated frontier models on IRS tax scenarios and found the best-performing model (Gemini 2.5 Pro) achieved only 32% strict accuracy on tax calculations; even with a ±$5 lenient threshold, accuracy reached only 52%. Fifteen to twenty percent of failures were caused by models using percentage-based bracket arithmetic instead of the IRS-required Tax Table lookup for incomes under $100,000. [arxiv.org/html/2507.16126v1]

The LLM Agentic Tax Software paper (2025) found that Claude 3.5 in an agentic framework with structured JSON tax-rule references achieved 93% PP@1 versus a 39% baseline — a 54-point improvement from adding deterministic scaffolding. The lesson: routing all arithmetic to deterministic tools transforms LLM tax accuracy. [arxiv.org/html/2509.13471]

Moveo.ai's financial domain analysis documents five specific error mechanisms: carry drift in long multiplication; rounding policy mismatch; locale confusion (12.345 vs. 12,345); unit confusion (basis points treated as percentages); and period misinterpretation (annual rate applied monthly). [moveo.ai]

Python arithmetic is deterministic: the same calculation run 1,000 times yields identical results. An LLM's "calculation" is stochastic even at temperature=0, due to floating-point non-determinism in GPU operations. [dev.to/nodefiend, scoopanalytics.com]

### The IRS Tax Table Requirement

The sample filer (wages $44,629.35, standard deduction Single $14,600, taxable income approximately $30,029) falls below the $100,000 threshold at which the IRS requires use of the Tax Table — a pre-computed lookup, not bracket arithmetic. The Tax Table rounds taxable income to the nearest $50 and returns a pre-computed tax amount. A model applying the 10%/12% bracket formula to the exact dollar figure produces a different result. TaxCalcBench identifies this as the most common LLM failure pattern. The fix in Python is trivial: embed the IRS Tax Table as a sorted list of `(income_floor, income_ceiling, tax_amount)` tuples and binary-search it. [arxiv.org/html/2507.16126v1, irs.gov/instructions/i1040gi]

### Which Computations Must Live in Python

All of the following must be Python-side tools, never LLM-side generation:

- IRS Tax Table lookup
- EITC eligibility determination and credit computation (includes phase-out range arithmetic and poverty-level figures)
- Saver's Credit tier lookup (non-linear step function the LLM may interpolate instead of look up)
- Standard deduction application
- Withholding vs. tax liability comparison (refund or amount owed)

The LLM's role is intake (clarifying questions), extraction (W-2 parsing), and output (friendly plain-language explanation). All numbers flow through code. [moveo.ai, dev.to/nodefiend, arxiv.org/html/2507.16126v1, arxiv.org/html/2509.13471]

---

## Streaming: SSE over WebSockets

For streaming LLM tool-call events to a chat UI, Server-Sent Events (SSE) via FastAPI `StreamingResponse` is the correct choice. SSE is unidirectional (server to client), uses plain HTTP with `content-type: text/event-stream`, and requires no special client library — the browser `EventSource` API handles reconnection automatically.

The latency advantage of WebSockets over SSE is approximately 3ms, which is lost in the noise against typical LLM response times of 50–500ms. WebSockets add bidirectional protocol overhead, reconnection boilerplate (roughly 50 lines vs. 10 for SSE), and sticky-session scaling complexity, with no practical benefit for a chat assistant where the client sends a single POST and reads a stream. OpenAI's own streaming completions API uses SSE, validating the approach at production scale. [dev.to/polliog, akanuragkumar.medium.com, fastapi.tiangolo.com]

The structured event vocabulary for agentic streaming: `start`, `token`, `tool_call`, `tool_result`, `done`, `error` — each as a JSON payload with an event type field. Both Anthropic and OpenAI streaming APIs use SSE natively. [callsphere.ai, dev.to/pockit_tools]

Key footgun: HTTP status code cannot change mid-stream, so errors must be sent as typed SSE events, not HTTP error codes. The browser-native `EventSource` API only supports GET; for POST-initiated SSE the client uses `fetch()` with `ReadableStream`.

---

## Guardrails: Enforcing the 5-Question Budget

### Why Prompt-Only Counters Fail

A system-prompt instruction or application-level Python counter that the LLM can see is not a guardrail — it is a suggestion the model can be prompted to ignore. OWASP's LLM Prompt Injection Prevention cheat sheet notes that "a guardrail LLM is itself an LLM and is itself susceptible to prompt injection," and recommends controls "outside the LLM's decision path — in application logic that the model cannot influence." [owasp.org, render.com/articles, arxiv.org/pdf/2412.16682]

Research on guardrail evasion (arXiv 2504.11168) documents that character injection and adversarial ML techniques defeat LLM-based classification guardrails. For a tax assistant where user-uploaded content (W-2 PDF text, form answers) is fed back to the LLM, indirect prompt injection via document content is a realistic attack vector. [arxiv.org/pdf/2504.11168, blogs.cisco.com]

### The Correct Pattern

The FastAPI request handler checks `session['questions_asked'] >= 5` before calling the LLM API and returns a fixed refusal string if the budget is exhausted. This check executes in Python before any LLM call is dispatched. A Python integer in the server process cannot be incremented or reset by the content of the user's message.

The turn counter lives in server-side session state, not in the LLM's context window. It is incremented after each user-facing question is emitted, by the application code, not by the model. A framework-level pre-tool-call hook (e.g., Strands `BeforeToolCallEvent` or equivalent middleware wrapping the tool dispatch layer) that runs outside the LLM's decision loop provides the strongest defense; for a simpler implementation, the pre-dispatch check in the request handler is the minimum viable guardrail. [dev.to/aws, arxiv.org/html/2504.11168v1, relayplane.com]

Structured output fields like `questions_remaining` returned by the LLM provide no security: the LLM generates that field and the user content in the same inference pass, meaning a crafted prompt can instruct the model to return `questions_remaining: 5` regardless of the true count.

---

## Session State on Render Free Tier

### The Ephemeral Filesystem Problem

Render's official documentation states: "any changes to your web service's filesystem (uploaded images, local SQLite databases, etc.) are lost every time the service redeploys, restarts, or spins down." Free web services cannot attach persistent disks. Free services spin down after 15 minutes of inactivity, with a 30–60 second cold start on the next request. [render.com/docs/free, render.com/docs/disks, blog.samkiel.dev]

SQLite on the ephemeral filesystem resets on spin-down, providing no advantage over in-memory state. Render's free Redis-compatible Key Value instance is also in-memory only and loses all data on restart — it is functionally equivalent to an in-memory Python dict for a single-instance deployment. The only scenario where Redis adds value is multi-process or multi-instance state sharing, which does not occur on a single free-tier instance. [render.com/docs/free, dashdashhard.com]

### Recommended Mitigation

Encode the full conversation history in a signed cookie (or send it in each POST body) and eliminate server-side session state entirely. The conversation history for a 5-question chat session — question counter, extracted W-2 fields as JSON, LLM message list — is small enough (approximately 2–5 KB) to fit in a signed cookie. The FastAPI handler reads the session from the cookie on each request, appends the new message, calls the LLM, updates the counter, then writes the updated session back into the response cookie. [render.com/docs/free, owasp.org Session Management Cheat Sheet]

Cookie security baseline: `HttpOnly; Secure; SameSite=Strict`. For a hackathon demo with a live judge, a browser tab pinging the service every 10 minutes prevents the 15-minute spin-down from occurring mid-demo.

---

## Model Selection

### Claude Sonnet for Tool-Use Reliability

On TAU-bench (tool-agent-user benchmark, Sierra 2024), which measures pass^k — probability of success across k repeated runs — Claude 3.7 Sonnet achieves 81.2% on retail tasks versus OpenAI o1's 73.5%. For the hackathon's narrow use case (single W-2, 5 questions, deterministic computation routed to Python tools), this reliability advantage is meaningful: the demo must produce a correct 1040 on the first run in front of a judge. [sierra.ai/blog/tau-bench, anthropic.com/news/claude-3-7-sonnet]

On BFCL (Berkeley Function Calling Leaderboard), Claude Sonnet scores approximately 70–80% depending on the version benchmark. **This is flagged as medium confidence**: figures vary across sources (klavis.ai reports 70.29% for Claude Sonnet 4; Spheron estimates ~80% for Claude Sonnet 4.6 on BFCL v4), and the benchmarks were run on different BFCL versions. The relative conclusion — Claude is competitive with GPT-4o for structured extraction with a small tool set — is consistent. For 3–4 tools (vs. 100+), all frontier models approach ceiling performance; the differentiator is JSON schema compliance. [klavis.ai, spheron.network, tokenmix.ai]

### Why Haiku Is Insufficient for Multi-Step Tool Orchestration

ComplexFuncBench reports Claude 3.5 Haiku at 45.80% overall success rate with 69.50% call accuracy. The gap between call accuracy and success rate reveals that Haiku often invokes the right tool but with wrong parameters or in the wrong sequence — exactly the failure mode that would produce an incorrect 1040. Haiku's cost advantage (~$0.80/MTok vs. Sonnet's ~$3/MTok) does not outweigh the reliability gap for a demo requiring a correct output. **This finding is flagged as medium confidence**: it comes from a single benchmark source (ComplexFuncBench GitHub) and has not been independently corroborated in this review. [github.com/zai-org/ComplexFuncBench]

### Gemini Flash: Capable but Higher Setup Cost

Gemini Flash 2 and 2.5 improved substantially in function calling relative to early Gemini versions. In the Koncile.ai scanned-invoice study, Gemini led at 94% for scan accuracy due to integrated vision. For OntoIt, where W-2 uploads are likely digital PDFs, Claude's format-consistency advantage is more relevant than Gemini's scan-accuracy advantage. Gemini's main disqualifier for a one-day build is additional SDK setup and the need to separately verify schema compliance. **This finding is flagged as medium confidence** because the early-2024 Gemini function-calling weakness may not apply to 2025/2026 Gemini versions. [koncile.ai, deciphr.ai]

---

## References

1. westhealth.github.io — "Exploring Fillable Forms with pdfrw" — pdfrw AcroForm pattern
2. dev.to/pdffillr_ai — "I tried every popular library for programmatic PDF form filling" — pypdf appearance-stream gap
3. github.com/py-pdf/pypdf issue #546 — pypdf NeedAppearances / blank fields
4. pypdf.readthedocs.io/en/stable/user/forms.html — pypdf forms documentation
5. github.com/pmaupin/pdfrw issue #213 — pdfrw Adobe Reader open failure
6. irs.gov/help/downloading-and-printing — IRS Adobe Reader recommendation
7. irs.gov/pub/irs-pdf/f1040.pdf — IRS Form 1040 (2025)
8. artifex.com/blog/automating-pdf-form-filling-and-flattening-with-pymupdf — PyMuPDF fill/bake
9. pdf4.dev/blog/how-to-flatten-pdf — PDF flattening strategies
10. github.com/pymupdf/PyMuPDF issue #4055 — PyMuPDF checkbox IRS state names
11. koncile.ai — "Claude, GPT or Gemini: Which is the best LLM for invoice extraction?"
12. tokenmix.ai/blog/structured-output-json-guide — Claude tool_use schema compliance
13. github.com/anthropics/anthropic-cookbook — structured JSON extraction notebook
14. extend.ai/resources/pytesseract-guide-ocr-limits-alternatives — pytesseract accuracy limits
15. intsurfing.com — "Amazon Textract vs Anthropic PDF to JSON: accuracy, cost and scale"
16. github.com/jsvine/pdfplumber — pdfplumber documentation
17. woteq.com — pdfplumber structured field extraction
18. aimultiple.com/ocr-accuracy — OCR accuracy comparison
19. marktechpost.com — OCR model comparison 2025
20. render.com/docs/free — Render free tier limits
21. render.com/docs/disks — Render disk/persistence docs
22. blog.samkiel.dev — Render cold start timing
23. medium.com/@prajju.18gryphon — Render free apps keep-alive
24. dashdashhard.com — Render free tier guide
25. dev.to/polliog — "Server-Sent Events beat WebSockets for 95% of real-time apps"
26. akanuragkumar.medium.com — streaming AI agent responses with SSE
27. fastapi.tiangolo.com/tutorial/server-sent-events — FastAPI SSE
28. callsphere.ai — FastAPI SSE streaming AI
29. dev.to/pockit_tools — complete guide to streaming LLM responses
30. cheatsheetseries.owasp.org — LLM Prompt Injection Prevention Cheat Sheet
31. render.com/articles — prompt injection guardrails
32. arxiv.org/pdf/2412.16682 — guardrail susceptibility to prompt injection
33. arxiv.org/pdf/2504.11168 — guardrail evasion via character injection
34. blogs.cisco.com — "Prompt injection is the new SQL injection"
35. dev.to/aws — "AI Agent Guardrails: Rules that LLMs cannot bypass"
36. arxiv.org/html/2504.11168v1 — indirect prompt injection via tool calls
37. relayplane.com/blog/agent-runaway-costs-2026 — agent turn budget enforcement
38. cheatsheetseries.owasp.org — Session Management Cheat Sheet
39. sierra.ai/blog/tau-bench — TAU-bench benchmark methodology and results
40. anthropic.com/news/claude-3-7-sonnet — Claude 3.7 Sonnet announcement
41. klavis.ai — "Function Calling and Agentic AI in 2025: BFCL benchmark"
42. spheron.network — tool-calling benchmarks BFCL v4 approximate figures
43. github.com/zai-org/ComplexFuncBench — ComplexFuncBench multi-step function calling
44. deciphr.ai — "Gemini Flash is surprisingly good for agents and function calling"
45. moveo.ai/blog/why-llm-struggle — LLM numeric error types in financial domains
46. dev.to/nodefiend — "Trust the server, not the LLM: deterministic approach"
47. scoopanalytics.com — "Why LLMs struggle with basic math"
48. arxiv.org/html/2507.16126v1 — TaxCalcBench (2025): LLM tax calculation accuracy
49. arxiv.org/html/2509.13471 — LLM Agentic Tax Software (2025): agentic scaffolding improvement
50. irs.gov/instructions/i1040gi — IRS 1040 General Instructions (Tax Table requirement)
51. claudeimplementation.com/blog/claude-vision-api — Claude Vision API accuracy
