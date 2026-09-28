# Operations milestone 1 — executable financial resolution

28 September 2026. Development increment; no real funds or production connectors.

## Implementation

The homepage shows six financial cases. Gemini selects bounded evidence lookups, then synthesises a typed financial resolution program using the retrieved records. Server-owned connectors return synthetic supplier, order, delivery, credit and prior-payment records. Exact rules report missing evidence and conflicts, or establish the supported obligation. A separate verifier checks the model's proposed actions; a mandate gate atomically saves the action journal, signed resolution, synthetic posting and completed run.

Routine: ₹4.8 lakh. Partial delivery and credit: 80 × ₹4,800 − ₹24,000 = ₹3.6 lakh, allowed only by explicit partial-payment terms. The executable program records a ₹96,000 deferral, applies the approved ₹24,000 credit and posts the remaining ₹3.6 lakh. A deferral is an outstanding obligation, not a saving or waived debt. Changed accounts, unavailable records and conflicting receipts stay held. Document instructions cannot edit connector records or acquire a payment tool.

Only four fixed verbs are supported: defer undelivered goods, apply an approved credit, recognise a prior payment and post the remaining payment. Generated code is never executed. Exact checks bind the invoice, beneficiary, currency, source evidence, action amounts and ordering. Six negative guard tests reject modified or incomplete programs. Invalid schema or unsupported actions can receive one bounded correction attempt; persistent invalidity and model errors never trigger a silent local fallback.

Runs persist with tenant-scoped IDs. Repeat requests reconcile the same invoice; concurrent posts serialise in SQLite. Signing or journal failure rolls back. Routine actions need no customer confirmation under the fixed development mandate. The earlier browser-confirmed experiment remains at `/payment-check`.

The UX now leads with completed actions and the exact outstanding issue. Provider details, action-program checks, the graph and raw evidence are expandable instead of becoming the main experience. Old saved runs are labelled honestly: a pre-program posting is not retrospectively presented as AI-generated resolution.

## Interfaces

- `GET /v1/operations/cases`
- `POST /v1/operations/cases/{case_id}/resolve` with `{"planner":"configured"}` or explicit `local`
- `GET /v1/operations/runs/{run_id}`

Existing tenant authentication applies. The local web proxy keeps the API key off the browser. Synthetic operation routes register only in development/test.

## Verification

Full Docker suite with the authorised local Anthos database enabled: **119 tests passed; no skips** (`Ran 119 tests in 6.658s`, `OK`). Tests cover execution, arithmetic variants, partial-payment terms, holds, tenant isolation, unsupported tools/citations, misleading model explanations, model failure, changed snapshots, limits, concurrency, tampering and atomic rollback. Resolution tests additionally cover correction of unsafe or malformed proposals, repeated invalid output, all six guard challenges, double-credit prevention and corrupt journal readback. Adapter tests verify the dynamic tool/citation schema and bounded evidence-plan correction.

Comparison command: `python -m carapace_core.operations_benchmark`. All six fixture outcomes matched the expected result. Adaptive local rules retrieved 18 records versus 30 for fetch-all. These are six hand-authored fixtures, not an unseen corpus, a real-world fraud accuracy result or evidence that Gemini beats a rules engine.

During live testing, the first resolution request returned schema-invalid output and stopped without executing. This exposed a gap beyond mocked-provider tests; bounded schema-error feedback and two regression tests were added. Live-run results below must distinguish that failed attempt from successful calls.

An ordinary invoice then exposed an invalid evidence-plan citation. The adapter now constrains each response schema to missing tools and observed source keys; the server still independently rejects invalid calls and permits at most one planning correction. Both invalid-output cases were stopped, not declared successful.

### Live partial-resolution result

Run `ops_238bdca6ecb14abdb634ed7c319c7f17` used `GEMINI_API / gemini-3.5-flash-lite`: two schema-parsed model responses, including one resolution-generation response. Its generated program passed exact verification and all six bounded guard challenges. The existing ₹3.6 lakh posting was reconciled (`ALREADY_POSTED`); the ₹96,000 deferral and ₹24,000 credit were recorded with a signed resolution journal. No second payment was created. The browser showed those actions and the remaining delivery obligation, not merely a reasoning report.

### Final live/browser checks

- Routine invoice: `ops_bb792c4b8a70468080d0e648403258af`, three schema-parsed Google responses including one resolution-generation response, `POSTED_SYNTHETIC`, ₹4.8 lakh. The generated program passed all six negative guard checks; the posting and journal were read back.
- Changed beneficiary: `ops_d16ec040511a4e23a8e691a464b1d46f`, one Google response, `HELD` after the enrolled-account lookup. No payment or resolution action executed. The UI gave the exact account-mismatch reason and independent-verification requirement.
- Browser navigation to `/payment-check` still loads the earlier signed refund/bill workflow. No new execution of that older browser flow was needed for this check; its regression suite and actual database bridge test ran above.
- No warnings or errors were captured in the preview tab's browser console during the final checks. The outcome view was visually checked at the attached narrow viewport. This is not a full accessibility or cross-browser audit.

Live validation used artificial business records only. Vertex AI, Document AI and cloud deployment were not activated; these calls used the already configured Gemini Developer API. The live attempts include failures documented above and are not a model-accuracy benchmark.

## Remaining work

- Real document ingestion, grounded extraction and authorised accounting connectors.
- Multiple line items, taxes, fees, FX, staged allocations and administered mandates.
- Richer evidence selection and unseen-case evaluation against deterministic baselines.
- Resumable investigations, external storage and cloud identity before hosted scaling.

The graph is a small typed graph, not a learned causal model. Conflict witnesses are rule-specific. Synthetic snapshots do not perform email outreach, ERP access or refunds. The operations ledger is separate from preflight and Anthos. AI advantage and patent novelty remain unproven.
