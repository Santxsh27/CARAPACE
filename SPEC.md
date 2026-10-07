# Financial Friday — Product and Engineering Specification

Version 1.2 · 2 October 2026

## Product statement

Financial Friday is a bounded AI operator for everyday financial tasks. A person delegates an outcome and constraints; Gemini creates or repairs a typed plan; an independent deterministic kernel proves the plan stays within those constraints; a restricted provider adapter performs the allowed action; and reconciliation verifies what actually happened.

The product removes routine work without asking a person to trust a chatbot or give an LLM unrestricted financial authority.

## The one problem

Existing financial assistants can explain, classify or recommend. Existing payment systems can execute a precise instruction. The dangerous gap is between them: translating a human goal into reliable financial actions while preserving recipient, amount, fee, cadence, privacy and retry constraints.

Financial Friday closes that gap with **proof-carrying financial programs**: the AI proposal cannot execute until ordinary code independently validates its effects against the user's immutable goal and authoritative provider evidence.

## First complete journey

The user delegates:

> Pay this verified ₹1,999 electricity bill once, with no subscription or extra fee.

Financial Friday:

1. Resolves the enrolled biller and current obligation from an authorised connector.
2. Gives Gemini only the bounded goal, connector evidence and typed action vocabulary.
3. Receives a structured `FinancialProgram`, not prose or generated code.
4. Checks provider, payee, amount, fee, currency, cadence, data disclosure, evidence and prior operation state.
5. Feeds only safe validation error codes back for one repair attempt when the AI proposal is invalid.
6. Runs adversarial mutations against the same guard.
7. Executes through a provider sandbox with the original idempotency identity.
8. Reads back or reconciles the provider outcome.
9. Returns a signed receipt that says exactly what was proven and what remains outside scope.

## Live unfamiliar-input journey

The user saves a standing instruction containing a protected balance, an automatic
payment ceiling and whether verified artificial-money tasks may execute without a
second click. A test provider then publishes a fresh bill with a new reference,
amount and recipient. The user speaks or pastes a message that Friday has not seen.

Gemini extracts a typed interpretation from the untrusted content. That extraction
does not authenticate anything. Friday uses the extracted reference to retrieve the
separate provider record, compares amount and recipient, applies the standing
instruction and creates a dynamic financial program. A matching bill can execute
inside the saved sandbox authority. A changed amount, recipient, recurring request,
embedded instruction or protected-balance violation produces ATTENTION with no
payment. Repeating the same input resolves to the same event and payment identity.

## Demonstration cases

### Genuine bill

A verified one-time obligation matches the goal. One artificial-money operation is created. Repeating the run returns the existing signed receipt rather than creating another payment.

### Misleading subscription offer

The provider highlights a cheaper recurring offer but also exposes an authenticated one-time option. Gemini selects the one-time route and the safety kernel verifies that choice. If only recurring options exist, no AI proposal can make the task executable without new customer authority.

### Recipient swap

The connector's recipient differs from the approved recipient. The kernel emits `EVIDENCE_PAYEE_MISMATCH`. AI explanation has no authority to override it.

### Unknown network outcome

An earlier provider call timed out after submission. The only valid plan is `RECONCILE_EXISTING → CONFIRM_RESULT`. If the provider reports success, Financial Friday completes without issuing a retry.

## Technical layers

### 1. Immutable goal contract

The goal binds the task ID, instruction, enrolled provider, recipient, currency, total ceiling, fee ceiling, one-time cadence, allowed data fields and idempotency identity.

### 2. Authoritative evidence

Evidence comes from enrolled server-side connectors. Model text is never promoted to an authoritative amount, recipient, provider status or payment result.

### 3. Gemini planner

Gemini on Vertex AI maps the goal and evidence to a schema-constrained action program. It may explain the plan and repair a rejected candidate using fixed error codes. It has no executor or arbitrary tools.

### 4. Deterministic safety kernel

Pure code verifies the program and derives the authorised total. The model cannot change this verdict. The kernel fails closed on missing, contradictory or unknown evidence.

### 5. Adversarial challenge stage

Before execution, deterministic mutations test whether the same guard rejects an extra unit, changed recipient, excess data field, recurring mandate, duplicate financial action and missing confirmation.

### 6. Restricted executor

Only fixed verbs can reach the provider adapter. The current adapter uses SQLite and artificial money, signs the result, enforces tenant-scoped uniqueness and verifies the stored receipt.

### 7. Reconciliation

An unknown external result is not equivalent to failure. Financial Friday checks the original operation before retrying. This is essential because a local rollback cannot undo a provider-side payment.

## Trust rules

- Gemini proposes; deterministic code authorises.
- No generated Python, JavaScript, SQL, shell command, URL or provider tool is executed.
- No PIN, OTP, CVV, password or signing key enters the model context.
- Authoritative evidence and user constraints remain separate from untrusted text.
- Model failure never silently falls back while claiming a live AI result.
- Unknown outcomes reconcile before retry.
- Every money-moving operation is idempotent and tenant scoped.
- A signed receipt proves bytes and checks, not universal financial safety.
- Unsupported or unavailable evidence is shown as held/unverified, never green.

## Google Cloud architecture

```text
Web / future voice client
          │
          ▼
Cloud Run API and orchestrator
          │
          ├── Vertex AI Gemini: structured planning and repair
          ├── Safety kernel: deterministic financial verification
          ├── Provider adapters: allowlisted operations only
          ├── Firestore: atomic artificial-payment journal, state and evidence
          ├── Cloud Tasks: future resumable execution and reconciliation
          ├── Secret Manager + IAM: future connector credentials and keys
          └── Cloud Logging: operational evidence without payment secrets
```

The first deployment uses a Cloud Run service identity with `roles/aiplatform.user`; it does not use a Gemini API key. Version 0.13.0 implements tenant-scoped Firestore state and atomically commits artificial-money balance, receipt, bill-level payment identity, idempotency marker and run outcome. Restored tasks consult the same authoritative journal. Commit-time checks revalidate provider records, mandate instructions, automatic permission and protected balance. Local development retains its SQLite transaction and guards.

Local mode is `SQLITE_LOCAL`; cloud mode is labelled `FIRESTORE_TRANSACTIONAL`. The default database is provisioned in Mumbai, with runtime permissions and persistent signing keys in Secret Manager. In-memory callback tests do not replace live Firestore restart/replay verification. The API exposes the active boundary at `GET /v1/friday/storage-status`, and the product surface displays the storage mode. Version 0.13.2 validates existing signed receipts before requesting an AI plan, so completed bills remain confirmable during an AI outage.

Google ADK should be introduced when there are multiple durable agent stages requiring orchestration. It must not replace the safety kernel. Document AI should be added only when real consented bill/document ingestion is implemented. BigQuery/Vertex model evaluation should be added when there is a sufficiently large labelled evaluation set. Products are selected for real responsibilities, not logo count.

## Security algorithm

The differentiating mechanism is the combination of:

1. Immutable financial goal contract.
2. Schema-constrained AI action program.
3. Independent effect verification.
4. Mutation-based pre-execution challenge.
5. Restricted capability executor.
6. Idempotent external operation identity.
7. Reconciliation-before-retry.
8. Signed outcome evidence.

The project may describe this as a **Constraint-Carrying Financial Program** pattern. Novelty and patentability remain hypotheses requiring a professional prior-art search; they are not current claims.

## Evaluation

Report measured results rather than promises:

- Valid-task completion rate.
- Unsafe-program rejection rate.
- False-hold rate.
- Duplicate-effect rate under concurrent/repeated requests.
- Unknown-outcome reconciliation accuracy.
- Gemini schema-valid response rate and repair success rate.
- Cost and latency per completed task.
- Data minimisation violations blocked.
- Difference between deterministic and Gemini planning on unseen scenarios.

## Build status

Implemented:

- Typed goal, evidence, action and program schemas.
- Vertex-compatible Gemini planner and explicit local baseline.
- Independent safety kernel.
- Six mutation challenges.
- One bounded repair loop.
- Artificial-money executor, tenant isolation and idempotency.
- Reconciliation-before-retry case.
- Signed receipts and readback.
- API endpoints and automated tests.
- Persistent tenant-scoped standing instructions and artificial account balance.
- Dynamic enrolled test-provider bills rather than only predefined scenarios.
- Gemini structured interpretation of new message, QR and voice-transcript content.
- Automatic artificial-money completion inside saved limits.
- Recipient, amount, recurring-request, embedded-instruction and reserve protection.
- Browser voice capture feeding the same live-input API.
- Ephemeral Gemini document understanding for PNG, JPEG, WebP and PDF bills with exact source quotations and no raw-file persistence.
- Google Cloud project, enabled services, budget alerts and live Vertex smoke test.
- Opt-in tenant-scoped Firestore transactions for artificial payments, balances, receipts, idempotency and run outcomes, with commit-time provider and mandate checks.
- Restored tasks use the cloud journal before creating any payment effect; persistent signing keys are required in Firestore mode.
- Bounded read-only understanding retries for transient provider failures; exhausted understanding fails closed with no submitted payment. Attempt and model provenance are retained.

Next:

1. Arrange approved judge access and confirm dashboard rules. The owner-only IAP web surface and new-bill browser journey now work; see docs/FRIDAY_BROWSER_VERIFICATION_1008.md. The API remains private and tenant credentials stay server-side.
2. Verify live document uploads and a second independently enrolled cloud identity; finish the unseen-case evaluation and submission artifacts.
3. Replace the same-operator test provider with an independently authenticated sandbox connector.
4. Add durable Cloud Tasks orchestration and recovery.
5. Replace browser transcription with Gemini Live API native audio using the same tools.
6. Build an unseen-case evaluation, then prepare the video, deck and threat model.

## Product boundaries

The prototype is not a bank, UPI application, investment adviser or autonomous controller of real accounts. Production actions require authorised provider partnerships and their authentication/approval rules. Human review remains mandatory for ambiguous, high-impact or regulated actions. Financial Friday automates routine work inside explicit authority; it does not ask users to surrender control of all finances.
