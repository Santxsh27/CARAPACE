# Incremental build roadmap

## Milestone 0 — Trust core (complete)

- PAC and execution-evidence schemas.
- Canonical request hashing.
- Lifecycle transition validation.
- Deterministic financial invariant engine.
- Passing and duplicate-debit examples.
- Unit tests and CLI.

Exit condition: a valid payment passes, a duplicate debit fails, and the result
is reproducible without an AI model.

## Milestone 1 — API and evidence store (complete)

- Cloud Run-compatible control-plane API.
- Contract and run persistence.
- Authentication and tenant boundaries.
- Evidence-case creation.
- Generated OpenAPI documentation.

Exit condition: two tenants cannot read one another's records, invalid
contracts are rejected before storage, every submitted run receives the exact
deterministic verdict, and every mismatch opens a durable evidence case.

## Milestone 2 — Gemini context interpreter (in progress)

- Structured input/output schemas. **Complete for text intent.**
- Prompt-injection boundary and strict model output. **Complete; redaction next.**
- `SEND` versus `RECEIVE_EXPECTED` contradiction detection. **Complete.**
- Vertex AI provider plus honest no-cost local mode. **Complete; live cloud call pending credentials.**
- Evidence spans, evaluation dataset, confidence calibration and explicit uncertainty. **Remaining.**
- No autonomous payment decision. **Enforced by deterministic reconciliation.**

## Milestone 3 — Consumer Lens and bank SDK demo

- Beginner-facing Lens workflow in the existing Control Room. **Complete for text + decoded UPI URI.**
- Firebase web application. **Remaining.**
- User-initiated QR image import. **Complete in supported Chromium browsers.**
- Link, invoice, screenshot understanding and camera capture. **Remaining.**
- Bank-controlled confirmation screen.
- PAC creation and integrity verification.
- Honest coverage levels in the UI.

## Milestone 4 — Ledger Witness

- Bank of Anthos ledger adapter. **Complete for the official local ledger slice.**
- Controlled payment and retry execution. **Complete with artificial money.**
- Exact transaction-ID binding and ledger-row reconciliation. **Complete.**
- Beginner-facing live integration page. **Complete.**
- Deterministic, stored staged Trust Receipt. **Complete; Cloud KMS signing remains.**
- Full LedgerWriter/Kubernetes path. **Remaining.**

## Milestone 5 — ProofOps

- Change-impact extraction.
- Risk-guided adversarial scenarios.
- Counterexample minimization.
- Gemini cause, patch, and regression proposals.
- Independent rerun, human approval, and Release Passport.

## Milestone 6 — Hackathon hardening

- Seeded mutation benchmark.
- Security and privacy review.
- Cost and latency instrumentation.
- Cloud deployment.
- Three-minute end-to-end demonstration.
