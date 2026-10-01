# Financial Friday

## A bounded AI operator for everyday financial tasks

**Delegate the goal. Gemini plans. The safety kernel proves. The executor acts once.**

Financial Friday is not a financial chatbot and it is not an AI with unrestricted bank access. It turns a user's limited financial instruction into a typed action program, independently verifies every financial effect, executes only allowlisted operations through an authorised provider, and reconciles the recorded result before declaring success.

The working slice now accepts a saved standing instruction plus a previously unseen message, QR text or voice transcript. Gemini extracts a typed financial request, Friday retrieves a separate enrolled test-provider record, and the deterministic kernel decides whether an artificial-money action is allowed. A verified task can execute automatically inside the saved limit; changed amounts, recipients, recurring requests, embedded instructions and protected-balance violations stop before execution.

The existing Python package names still use `carapace_*` to preserve compatibility while the product transitions from CARAPACE to Financial Friday.

## What works now

The local homepage has two working paths. The **live input path** saves a user's
instruction, publishes a new artificial bill into an enrolled test provider, and
accepts unfamiliar message, QR or voice-transcript content. It uses configured
Gemini structured extraction (or the visibly labelled local comparison), grounds
the extracted reference against the provider record, and can complete one
artificial-money action automatically when the user has enabled that permission.
The **proactive inbox path** remains an opt-in worker demonstration with durable
claims, bounded retries, tenant isolation and no payment authority.

The live flow is content-driven rather than a stored question/answer animation.
Users can change the reference, amount, payee and wording. The outcome changes
from READY or COMPLETED to ATTENTION when the content contradicts the provider.

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
- The Cloud Run container remains a bounded hackathon service. SQLite on its temporary filesystem is not production persistence; Firestore/Cloud SQL migration is a later milestone.
- The official Google Cloud CLI is installed and authenticated for the project. The current `0.10.0` Financial Friday image, including live message/QR/voice-transcript ingestion, was successfully built in Cloud Build and published to Artifact Registry. The existing Cloud Run API remains on its previous revision until the new private revision is deployed and authenticated health-checked.

## Next steps

1. Deploy the published `api:0.10.0` image as a no-traffic private Cloud Run revision; verify authenticated health, API version and Vertex mode; then move traffic.
2. Deploy the Friday web surface separately while keeping the API private.
3. Replace temporary SQLite state with Firestore or Cloud SQL, then add Cloud Tasks for durable background work.
4. Add authorised provider/account connectors and document uploads; do not claim real bank or SMS access without an approved integration.

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
POST /v1/friday/scenarios/{scenario_id}/run
GET  /v1/friday/runs/{run_id}
GET  /v1/friday/mandate
PUT  /v1/friday/mandate
POST /v1/friday/test-provider/bills
GET  /v1/friday/live-input
POST /v1/friday/live-input
POST /v1/friday/live-input/{event_id}/run
```

Choose `{"planner":"local"}` for the explicit deterministic comparison. With Vertex configured, `{"planner":"configured"}` uses live Gemini structured output.

Run every automated test:

```bash
docker compose run --rm --build \
  -e CARAPACE_TEST_ANTHOS_BRIDGE_ENABLED=false \
  api python -m unittest discover -s tests
```

Current isolated result: **136 tests passed, 1 optional Anthos integration test skipped**. The test command disables the development-only direct Anthos bridge so unit tests do not inherit a live integration setting.

## What is retained from CARAPACE

The repository still contains useful earlier foundations: signed payment envelopes, intent-versus-action checks, transaction evidence, tamper-evident witness logs, Bank of Anthos experiments, exact obligation resolution, counterfactual repair search and release passports. They are reusable modules, not separate claims that every feature is already one production product.

The new submission focus is Financial Friday's closed loop:

```text
understand → plan → prove → execute → reconcile → remember
```

## Honest limits

This prototype uses an enrolled test-provider API, retained regression fixtures and artificial money. Browser speech recognition supplies an optional transcript; Gemini Live native audio is not connected yet. It does not access GPay, phone SMS, a real bank account, UPI credentials, OTPs or production funds. A real launch requires authorised bank/biller connectors, durable managed storage, security review, regulated partner controls, customer support and formal compliance work. Financial Friday does not promise zero fraud, guaranteed savings, guaranteed reimbursement, investment returns, patentability or a hackathon prize.

See [SPEC.md](SPEC.md) for the product contract, trust model and roadmap, and [docs/CLOUD_RUN.md](docs/CLOUD_RUN.md) for the cloud deployment boundary.
