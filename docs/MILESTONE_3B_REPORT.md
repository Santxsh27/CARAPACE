# Milestone 3B — recoverable artificial-money test delivery

27 September 2026. This remains a local development integration, not a production payment rail.

## What now works

When the CARAPACE gate commits a permitted synthetic posting, it commits a `PENDING` delivery item in the **same SQLite transaction** as the transfer and signed posting evidence. If that outbox insert fails, the posting and evidence roll back together. A `HOLD` decision never creates a posting or delivery item.

An opt-in worker in the development API polls due items every five seconds. It retrieves the saved posting receipt and its current inclusion proof, verifies the signed evidence, and calls the test-only Anthos bridge with the original transfer ID. The bridge inserts or reuses the exact bound PostgreSQL row. Only a matching readback can mark the local delivery item `MATCH`; failures remain pending with bounded retry delay. If PostgreSQL commits but SQLite does not record the match, replay uses the same transfer ID and reuses the original row.

The authenticated delivery-status API re-reads a recorded match from Anthos before displaying `MATCH`; a missing or changed row becomes `MISMATCH` or `UNAVAILABLE`. The local customer page can show `Confirmed locally; Anthos test check pending`, then update to `Recovered; two test ledgers match` if the worker succeeds while that page remains open.

## Verification

- The full Docker suite passed **90 tests**, with one optional PostgreSQL test skipped by default. The optional exact-bound row/readback test passed against the local Anthos test database.
- Unit tests cover outbox atomic rollback, bank-tenant isolation, unavailable bridge, restart/replay, idempotent match recording, and refusing to display a stale match when readback disagrees.
- In a live browser run with Gemini Developer API, a genuine bill passed the gate and matched artificial-money Anthos row **#123**.
- For a controlled outage run, the Anthos test database was stopped. Two live Gemini attempts timed out and correctly failed closed before payment. To isolate delivery recovery, the API was temporarily switched to its labelled `LOCAL_RULES` fallback. A confirmed synthetic bill then stayed `UNAVAILABLE`/pending. After Anthos restarted, the background worker delivered the saved item and the page changed to `Recovered`, exact row **#124**. Live Gemini mode was restored and verified afterward.

These are observed local runs, not fraud-detection or availability metrics.

## Trust boundaries and remaining work

- The bridge still writes directly to the **Bank of Anthos sample PostgreSQL table**, not through its official LedgerWriter/payment API. This is artificial money only.
- CARAPACE SQLite and Anthos PostgreSQL cannot commit atomically together. The outbox makes the second step retryable and idempotent in this local setup; it is not a distributed transaction or settlement guarantee.
- Both signers, API, worker and databases remain under one development operator. They do not demonstrate independent bank operation or a bank-owned event feed.
- Only new postings are queued; older synthetic transfers created before this migration are not backfilled. Persistent failures need production-grade alerting, dead-letter handling and operator review. The page polls for at most one minute; a later recovery is still visible through the authenticated status endpoint.
- The actual next integration milestone is a bank-controlled request-to-ledger reference and an authorised processor route, with no direct sample-table insert.
