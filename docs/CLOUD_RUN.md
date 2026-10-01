# Financial Friday on Google Cloud

## Current cloud boundary

The Google Cloud project, billing alerts and required APIs are configured. Vertex AI has been called successfully with Google identity. The repository can be built into the existing non-root Docker image and deployed to Cloud Run.

The initial Cloud Run service is deliberately private. It uses a dedicated runtime service account with only Vertex AI invocation permission. It uses Application Default Credentials supplied by Cloud Run; no Gemini API key is embedded in the image or repository.

Version 0.10.0 adds live text/QR/voice-transcript ingestion and saved mandates to
the local container. These records still use SQLite and therefore disappear when a
Cloud Run instance is replaced. Do not present the existing cloud revision as a
durable always-on assistant until Firestore/Cloud SQL and Cloud Tasks are connected.

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
