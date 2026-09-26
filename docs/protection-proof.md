# Protection evidence — local incremental slice

The pre-payment gate now creates three kinds of bank-signed records:

1. `DECISION` records the bank order digest, amount, direction, payee, verdict, exact warning issued, reason codes, AI mode, and SHA-256 digests of customer-supplied text/image. It explicitly says `NOT_ACKNOWLEDGED` at decision time; a later signed choice is a separate record.
2. `DEVICE_ACKNOWLEDGEMENT` contains the exact statement and `PROCEED` or `CANCEL` choice signed with a locally enrolled browser P-256 key. It links to the original decision record. The bank-authenticated test enrollment is not production customer-identity proof.
3. `SYNTHETIC_POSTING` records the artificial-money transfer ID, amount, decision and `PROCEED` acknowledgement receipt. A held or cancelled payment never receives this record.

Each decision, browser choice and allowed synthetic transfer commits atomically with its evidence record in SQLite. If the witness history is corrupt, that attempted local write rolls back. A `HOLD` cannot be overridden even by a valid device signature; `ALLOW` and `WARN` require a valid `PROCEED` choice before posting. This is a local prototype guarantee for this SQLite store, not a guarantee about an outside payment rail.

The records are signed by the local bank development key. Their hashes become leaves in an [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162.html)-shaped, domain-separated SHA-256 Merkle tree. A distinct local witness key signs each tree head. `GET /v1/preflight/receipts/{receipt_id}` returns the record and inclusion path against the latest signed checkpoint. A verifier can call `carapace_core.protection_proof.verify_protection_bundle(bundle, bank_public_key=..., witness_public_key=...)` with keys pinned outside the bundle. Changing a warning, verdict, amount, inclusion path or checkpoint causes verification to fail.

This establishes **integrity and inclusion in one signed checkpoint**. It does not prove:

- The customer actually saw, understood or freely accepted the warning. A browser signature establishes key control over bytes only.
- The locally enrolled test key belongs to a verified customer. Production enrollment must be tied to strong bank authentication and device lifecycle controls.
- Every payment was logged. That needs coverage checks against a bank-owned payment gateway and ledger.
- The witness is independent. Both local keys are operated on the same development machine.
- Checkpoint N is an append-only extension of checkpoint N−1. A consistency proof and an externally monitored checkpoint history are still required.
- A local database rollback cannot be hidden. The current key and checkpoint live with the same operator, so an external auditor must retain trusted checkpoint history to detect a rollback or fork.
- A synthetic posting settled with a real recipient or rail.

Raw screenshots and customer messages are not stored in the protection record; their digests allow a holder to match a voluntarily disclosed original later. The authenticated receipt endpoint returns private payee and warning details only to the bank tenant. Public transparency surfaces should expose only hashes and proofs, not customer details.

Next: bank-authenticated production device enrollment, independent witness deployment and key pinning, Merkle consistency proofs, and reconciliation of every authorised transfer to a decision record.
