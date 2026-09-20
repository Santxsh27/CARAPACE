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

## API

After a mismatch creates an evidence case:

```text
POST /v1/cases/{case_id}/analyze
```

The endpoint is tenant-authenticated and returns provider provenance, the
bounded hypothesis, generated regression scenarios and the independently
verified counterfactual result.

## AI modes

- `local`: deterministic offline fixture for reproducible development.
- `gemini` or `ai_studio`: real Gemini Developer API through an AI Studio key.
- `vertex`: Gemini on Vertex AI using Google Cloud identity.

The local provider is never labelled as Gemini. Gemini failures return an
explicit unavailable response instead of silently switching modes.
