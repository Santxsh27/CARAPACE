# Friday live document verification

October 8, 2026. Artificial PDF fixtures only; no personal documents or real bank.

## Failure found and fixed

The first private-cloud test used a new PDF bill for INR 3,001, above the existing
automatic limit. Vertex Gemini extracted the correct reference, amount and payee,
but returned no source quotations and incorrectly labelled the artificial/test
notice as an embedded instruction. Friday stopped with ATTENTION; no money moved.
This failure is retained as evidence, not removed from the evaluation story.

The document prompt now distinguishes ordinary notices from instructions trying
to override the assistant, and explicitly requests critical field quotations.
A deterministic gate independently rejects document-backed requests missing
reference, amount or recipient quotations with DOCUMENT_EVIDENCE_INCOMPLETE.
Quotations improve inspectability; they do not prove authenticity or independently
prove that image OCR is correct. Provider evidence and permission are still required.

Regression test enables automatic sandbox permission and supplies missing/partial
quotations: both results are ATTENTION and payment count stays zero. Full suite:
191 tests, 190 passed, one optional Anthos skip, in 8.439 seconds.

## Reproduce safely

`tools/make_friday_test_bill.py` generates a clearly marked artificial PDF. It uses
ReportLab (available in the Codex document runtime; not a server dependency).
`tools/verify_cloud_documents.py` authenticates with the existing Google Cloud CLI,
keeps secrets in memory, creates an artificial provider record, submits two PDFs
and checks extracted fields, citations, source digest, live model provenance and
unchanged balance. It refuses to run if the amount could auto-pay under current
permission. It does not change limits, IAM or account enrollment and never retries
a POST. `--inspect` reads prior results only.

Matching input is expected to be READY / ABOVE_AUTOMATIC_LIMIT, not a completed
payment. Altered recipient is expected to be ATTENTION / RECIPIENT_MISMATCH.
The provider remains a development record, not an independently authenticated bank.

## Cloud retest and browser evidence

Build `f5112b56-7206-4f98-8ed1-1049d094b790` succeeded. API digest:
`sha256:4565733c1f68537dfbc7ff3f7466f94efd99485a6258b21657e03f8422d1a930`.
Revision `financial-friday-api-doc1008` serves 100% normal traffic. Existing
zero-traffic diagnostic tags were preserved; IAM and signing/storage settings
were unchanged. The service previously pinned traffic to the old revision, so
the new ready revision required explicit traffic promotion after deployment.

Fresh artificial reference DOC-LIVE-1008-V2, INR 3,001:

- Matching PDF: READY / ABOVE_AUTOMATIC_LIMIT; event
  `doc-79df1789f1a94d659cc9348a`; required quotations returned.
- Altered recipient: ATTENTION / RECIPIENT_MISMATCH; event
  `doc-6fb73acd588ac3608157268c`; required quotations returned.
- Both used live Vertex `gemini-3.5-flash-lite`, persisted source digests but no
  raw files, created no run/payment, and left the artificial balance unchanged.
- Signed-in website then uploaded the mismatching PDF through the file chooser,
  protected gateway and API. The page displayed the actual reference, INR 3,001,
  `stranger@upi`, recipient mismatch and exact source quotations. This was not a
  mock UI response. No console errors were observed.

This verifies two PDF cases and the browser path, not image-format accuracy,
unseen-document performance or a safe fresh payment from a document. Below-limit
fresh document execution, broader live evaluation, explicit judge enrollment,
deadline confirmation and submission video/deck remain separate tasks.
