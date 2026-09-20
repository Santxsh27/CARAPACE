# Trust Receipts

A CARAPACE Trust Receipt is a customer-readable view of the exact assurance
that the deterministic verifier can prove for one payment execution. It is
created for both matching and mismatching runs and stored inside the same
tenant boundary as the underlying evidence.

## Assurance levels

The levels are cumulative and evidence-limited:

1. `PAYMENT_FIELDS_BOUND` — the submitted request matches the amount,
   recipient and payment identity that the customer confirmed.
2. `BANK_POSTING_MATCHED` — the observed bank posting also matches the
   promise, including the one-debit condition.
3. `SETTLEMENT_CONFIRMED` — the lifecycle reached `SETTLED` and an
   authoritative settlement reference is present.
4. `MISMATCH` — at least one deterministic verification rule failed.
5. `UNVERIFIED` — there is not enough matching evidence to make a stronger
   claim.

Bank of Anthos exposes a ledger posting, not an external payment-rail
settlement signal. Its correct demo run therefore stops honestly at
`BANK_POSTING_MATCHED`; settlement remains `PENDING`.

## Integrity boundary

The local implementation stores a SHA-256 digest over the contract identity,
execution evidence and full deterministic report. This makes the receipt
content-addressed and reproducible, but it is not yet a bank signature. A
production deployment should sign the receipt with a bank-controlled Cloud
KMS key and preserve key/version metadata.

The receipt adds no independent safety claim. Gemini cannot create a green
stage, change a failed check, or promote the assurance level.

## API

Every new verification-run response includes a `receipt` object. A stored
receipt can be fetched using the same tenant credentials:

```text
GET /v1/receipts/{receipt_id}
```

Receipts are isolated by tenant. Another tenant receives `404`, even if it
knows the receipt identifier.
