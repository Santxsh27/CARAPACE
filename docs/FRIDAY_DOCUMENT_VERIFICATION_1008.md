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

This initial verification covered two PDF cases and the browser path, not
image-format accuracy or unseen-document performance. The later complete
document-to-payment check is recorded below.

## Fresh PDF to one payment, live repair and safe replay

New artificial reference DOC-PAY-1008-49, amount INR 49.00, enrolled development
payee `fridaydocs@upi`. The existing saved permission already allowed the amount;
no permission, reserve, IAM or identity enrollment was changed.

- Live Vertex document interpretation returned the bill facts and quotations.
- Fresh run `ff_8941c311741749c3b435415fae278f2a` completed one artificial payment.
- Gemini's first actual plan was rejected with WRONG_CADENCE: it assigned NONE
  to the payment action. A second live proposal set ONE_TIME and passed. The
  executor ran only after acceptance; this was not a deliberately injected mock.
- One INR 49 debit occurred. The receipt had the correct amount and payee, signature
  and key ID; the server's cryptographically verified receipt count increased by one.
  Operation: `ffpay_d4742aa063bd46319dca860bec92b72d`.
- Replay run `ff_9e1a4eeef182469cb51bf78d7efee1d5` returned ALREADY_COMPLETED,
  reused the identical receipt, made zero model calls and left the balance unchanged.
- The single sampled completion took 10.319 seconds including verification reads.
  It is not an average, p95, model latency benchmark or cost estimate.
- Signed-in cloud browser reopened the completed run with GET only. It displayed
  two planning attempts, passed gate, one effect, six rejected hostile mutations
  and signed receipt. No console errors observed. No additional payment on viewing.

The verification tool's default remains no-payment. Its new explicit
`--allow-artificial-payment` mode is capped at INR 50, checks existing automatic
permission and reserve, refuses recently recorded references, and requires a fresh
completion result. Five offline tooling checks cover caps, permission, reserve and
missing source evidence; CI runs them separately from the 191-test application suite.
Run tooling checks with `python -m unittest discover -s tools -p test_cloud_document_checks.py`.

Broader live evaluation, image accuracy, explicit judge enrollment, deadline
confirmation and submission video/deck remain outstanding. This remains artificial
money with development provider evidence, not an authorized real-bank payment.
