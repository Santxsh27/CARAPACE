# Financial Friday 0.13.2 — cloud verification

Date: October 7, 2026. Scope: private, artificial-money sandbox only.

## Implemented

- Native Firestore in Mumbai, deletion protection enabled.
- Atomic payment receipt, idempotency, balance and run-outcome transaction.
- Stable Ed25519 bank/witness keys and tenant demo credentials in Secret Manager, pinned to version 1. No secret values in Git.
- Read-only AI understanding retries fail closed when exhausted.
- Receipt-first replay checks identity, amount, scope and signature before returning an existing result. Invalid receipts hold the task, never trigger replacement payments.
- Cloud verification tool keeps Google identity tokens and API credentials in process memory and retains TLS certificate verification.

## Automated tests

```text
Ran 159 tests in 6.187s
OK (skipped=1)
```

158 passed; one optional direct Anthos integration test skipped. Tests cover concurrent payment attempts, changed mandate/provider data, failed commits, restarted services, AI-offline replay and corrupted receipts. They do not establish live-bank readiness.

## Live evidence

1. Vertex AI with `gemini-3.5-flash` interpreted a generated bill and completed one artificial INR 2,479 payment on revision 0.13.1.
2. That revision's replay encountered repeated Vertex server errors and safely held without another debit.
3. Revision `financial-friday-api-v0132-durable1` restored the previous payment from Firestore: `ALREADY_COMPLETED`, zero successful model calls, no new debit, unchanged balance 4,752,100 paise, same signing key and operation ID.
4. A new 0.13.2 bill was understood by live Vertex, but planning again encountered server errors. The task held with `NO_VERIFIED_PROGRAM`; no money moved. This failed check is not counted as successful completion.
5. Revision `financial-friday-api-v0132-lite1` passed the complete new-bill check with `gemini-3.5-flash-lite`: one understanding attempt, automatic artificial payment, signed receipt, unchanged replay balance, zero AI calls on replay, recipient mismatch held, anonymous request blocked. New event: `evt-471704809d3b251b832dc760`; run: `ff_73310799d05d489084cc7952b9250b58`; operation: `ffpay_e850cb6ea2894def9c6279b5bc523e03`; resulting balance: 4,504,200 paise. These are artificial test identifiers, not credentials.

Flash-Lite is an explicit model configuration for this release, not a hidden fallback. The larger Flash model's failed checks remain recorded above. Real-world quality and latency require an unseen-case evaluation; one successful smoke test does not prove reliability across all bills.

## Build provenance

- Cloud Build: `34464b1f-92f3-4c0a-8272-76550c315207`, SUCCESS.
- Image digest: `sha256:44f27d11ba2f1309c0011bd1c993666bf680434234b1420f777d1ee09f11acee`.
- Build context excludes local secrets and the unrelated unfinished UI edit.
- Anonymous requests were blocked; Cloud Run IAM has no public invocation binding.

## Remaining release boundaries

The web interface still runs locally on port 8090; public cloud web hosting and user authentication are not finished. Cloud Tasks scheduling, independent provider integration, unseen-case evaluation and submission materials remain. No real bank accounts, UPI, GPay, SMS, OTPs or production money are connected. Budget alerts are not hard spending caps.
