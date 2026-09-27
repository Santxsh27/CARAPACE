# Milestone 3A — exact-bound Anthos artificial-money test ledger

27 September 2026. This is a local integration experiment, not a production bank integration.

## What changed

- The current payment-intent page keeps `HOLD` before all postings and requires the existing signed `PROCEED` choice for a genuine bill.
- After CARAPACE's local synthetic posting succeeds, a test bridge checks the bank-signed posting receipt and its local witness inclusion proof, then inserts one direct test row into Bank of Anthos's append-only PostgreSQL `transactions` table.
- The bridge atomically stores the returned `transaction_id` alongside the CARAPACE transfer ID, order ID, decision ID, posting receipt ID and payment fields in a separate `carapace_test.preflight_bindings` table. The binding is explicit; the code never guesses from amount or timestamp.
- A repeat call with the same transfer and evidence reuses the original bound row. A reused transfer ID with different payment evidence is rejected. A readback compares the exact bound ledger row's payer, payee, amount and routing fields to the CARAPACE transfer.
- Direct sample-ledger writes require an explicit test-only opt-in and a local Bank of Anthos sample database name/host. This is a guardrail, not an authorization mechanism for production.
- The page shows `MATCH` only when that exact bound test row is read back and matches. If the PostgreSQL step fails after the CARAPACE synthetic posting has committed, it reports `UNAVAILABLE`, not an external match.

## Verification

The full Docker suite passed: **87 tests, one skipped by default**. The skipped case is the PostgreSQL integration test requiring the authorised local test database URL. Running that integration case against the existing Bank of Anthos Docker database passed: one artificial row was created, a repeat call returned the same transaction ID, and no second row was inserted for that transfer. A separate test confirms the opt-in and local-database restrictions.

The browser walkthrough was also exercised with live Gemini Developer API. The fake refund returned `HOLD`/`BLOCKED` with no posting. The genuine bill returned `ALLOW`, waited for browser-signed `PROCEED`, then showed `Confirmed; two test ledgers match` after Bank of Anthos test row **#121** matched the CARAPACE amount and account fields. On a prior attempt the Gemini request timed out, so the same bill correctly became `HOLD`/`BLOCKED` and did not post. This is an observed local run, not a measured detection or availability rate.

The Dockerfile now caches runtime dependency installation separately from CARAPACE source code. A clean rebuild passed the full suite, and a second build reused the dependency and application layers without downloading packages again.

## Limits that must remain visible

- This writes directly to the **sample database**, not through Bank of Anthos's official LedgerWriter/payment service. The official website is separate from this route.
- Both databases and the bridge still run under one local developer's control. The companion binding table is not a bank-independent source of truth.
- The CARAPACE SQLite transaction and Anthos PostgreSQL transaction are not atomic together. A partial failure must be shown as pending/unavailable and reconciled later; the current browser flow does not automatically repair that state.
- The upstream Anthos `transactions` table stores amount and accounts but **no currency or CARAPACE request ID**. The INR tag and exact request binding are maintained by the test-only companion table, not by upstream LedgerWriter.
- No real funds, payment rail, settlement, production identity, or bank-owned processor authorization is involved.

## Next work

Build a recoverable outbox and a bank-controlled request-to-ledger binding that survives service restarts, then wire the gate before an authorised LedgerWriter/payment path or equivalent processor. Add an outside-rail reconciliation feed, independent witness operation, and a labelled model-evaluation corpus before stronger claims.
