# Financial Friday

Start with [START_HERE.md](START_HERE.md) for the plain-language tour, demo steps, technology list and remaining submission work. The [household bill journey](docs/CUSTOMER_JOURNEY.md) explains the customer value, three new artificial examples and next build priorities.

## A bounded AI operator for everyday financial tasks

Friday's broader product is **Understand → Handle → Protect → Resolve**, sharing
one permission-controlled engine rather than unrelated financial mini-apps.
**My money** now gives a read-only snapshot of recorded artificial bills, available
funds above the reserve, potential bill commitments and shortfalls. Signed matching
internal payment receipts are distinguished from unresolved records; none of this
establishes external settlement or permits spending. Bill payments remain the first
working execution adapter, not the whole product vision.

A new bill-resolution kernel checks separately shaped bank and biller evidence,
freshness, exact identity bindings and reconciliation permission. It never approves
repayment or a refund. **The kernel is tested; external bank/biller connectors and
end-to-end correction are not connected.** Statements, investments and universal
bank control are not implemented. Transaction alerts and unknown requests now stop
before a payment case is constructed.

**Delegate the goal. Gemini plans. The safety kernel proves. The executor acts once.**

Financial Friday is not a financial chatbot and it is not an AI with unrestricted bank access. It turns a user's limited financial instruction into a typed action program, independently verifies every financial effect, executes only allowlisted operations through an authorised provider, and reconciles the recorded result before declaring success.

The working slice now accepts a saved standing instruction plus a previously unseen message, QR text, voice transcript, bill image or PDF. Gemini extracts a typed financial request and proposed source quotations, Friday retrieves a separate enrolled test-provider record, and the deterministic kernel decides whether an artificial-money action is allowed. Text quotations are checked against the original input and unsupported quotations discarded; document quotations are model-produced, not independently OCR-verified. A verified task can execute automatically inside the saved limit; changed amounts, recipients, recurring requests, embedded instructions, unusual bill increases above a saved review threshold and protected-balance violations stop before execution. The bill-increase comparison uses a previous amount supplied by the artificial test provider, not a real utility history.

The existing Python package names still use `carapace_*` to preserve compatibility while the product transitions from CARAPACE to Financial Friday.

## What works now

The app now has separate screens: **Friday home, My money, Bills, Documents, Activity,
Safety lab and My rules**, plus a dedicated **Run** screen. Home shows an animated
assistant core and four clear task choices, not a previous payment or a developer
console. Every run uses the existing API; screen animations do not manufacture
successful checks. Home also lists upcoming artificial provider bills for read-only
review; selecting a bill prepares a request without submitting a payment. Browser
Back, keyboard focus, phone layouts and reduced-motion
preferences are supported. Activity reopens recorded evidence with a read-only
request; it never repeats a payment. Pointer-driven 3D card tilt, coloured task
surfaces, gentle button lift and active-stage shimmer provide visual feedback.
Green means confirmed, rose/red means held, amber means verification needed and
cyan means working; labels always accompany colours. The Motion toggle remembers
only a local display preference and respects the OS reduced-motion setting.
These effects do not create new financial permissions or simulate success.
The Jarvis-inspired command centre pairs the assistant core with a time-aware
greeting, one direct bill request and a read-only briefing from the most recent ten
recorded runs. Activity has text search and Confirmed/Held/Review filters. Native
dialog help explains the permission boundary; `/` focuses the command outside
text fields and `?` opens help. Help, filters, journal reads and keyboard shortcuts
do not submit a payment.
Submitting the home request starts the live task; saved automatic permission can
complete a permitted artificial payment. This is disclosed next to the request.
The dedicated outcome summary explains what happened, why and the next step.
Repeated developer metrics stay inside the evidence disclosure, and saved-receipt
loading never shows a previous task's outcome as the new result.
See [the latest UI flow check](docs/submission/UI_VERIFICATION_1009.md) and [earlier UI verification](docs/FRIDAY_MULTISCREEN_1008.md).

The **live input path** saves a user's
instruction, publishes a new artificial bill into an enrolled test provider, and
accepts unfamiliar message, QR or voice-transcript content. It uses configured
Gemini structured extraction (or the visibly labelled local comparison), grounds
the extracted reference against the provider record, and can complete one
artificial-money action automatically when the user has enabled that permission.
The **proactive inbox path** remains an opt-in worker demonstration with durable
claims, bounded retries, tenant isolation and no payment authority.

The live flow is content-driven rather than a stored question/answer animation.
Users can change the reference, amount, payee and wording or upload a new PNG,
JPEG, WebP or PDF bill. Documents are capped at 8 MB, checked against their file
signature and processed ephemerally: Friday persists the SHA-256 digest, typed
facts and proposed evidence quotations, but not the raw file. The outcome changes
from READY or COMPLETED to ATTENTION when the content contradicts the provider.

The dedicated Run screen exposes the same backend truth as a five-stage assurance
journey: **understand → ground evidence → plan with AI → prove safety → act or
recover**. Each stage changes from waiting to active, completed, skipped or
blocked using the returned run events—not a decorative timer. A plain-language
Friday briefing shows the result, AI-call count, deterministic-gate decision and
number of artificial-money effects. The full program, hostile-mutation checks,
events and receipt remain available underneath for judges and engineers.

The primary experience is a Jarvis-inspired FRIDAY command surface: choose a task,
provide the details once, then follow its outcome on a separate screen. Saved
permission has its own My rules page; controlled scenarios live in Safety lab.
Technical evidence stays collapsed beneath the outcome. The task indicator shows
working, confirmed completion or attention based on actual API results, while
the home core returns to READY when no task is running.

Five retained end-to-end artificial-money cases are exposed through the API:

| Scenario | Result |
|---|---|
| Genuine bill | A typed program is verified, challenged, executed once, signed and read back. |
| Misleading subscription offer | Gemini ignores the highlighted recurring discount and selects the authenticated one-time option. |
| Recurring-only provider | No available option preserves the one-time goal, so execution is held. |
| Recipient changed | Authoritative evidence does not match the approved payee, so no model can override the hold. |
| Network timeout | The prior operation is reconciled before retry; a successful existing payment produces no duplicate. |

The safety kernel checks:

- Goal, provider, recipient and currency binding.
- Exact principal, fee and total ceilings in integer minor units.
- One-time versus recurring cadence.
- Minimum data disclosure.
- Evidence provenance.
- Exact action order and no repeated financial effect.
- Reconciliation before retry when an earlier result is unknown.
- Tenant isolation, idempotency, signed receipts and read-after-write verification.

It also mutates an approved program in six hostile ways—extra amount, changed payee, excess data request, recurring mandate, repeated payment, and missing result confirmation—and proves that the independent guard rejects every mutation.

## Core architecture

```text
User's bounded financial goal
             │
             ▼
Gemini on Vertex AI ── proposes a typed FinancialProgram
             │
             ▼
Deterministic Safety Kernel
recipient · amount · fees · cadence · data · evidence · retry state
             │
       ┌─────┴─────┐
       │           │
      HOLD       VERIFIED
                   │
                   ▼
Restricted Provider Executor
                   │
                   ▼
Reconciliation + signed artificial-money receipt
```

Gemini has no payment credentials or generic network, code, SQL, shell, or URL tool. The executor accepts only a schema-validated, independently approved program. A model failure stops the live path; it never silently pretends that local rules were Gemini.

## Google Cloud status

- A dedicated **Financial Friday** Google Cloud project is configured.
- Billing is protected by a ₹1,000 monthly alert budget at 25%, 50%, 90% and 100%. Alerts are warnings, not a hard spending cap.
- Vertex AI, Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Firestore and Cloud Tasks APIs are enabled.
- A real Vertex AI call to `gemini-3.5-flash` succeeded. No API key was created; Vertex uses Google identity and the Cloud Run service identity.
- Version `0.13.2` implements `FIRESTORE_TRANSACTIONAL` state: one transaction stores the artificial payment receipt, idempotency marker, balance change and run outcome. Local development remains `SQLITE_LOCAL` by default. Already-paid bills are reconciled from verified receipts before any AI call; malformed receipts fail closed.
- Bill identity, rather than message identity, prevents two messages about one bill from creating two payments. At commit time, the cloud executor rechecks provider details, current mandate, automatic permission and protected balance. Updating a mandate never resets the artificial account balance.
- Transaction callback contract tests cover restart recovery, concurrent attempts, repeated bill messages, changed provider details, corrupt receipts, AI-offline replay and commit failures. Cloud integration checks are recorded separately in `docs/CLOUD_RUN.md`; neither establishes production banking readiness.
- The default Firestore database is now provisioned in Mumbai (`asia-south1`), with deletion protection. Payment and witness signing keys plus private demo API credentials are provisioned in Secret Manager; secret values are never committed.
- The official Google Cloud CLI is installed and authenticated. Private Cloud Run revision `financial-friday-api-ready1008` serves version `0.13.2` at 100% normal traffic with `gemini-3.5-flash-lite` on Vertex AI. It includes the document gate, targeted message prompt repair, privacy-safe diagnostics and text quotation validation. Fresh artificial payments and cross-revision receipt-first replay have been verified without repeat debits. See [current release and handoff](docs/submission/FINAL_HANDOFF_1009.md), [message release history](docs/submission/MESSAGE_PROMPT_REPAIR_1008.md), [original API evidence](docs/CLOUD_RELEASE_0132_VERIFIED.md) and [browser verification](docs/FRIDAY_BROWSER_VERIFICATION_1008.md).
- The protected [cloud website](https://financial-friday-web-171681243260.asia-south1.run.app/) now works with real owner Google sign-in through IAP. A new ₹2,487 bill completed through browser → live Vertex AI → transactional Firestore → signed receipt; replay created no additional debit, and a changed recipient was held. The API is still private and backend keys never enter the browser. Owner-only access is not yet judge enrollment. See [browser verification and limits](docs/FRIDAY_BROWSER_VERIFICATION_1008.md).

## Next steps

1. Arrange explicitly authorized judge access and confirm dashboard deadline/eligibility; record the live journey using [the demo script](docs/submission/DEMO_SCRIPT.md).
2. Expand unseen message/document/image checks and explicitly enroll a second identity; the targeted false-hold repair and owner PDF-to-payment journey are verified.
3. Add Cloud Tasks for durable claims, bounded retries and reconciliation.
4. Add authorised provider/account connectors; do not claim real bank or SMS access without an approved integration.
5. Run the labelled adversarial evaluation set and publish accuracy, false-hold, latency and per-run cost measurements.

## Run locally

Docker Desktop is recommended:

```bash
docker compose --profile anthos up --build
```

Open:

- API documentation: [http://localhost:8080/docs](http://localhost:8080/docs)
- Financial Friday sandbox: [http://localhost:8090](http://localhost:8090)
- Earlier operations lab: [http://localhost:8090/operations](http://localhost:8090/operations)
- Earlier payment-check demo: [http://localhost:8090/payment-check](http://localhost:8090/payment-check)

The sandbox is the first Jarvis-style product surface. Save a standing instruction,
publish a fresh artificial provider bill, then speak or paste a new request. The screen renders the real
typed program returned by Gemini (or the explicitly labelled local comparison),
the deterministic safety result, adversarial mutation checks, restricted executor
events and signed artificial-money receipt. It is not a scripted animation and it
does not imply access to a real account.

Use the local development headers documented in [docs/api.md](docs/api.md). The new routes are:

```text
GET  /v1/friday/scenarios
GET  /v1/friday/storage-status
POST /v1/friday/scenarios/{scenario_id}/run
GET  /v1/friday/runs/{run_id}
GET  /v1/friday/mandate
PUT  /v1/friday/mandate
POST /v1/friday/test-provider/bills
GET  /v1/friday/live-input
POST /v1/friday/live-input
POST /v1/friday/live-input/{event_id}/run
POST /v1/friday/documents?filename={name}
```

Choose `{"planner":"local"}` for the explicit deterministic comparison. With Vertex configured, `{"planner":"configured"}` uses live Gemini structured output.

Run every automated test:

```bash
docker compose --profile test run --rm --no-deps --build \
  -e CARAPACE_AI_PROVIDER=local \
  -e CARAPACE_TEST_ANTHOS_BRIDGE_ENABLED=false \
  tests
```

Local workspace increment **0.14.0**: **235 tests run, 234 passed, one optional Anthos integration test skipped** in the native suite, including JavaScript parsing/renderer checks. The Docker test image lacks Node and skips browser-script tests; those passed in the native suite. The previous deployed 0.13.2 release ran 195 tests plus eleven tooling tests. New coverage includes exact workspace totals, receipt binding, tenant isolation, non-payment alerts and the bill-resolution kernel. The workspace was checked through the local browser and API. **This increment has not been deployed or live-Gemini evaluated; Cloud Run still runs the earlier release.** These regressions are not broad fraud-accuracy or product-impact measurements.

Live PDF verification now includes a matching bill stopped at the saved automatic
limit and a recipient mismatch stopped before payment, through Vertex AI and the
signed-in cloud website. The document gate refuses missing critical quotations.
An additional fresh INR 49 PDF completed one artificial payment: Gemini corrected
a real rejected first plan, the server verified the signed receipt, and replay
reused it without another debit or model call. Five separate offline verification
tooling checks protect the explicit INR 50 test cap and existing permission.
See [the document verification report](docs/FRIDAY_DOCUMENT_VERIFICATION_1008.md)
for the initial failure, fix, live evidence and scope limits.

The no-payment [proposal evaluation](docs/submission/SAFETY_EVALUATION.md) checks
51 generated cases: 12 valid proposals allowed, 39 unsafe proposals rejected,
zero false holds. Run `python -m carapace_core.friday_evaluation`; CI preserves
the JSON evidence. This isolates the gate, not live Gemini or real fraud accuracy.
See [security and launch boundaries](docs/submission/SECURITY_BOUNDARIES.md).

Two fresh [live Vertex message batches](docs/submission/LIVE_MESSAGE_EVALUATION_1008.md)
returned 14/16 expected outcomes: ten problematic requests were held, but one
normal request had HTTP 503 and another was falsely held. No payments occurred.
This small component check is not broad fraud accuracy. The subsequent
[prompt repair](docs/submission/MESSAGE_PROMPT_REPAIR_1008.md) passed 24 live
extraction and eight private API checks without weakening the gate. The earlier
503 remains undiagnosed; sanitized diagnostics now help investigate future failures.
The broader follow-up checked 16 fresh message variants on the private candidate:
16/16 expected outcomes, exact financial extraction and retained text quotations
passed; the balance was unchanged. Sample API median 2.240 seconds and maximum
7.824 seconds are not a p95 or general latency promise. Cost was not measured.
An earlier 16-case pass exposed two invented quotations; the subsequent filter
fix and both limitations are retained in the final handoff report.
The evaluator and nine offline tooling tests are included in CI.

## What is retained from CARAPACE

The repository still contains useful earlier foundations: signed payment envelopes, intent-versus-action checks, transaction evidence, tamper-evident witness logs, Bank of Anthos experiments, exact obligation resolution, counterfactual repair search and release passports. They are reusable modules, not separate claims that every feature is already one production product.

The new submission focus is Financial Friday's closed loop:

```text
understand → plan → prove → execute → reconcile → remember
```

## Honest limits

This prototype uses an enrolled test-provider API, retained regression fixtures and artificial money. Browser speech recognition supplies an optional transcript; Gemini Live native audio is not connected yet. The atomic Firestore journal and persistent signing keys are provisioned; cloud release checks are documented separately. Public user authentication and durable cloud scheduling remain unfinished. It does not access GPay, phone SMS, a real bank account, UPI credentials, OTPs or production funds. A real launch requires authorised bank/biller connectors, security review, regulated partner controls, customer support and formal compliance work. Financial Friday does not promise zero fraud, guaranteed savings, guaranteed reimbursement, investment returns, patentability or a hackathon prize.

See [SPEC.md](SPEC.md) for the product contract, trust model and roadmap, and [docs/CLOUD_RUN.md](docs/CLOUD_RUN.md) for the cloud deployment boundary.

## Local follow-through increment (October 10)

The **My money** page now offers “Match recorded payment”. Supply a bill reference;
the authenticated API re-reads the tenant's enrolled bill and signed artificial
payment receipt in one SQLite transaction, verifies their exact binding, and
records a signed local acknowledgement once. Concurrent retries cannot create
another acknowledgement. Missing or conflicting evidence remains unverified or held.
This does not debit money, amend a real utility bill, or prove external settlement.
Firestore/Cloud Run execution is deliberately disabled until a transactional
connector is implemented; no local fallback is used in cloud mode.

Verification for this local increment: native suite **244 tests: 243 passed,
one optional integration skip**; isolated Docker suite **244 tests: 237 passed,
seven environment-dependent skips**. Browser-to-API verification confirmed that
a bill without a matching recorded payment stays unverified. Successful,
concurrent, tampered-evidence and cross-tenant cases are covered in automated tests.
