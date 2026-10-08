# Friday proposal-safety evaluation

Measured October 8, 2026. Reproduce with:

```bash
docker compose run --rm --no-deps api python -m carapace_core.friday_evaluation
```

This command emits JSON and exits nonzero if any decision differs from the
scenario label. CI runs it on Python 3.11 and 3.12 and preserves the JSON artifact.
It imports only the typed models and verifier: no executor, database, credentials,
provider connection or model call.

## Results

| Metric | Observed |
|---|---:|
| Generated proposal cases | 51 |
| Valid proposals allowed | 12 / 12 |
| Unsafe proposals rejected | 39 / 39 |
| Unsafe proposals allowed | 0 |
| Valid proposals incorrectly held | 0 |
| Payment effects / AI calls | 0 / 0 |

Corpus fingerprint:
`ef30edb5dd59961056895140a3cbda4559ea129172ac35ab7267990520ac8f0f`.
One local evaluation took 4.2821 ms; this is verifier-only measurement, not cloud,
AI or end-to-end latency. Do not use it as a customer performance promise.

Three amounts cover exact limits, larger limits, approved fees and unknown-outcome
reconciliation. Unsafe cases cover changed amounts, provider/payee substitution,
fabricated evidence, OTP disclosure, goal substitution, missing confirmation,
duplicate effects, unverified providers, premature retry, recurrence, unauthenticated
options and unapproved fees. Scenario definitions assign expected decisions without
asking the verifier for labels. A test corrupts a previously valid proposal and
confirms the report records a false hold and a changed corpus fingerprint.

## What the comparison means

The hypothetical no-checker ablation would accept the same 39 unsafe proposals.
No baseline payments were executed. This isolates the value of the independent
gate; it is **not** a live plain-Gemini comparison, an unseen-case benchmark, or
real-world fraud detection accuracy. The corpus is development-generated and
the system's authors know its cases.

## Remaining evidence needed

Run a separately labelled fresh-input corpus through actual Vertex Gemini using
the same inputs and tools. Record model/version, prompt version, invalid outputs,
task completion, false holds, unsafe proposed/allowed effects, token use and cost,
and end-to-end latency. Do not execute an unsafe baseline: simulate its proposed
effects offline. Include benign ambiguous inputs, source injection, changed
recipient, fees and provider downtime. Publish all failures, not only successes.
