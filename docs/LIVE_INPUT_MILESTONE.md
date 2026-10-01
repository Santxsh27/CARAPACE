# Financial Friday live-input milestone

Version 0.10.0 removes the fixed-input limitation from the main demonstration.

## Demonstrated flow

1. Save a tenant-scoped instruction, protected balance and automatic sandbox limit.
2. Publish a new artificial bill through the enrolled test-provider endpoint.
3. Speak or paste an unfamiliar message, QR payload or bill text.
4. Use Gemini structured output to extract the bill reference, amount, claimed payee and unsafe embedded instructions.
5. Retrieve the independent provider record by reference.
6. Stop on amount, recipient, recurring, prompt-injection or reserve contradictions.
7. Otherwise create a dynamic typed financial program and either mark it READY or execute automatically inside saved authority.
8. Preserve idempotency, signed receipts and readback through the existing executor.

The local comparison parser is explicitly labelled and exists for offline tests.
The production demo must show configured Gemini provenance.

## Verification

- Financial Friday suite: 18 tests passed.
- Full isolated Docker suite: 137 tests passed, 1 optional Anthos integration test skipped.
- New coverage includes unfamiliar content grounding, changed-recipient refusal,
  automatic execution, balance reduction and repeated-input idempotency.

## Remaining boundary

The test provider and artificial account are controlled by this prototype. They
demonstrate the integration contract without claiming access to a real bank, biller,
SMS inbox or UPI rail. Browser speech recognition provides text input; Gemini Live
native audio remains a later connector. Cloud persistence and scheduling remain the
next deployment milestone.
