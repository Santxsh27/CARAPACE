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

## Milestone 2 — Gemini context interpreter (next)

- Structured input/output schemas.
- Prompt-injection boundary and redaction.
- `SEND` versus `RECEIVE_EXPECTED` contradiction detection.
- Evidence spans, confidence, and explicit uncertainty.
- No autonomous payment decision.

## Milestone 3 — Consumer Lens and bank SDK demo

- Firebase web application.
- User-initiated message, QR, link, invoice, and screenshot check.
- Bank-controlled confirmation screen.
- PAC creation and integrity verification.
- Honest coverage levels in the UI.

## Milestone 4 — Ledger Witness

- Bank of Anthos adapter.
- Controlled payment and retry execution.
- Ledger snapshot and event reconciliation.
- Trust Receipt and mismatch case.

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
