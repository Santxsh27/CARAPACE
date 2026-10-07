# Financial Friday on Google Cloud

## Current cloud boundary

The Google Cloud project, billing alerts and required APIs are configured. Vertex AI has been called successfully with Google identity. The repository can be built into the existing non-root Docker image and deployed to Cloud Run.

The initial Cloud Run service is deliberately private. It uses a dedicated runtime service account with only Vertex AI invocation permission. It uses Application Default Credentials supplied by Cloud Run; no Gemini API key is embedded in the image or repository.

Private revision `financial-friday-api-00005-w8k` serves version 0.10.1 at 100%
traffic after authenticated health, Vertex configuration, live Gemini planning,
pre-AI identity rejection and reconciliation checks. Transient Vertex server
errors receive a bounded retry and still fail closed. Records still use SQLite and
therefore disappear when a Cloud Run instance is replaced. Do not present the
current service as a durable always-on assistant until Firestore/Cloud SQL and
Cloud Tasks are connected.

## Demo configuration

```text
CARAPACE_ENV=development
CARAPACE_DB_PATH=/tmp/financial-friday/financial-friday.db
CARAPACE_AI_PROVIDER=vertex
GOOGLE_CLOUD_LOCATION=global
CARAPACE_GEMINI_MODEL=gemini-3.5-flash
```

`development` currently enables the fixture routes and creates short-lived signing keys on the container's temporary filesystem. This is acceptable for a private bounded demo, not a production release. A production deployment must use managed persistent state, protected signing keys and a non-development configuration.

## Cost controls

The configured billing budget sends warnings; Google Cloud budgets do not automatically stop resources. Keep Cloud Run minimum instances at zero, set a small maximum instance count, use request timeouts and review the billing dashboard during development.

## Required production upgrades

- Migrate run, idempotency and receipt state to Firestore or Cloud SQL.
- Store connector secrets in Secret Manager.
- Use Cloud KMS or another bank-approved signer.
- Make authentication user/provider aware instead of the local tenant API key.
- Use Cloud Tasks for durable work and reconciliation.
- Add audit retention, regional/data residency review and incident controls.
- Perform a threat model and independent security review.

## Version 0.13.0 activation gates

The code now supports `CARAPACE_FRIDAY_DURABLE_STORE=firestore`. Payments remain
artificial money. Receipt, bill-level payment identity, idempotency, balance and
run outcome commit atomically. Reads use cloud authority rather than local caches.
An enrolled provider change or mandate change at commit time can hold the task.

Before activation:

1. Confirm database location (existing Cloud Run is Mumbai, `asia-south1`).
2. Create the default Firestore database and grant the runtime identity the
   required Firestore data permissions, scoped to this project.
3. Provision a stable Ed25519 key in Secret Manager and mount it read-only.
   Set `CARAPACE_BANK_SIGNING_KEY_PATH` to the mounted file. Firestore mode
   refuses ephemeral auto-generated bank signing keys.
4. Deploy a private revision and use authenticated requests to test a genuine
   new bill, duplicate attempt, recipient mismatch, restart, and receipt verification.
5. Only promote after live checks pass. Unit tests use a strict in-memory
   transaction driver; they are not a substitute for the Firestore checks.

Cloud Tasks, public web deployment and real provider OAuth connectors remain
separate work. Do not call the current local poller a durable cloud scheduler.
