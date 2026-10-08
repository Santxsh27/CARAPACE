# Financial Friday — release and handoff

October 9, 2026. This is a working artificial-money pilot, not unrestricted bank access or a claim that the whole submission is complete.

## One coherent product

Delegate a verified household bill within saved rules. Gemini understands the new input and proposes a typed plan; independently retrieved provider evidence and strict code validate the financial effects; a restricted executor acts once; Friday records a signed receipt and checks a previous outcome before retrying. AI can correct a rejected plan, but cannot relax permission or alter the production ledger. Voice transcripts, QR text and document inputs use the same safety boundary.

## What changed in this release

- One home request starts the real task, instead of copying text and asking for another click.
- Saved automatic artificial-payment permission is disclosed next to the request. My rules remains separate from financial execution.
- Home is less crowded: compact assistant core, four task choices, fewer repeated shortcuts, restrained colours and a desktop navigation rail.
- A dedicated outcome explains what happened, why and the next action. Confirmed, stopped and unverified states use labels as well as colours.
- Repeated run metrics are moved into the technical evidence disclosure; loading a saved receipt clears stale outcomes.
- Unsupported AI text quotations are discarded before persistence and display, with a recorded count. Documents still use model-produced quotations, not independently verified OCR.
- The live evaluation now covers sixteen fresh cases and checks exact extraction and retained quotation provenance, not just an expected badge.

## Measured verification

The isolated current suite ran 195 tests: 194 passed and one optional Anthos integration test skipped. Eleven offline tooling tests passed. Generated JavaScript syntax passed using the installed alternate Node runtime. Running unit tests inside the active Anthos-enabled service is not equivalent to an isolated test environment: two bridge-dependent tests failed there; the correctly isolated suite passed. No production data was reset to make tests pass.

On October 8 the earlier expanded live batch `EVAL-713B5AEAC504` matched 16/16 expected financial outcomes/fields, but manual review found two non-verbatim quotations. Those findings motivated the deterministic quotation filter; they are not counted as perfect quotation accuracy.

The private candidate then checked fresh `EVAL-22EE2847225F`, INR 3,001, above the unchanged automatic limit:

| Check | Result |
|---|---|
| Expected state/reason and exact financial fields | 16/16 passed |
| Retained text quotations occur in original input | 16/16 passed after server filtering |
| Ordinary one-time, reordered, reserve-respecting, negated recurrence, rupee/comma formatting, mixed Hindi/Tamil requests | Eight READY; explicit approval needed; no payment |
| Changed recipient, wrong amount, recurring request, unknown reference, impersonation and hostile/mixed instructions | Eight ATTENTION; no payment |
| Live model provenance | Vertex AI, gemini-3.5-flash-lite |
| Account balance | Unchanged |
| Sample API latency | Median 2.240 s; maximum 7.824 s |
| Token usage/cost | Not measured by this endpoint |

This is a small hand-authored regression corpus, not held-out fraud accuracy, a plain-Gemini comparison, comprehensive localization or a p95 latency measurement. Earlier 14/16 results and the undiagnosed provider 503 remain in the historical reports. Retained quotes may be a subset of the model's proposed quotes; substring membership does not establish claim authenticity or correct arithmetic.

Cross-revision replay of `doc-27c031b4ab95230a7492295c` returned ALREADY_COMPLETED, existing operation `ffpay_d4742aa063bd46319dca860bec92b72d`, key `09fa77671c19ebc6`, and unchanged balance 4,250,600 minor units (INR 42,506). No new debit or model call. Anonymous API access was rejected.

## Cloud release

API revision `financial-friday-api-ready1008`, version 0.13.2, was tested at zero normal traffic, then promoted to 100%. Immutable API digest:
`sha256:04fff203e02541d2ca756df47f0c44055c0dd627619ddb19572747253dab6cd1`.

Build `65e72122-f263-49e3-a161-b58c44fdaea7` deployed the simplified private website as `financial-friday-web-ready1008`. Follow-up UI-only build `a2ea0708-12b0-4422-9768-54ed07ec327b` completed the progressive disclosure cleanup. Revision `financial-friday-web-final1009` now serves 100% traffic with immutable digest `sha256:111440c7b3ba6040ad1a1e52f24f7360d52ea712851f3fcdeb874c1f1ca04edf`. IAP and owner-only access are preserved; no new IAM permissions, real financial provider or banking credential was added.

The local working folder remains `/Users/santosh/Desktop/CARAPACE`; no new repository was created. Existing unrelated `control_room_future.py` edits and Finder metadata are excluded from this release.

The October 9 final isolated container suite passed again: 195 tests in 26.791 seconds, 194 passed and one optional skip; eleven tooling tests passed. Local Friday and API returned HTTP 200/healthy after Docker restart, preserving named volumes. The promoted private API replay again retained the original operation, signature key and balance with zero new model calls/debits, and rejected anonymous access. The owner browser checked a new changed-recipient message and the completed read-only receipt; screenshots and UX limits are in [the final flow check](UI_VERIFICATION_1009.md).

## Demo and fallback

1. Use the signed-in Cloud Run website. Inspect My rules before any task; do not broaden limits just to make a sample succeed.
2. Bills → Demo provider setup: publish a fresh artificial reference, amount and payee. This is an explicitly same-operator development provider, not a real utility integration.
3. Submit unfamiliar wording on Home, or upload a matching synthetic bill PDF in Documents. Within enabled permission it can complete one artificial payment; otherwise it awaits approval or stops.
4. Change the recipient: show the contradiction and no money moved.
5. Open the completed task from Activity: inspect the original receipt without another debit.
6. In Safety lab, show an unavailable one-time option and an uncertain prior success. Explain that the bank adapter, not the AI, controls external effects.

If live AI fails, show the clearly labelled local comparison or an already-recorded receipt. Do not present a replay as a fresh AI call or a fake animation as a completed payment. `START_HERE.md` contains local Docker instructions; named volumes must be preserved.

## What still needs the owner or organizer

- Confirm deadline, eligibility, team and build-window rules in the actual Hack2skill dashboard. No current dashboard evidence was supplied.
- Approve specific judge/demo Google identities or obtain an organizer-approved access method. Owner-only IAP currently prevents arbitrary judges from opening the app. Do not make the financial API public to solve that.
- Complete video, deck and submission form fields; excluded from the requested implementation run.

## Not implemented / production roadmap

Independent provider authorization and real settlement, native Gemini Live voice, direct phone SMS, always-on durable Cloud Tasks scheduling, comprehensive model comparison/cost evaluation and independent security/privacy/compliance review are not implemented. Cloud budget alerts are not spending caps. Signed receipts do not guarantee the truth of a malicious same-operator provider. No zero-fraud, world-first, patentability or award guarantee is made.
