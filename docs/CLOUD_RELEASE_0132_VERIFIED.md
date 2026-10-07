# Financial Friday — verified cloud release, October 7, 2026

## Actual deployment

Private API version 0.13.2 now serves 100% traffic on Cloud Run revision
`financial-friday-api-v0132-lite1` in Mumbai (`asia-south1`).
Model: Vertex AI `gemini-3.5-flash-lite`.
Storage: `FIRESTORE_TRANSACTIONAL`, default Mumbai database with deletion protection.
Signing and demo tenant credentials: Secret Manager, version 1, runtime-only access.
No public invocation IAM binding. No real bank or payment credentials.

## Verification results

- 159 automated tests ran: 158 passed, one optional Anthos integration skipped.
- A newly generated arbitrary bill was understood by live Vertex in one attempt and automatically paid with artificial funds.
- A signed receipt was saved; resulting artificial balance was 4,504,200 paise.
- Replaying that bill returned ALREADY_COMPLETED with zero successful AI calls and no new debit.
- Changed recipient was held; anonymous request was blocked.
- Before model configuration changed, revision 0.13.2 restored a payment from revision 0.13.1: unchanged balance, original operation and signing key, no new debit and no AI call.
- Larger `gemini-3.5-flash` planning requests repeatedly returned server errors and safely held payments. Flash-Lite was explicitly selected and independently tested, not silently used as a fallback.

Cloud Build `34464b1f-92f3-4c0a-8272-76550c315207`: SUCCESS.
Image digest: `sha256:44f27d11ba2f1309c0011bd1c993666bf680434234b1420f777d1ee09f11acee`.
Live bill event: `evt-471704809d3b251b832dc760`.
Run: `ff_73310799d05d489084cc7952b9250b58`.
These are artificial test identifiers, not credentials.

## Local services

Docker API on localhost:8080 and Friday website on localhost:8090 were verified healthy. The Anthos ledger was also healthy. Browser appearance was not rechecked in this release.

## Remaining priority work

1. Public cloud web surface with user-aware authentication and server-side API credentials.
2. Durable Cloud Tasks scheduling; the local background poller is not a cloud scheduler.
3. Independent authenticated sandbox provider connector.
4. Unseen-case comparison, false-hold rate, latency and AI cost measurements.
5. Submission video, architecture, limits and dashboard deadline confirmation.

Native Gemini Live voice and extra analytics services remain optional. No real GPay, UPI, SMS, OTP or bank access is claimed. One successful cloud smoke test is not a guarantee of universal reliability or production readiness.

## Repository handoff

Core changes are committed locally as `ae749ac` and `b51bfec`. Documentation updates remain to be committed and pushed. During final saving, iCloud marked repository files and `.git/HEAD` dataless; reads timed out and `brctl download` could not resolve those files. Do not overwrite the repository or its unrelated unfinished UI change to work around this. Download/keep the Desktop CARAPACE folder locally in Finder, then resume documentation commit and GitHub push.
