# Financial Friday on Google Cloud

## Current cloud boundary

The Google Cloud project, billing alerts and required APIs are configured. Vertex AI has been called successfully with Google identity. The repository can be built into the existing non-root Docker image and deployed to Cloud Run.

The Cloud Run service is deliberately private. Its dedicated runtime service account has Vertex invocation, project-scoped Firestore data access and access to the three named demo secrets. It uses Application Default Credentials supplied by Cloud Run; no Gemini API key is embedded in the image or repository.

Version 0.13.2 with the document-evidence gate serves 100% normal traffic on `financial-friday-api-doc1008`. The document fix and live verification are recorded in `FRIDAY_DOCUMENT_VERIFICATION_1008.md`. A live
cross-revision check restored a payment created by 0.13.1 from Firestore, verified
the persistent signing key, retained its original operation ID and unchanged
balance, and returned ALREADY_COMPLETED without calling AI or creating a debit.
Fresh-bill live Vertex execution, replay, recipient holds and anonymous-access rejection passed; details are in `CLOUD_RELEASE_0132_VERIFIED.md`.
The owner-protected IAP website also completed a fresh ₹2,487 bill and displayed its stored receipt. The prompt revision corrects a false hold on ordinary customer wording without relaxing the kernel. Current browser evidence and UI fixes are in `FRIDAY_BROWSER_VERIFICATION_1008.md`.
Firestore persists Friday state, but Cloud Tasks scheduling is not yet connected:
do not describe this as a continuously running cloud assistant.

## Demo configuration

```text
CARAPACE_ENV=development
CARAPACE_DB_PATH=/tmp/financial-friday/financial-friday.db
CARAPACE_AI_PROVIDER=vertex
GOOGLE_CLOUD_LOCATION=global
CARAPACE_GEMINI_MODEL=gemini-3.5-flash-lite
CARAPACE_FRIDAY_DURABLE_STORE=firestore
CARAPACE_FIRESTORE_DATABASE=(default)
CARAPACE_BANK_SIGNING_KEY_PATH=/var/secrets/bank/key.pem
CARAPACE_WITNESS_SIGNING_KEY_PATH=/var/secrets/witness/key.pem
```

`development` enables the enrolled test-provider routes. This cloud revision uses persistent Ed25519 keys mounted from Secret Manager version 1, not auto-generated temporary keys. It is a private artificial-money demo, not a production release. A production deployment needs provider authentication, user-aware access controls and a non-development configuration.

## Cost controls

The configured billing budget sends warnings; Google Cloud budgets do not automatically stop resources. Keep Cloud Run minimum instances at zero, set a small maximum instance count, use request timeouts and review the billing dashboard during development.

## Required production upgrades

- Extend durable storage to any newly added workflows; Friday payment state already uses Firestore.
- Store future provider connector secrets in Secret Manager; signing and demo tenant credentials already use it.
- Use Cloud KMS or another bank-approved signer.
- Make authentication user/provider aware instead of the local tenant API key.
- Use Cloud Tasks for durable work and reconciliation.
- Add audit retention, regional/data residency review and incident controls.
- Perform a threat model and independent security review.

## Durable sandbox activation

The code now supports `CARAPACE_FRIDAY_DURABLE_STORE=firestore`. Payments remain
artificial money. Receipt, bill-level payment identity, idempotency, balance and
run outcome commit atomically. Reads use cloud authority rather than local caches.
An enrolled provider change or mandate change at commit time can hold the task.

Provisioned on October 7, 2026:

1. Mumbai (`asia-south1`) default Firestore database, native mode, deletion protection.
2. Runtime identity with Firestore data permissions scoped to this project.
3. Stable bank and witness signing keys plus private tenant credentials in Secret Manager, pinned to version 1. Secret values are never stored in Git.
4. Private zero-traffic candidate and authenticated live verification tool: `tools/verify_cloud_friday.py`.
5. Cross-revision recovery and the new-bill test passed, followed by promotion. Unit transaction tests alone are not a substitute for these live checks.

Cloud Tasks, consumer onboarding/judge enrollment and real provider OAuth connectors remain
separate work. Do not call the current local poller a durable cloud scheduler.
