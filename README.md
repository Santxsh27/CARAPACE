# Financial Friday

## A bounded AI operator for everyday financial tasks

**Delegate the goal. Gemini plans. The safety kernel proves. The executor acts once.**

Financial Friday is not a financial chatbot and it is not an AI with unrestricted bank access. It turns a user's limited financial instruction into a typed action program, independently verifies every financial effect, executes only allowlisted operations through an authorised provider, and reconciles the recorded result before declaring success.

The first working slice handles a familiar task: **“Pay this verified ₹1,999 electricity bill once, with no subscription or extra fee.”** Gemini can plan the steps and correct a rejected plan, but it cannot change the recipient, raise the amount, add a fee, create a recurring mandate, disclose extra data, retry an uncertain payment, or call an arbitrary tool. Those boundaries are enforced by deterministic code.

The existing Python package names still use `carapace_*` to preserve compatibility while the product transitions from CARAPACE to Financial Friday.

## What works now

The local homepage includes an opt-in proactive sandbox inbox. Enable monitoring,
then deliver a sample bill to emulate an enrolled provider event. A server worker
checks it using the configured planner, validates the plan independently, and
records READY, ATTENTION or UNAVAILABLE. It runs while the local API is running,
even with the browser closed. Intake is tenant-scoped and deduplicated; it never
executes a payment. Due reminders are shown in the inbox, not sent by email or push.
Real inbox access, PDF/OCR extraction, and Cloud Run background scheduling are
not implemented by this increment. Interrupted checks are reclaimed after a
three-minute lease expires. Claim tokens prevent stale workers overwriting newer
results. Failed checks can be retried explicitly, up to three total attempts per
sample bill. Pausing stops new claims; a check already in flight may finish.
Lease recovery may repeat a model call, but inbox checks never execute payments.

Four end-to-end artificial-money cases are exposed through the API:

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

The sandbox is the first Jarvis-style product surface. Choose a controlled financial
situation, then ask Friday to handle the fixed goal. The screen renders the real
typed program returned by Gemini (or the explicitly labelled local comparison),
the deterministic safety result, adversarial mutation checks, restricted executor
events and signed artificial-money receipt. It is not a scripted animation and it
does not imply access to a real account.

Use the local development headers documented in [docs/api.md](docs/api.md). The new routes are:

```text
GET  /v1/friday/scenarios
POST /v1/friday/scenarios/{scenario_id}/run
GET  /v1/friday/runs/{run_id}
```

Choose `{"planner":"local"}` for the explicit deterministic comparison. With Vertex configured, `{"planner":"configured"}` uses live Gemini structured output.

Run every automated test:

```bash
docker compose --profile test run --rm --build tests
```

Current verified result: **128 tests passed, 1 optional Anthos integration test skipped**.

## What is retained from CARAPACE

The repository still contains useful earlier foundations: signed payment envelopes, intent-versus-action checks, transaction evidence, tamper-evident witness logs, Bank of Anthos experiments, exact obligation resolution, counterfactual repair search and release passports. They are reusable modules, not separate claims that every feature is already one production product.

The new submission focus is Financial Friday's closed loop:

```text
understand → plan → prove → execute → reconcile → remember
```

## Honest limits

This prototype uses fixtures and artificial money. It does not access GPay, a real bank account, UPI credentials, OTPs or production funds. A real launch requires authorised bank/biller connectors, durable managed storage, security review, regulated partner controls, customer support and formal compliance work. Financial Friday does not promise zero fraud, guaranteed savings, guaranteed reimbursement, investment returns, patentability or a hackathon prize.

See [SPEC.md](SPEC.md) for the product contract, trust model and roadmap, and [docs/CLOUD_RUN.md](docs/CLOUD_RUN.md) for the cloud deployment boundary.
