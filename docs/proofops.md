# CARAPACE ProofOps and Counterfactual Safety Search

ProofOps starts only after the deterministic verifier has preserved a real
payment mismatch. It is not a chatbot and it does not edit a production bank.

## Difficult AI task

Gemini receives a minimised evidence bundle containing failed contract codes,
lifecycle states, debit counts and equality signals. Raw account identifiers
are excluded. With strict structured output, Gemini must:

1. identify a testable causal boundary;
2. cite the deterministic evidence codes that support it;
3. rank only predefined safe interventions;
4. create adversarial regression scenarios;
5. describe a patch strategy without authorising it.

The model cannot declare its own answer correct. CARAPACE runs **Counterfactual
Safety Search** over isolated copies of the failed evidence. It explores the
smallest combinations of these allowlisted interventions:

- `DEDUPLICATE_LOGICAL_DEBITS`
- `REUSE_CONTRACT_IDEMPOTENCY_KEY`
- `RESTORE_BOUND_PAYMENT_REQUEST`

Each candidate is sent through the same deterministic financial verifier used
for the original transaction. The result records how many experiments were
executed, the minimal intervention set and whether the counterfactual changed
`MISMATCH` to `MATCH`.

This is causal evidence for a repair direction, not proof that production code
is safe. Source changes, real refunds, ledger corrections and releases remain
human-controlled and require broader regression, security and performance
tests.

## Human release gate and Release Passport

Every ProofOps analysis is persisted before review. A tenant-authenticated
reviewer can approve or reject it exactly once. Approval is accepted only when
the counterfactual verifier reached `MATCH`; the model cannot approve its own
proposal.

An approval produces a Release Passport binding the incident, contract, run,
analysis, candidate commit/reference, minimal intervention, regression
scenarios and reviewer. The local build signs that canonical payload with
HMAC-SHA256 and verifies it when read. Any field change invalidates the
signature. A production deployment replaces only this signer with Cloud KMS.

## API

After a mismatch creates an evidence case:

```text
POST /v1/cases/{case_id}/analyze
POST /v1/cases/{case_id}/approve
GET  /v1/release-passports/{passport_id}
```

These endpoints are tenant-authenticated. The first returns provider
provenance, the bounded hypothesis, generated regression scenarios and the
independently verified counterfactual result. The second records the human
decision and conditionally issues the passport. The third recomputes and
returns the passport's `signature_valid` state.

## AI modes

- `local`: deterministic offline fixture for reproducible development.
- `gemini` or `ai_studio`: real Gemini Developer API through an AI Studio key.
- `vertex`: Gemini on Vertex AI using Google Cloud identity.

The local provider is never labelled as Gemini. Gemini failures return an
explicit unavailable response instead of silently switching modes.
