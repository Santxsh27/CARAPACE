# Financial Friday — core delivery 0.13.0

## Implemented

- Atomic Firestore artificial-payment journal: receipt, idempotency marker,
  balance update and completed run save in one transaction.
- Provider bill identity survives different messages about the same obligation.
- Cloud reads use Firestore authority, not stale instance-local caches.
- Commit-time checks for changed provider records, changed mandates, revoked
  automatic permission and protected balance.
- Updating a mandate does not reinitialize the account balance.
- Restored tasks can safely consult the durable payment journal before acting.
- Firestore mode requires an existing persistent bank signing key.
- SQLite fallback remains available, with equivalent provider/mandate guards
  and lookup of receipts created under the earlier message-level identity scheme.

## Verification boundary

Final Docker regression result: 151 tests ran; 150 passed and one optional
Anthos integration test was skipped. Local readiness and website proxy checks
returned version 0.13.0 and the configured Gemini model. Browser automation was
blocked by browser policy; no visual browser-verification claim is made.

The transaction tests use a strict in-memory driver running the real callback,
including a discarded attempt before commit. They cover restart, concurrent
requests, failed commit, repeated bill messages, provider changes, mandate
changes, revoked automation and reserve checks. They do not test Firestore's
network behavior or establish real-bank authorization.

## Required next, in order

1. Confirm Mumbai (`asia-south1`) for the default Firestore database.
2. Provision the database, runtime permissions and stable Secret Manager signer.
3. Validate live Firestore commit/restart/replay and a real Vertex planning run.
4. Update the private Cloud Run API, then deploy the customer website with
   authenticated server-side API access (do not expose tenant secrets).
5. Implement durable Cloud Tasks scheduling/reconciliation and run the labelled
   model-versus-guard evaluation. Prepare the submission video and evidence.

## Optional / after the core submission path

Native live voice, Agora, additional analytics services, broad UI redesigns,
extra scenarios and additional real-world connectors.

No production money, GPay, UPI authentication, SMS access or official banking
permissions are supplied by this implementation.
