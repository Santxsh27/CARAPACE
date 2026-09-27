# Protection evidence — local incremental slice

The pre-payment gate now creates three kinds of bank-signed records:

1. `DECISION` records the bank order digest, amount, direction, payee, verdict, exact warning issued, reason codes, AI mode, and SHA-256 digests of customer-supplied text/image. It explicitly says `NOT_ACKNOWLEDGED` at decision time; a later signed choice is a separate record.
2. `DEVICE_ACKNOWLEDGEMENT` contains the exact statement and `PROCEED` or `CANCEL` choice signed with a locally enrolled browser P-256 key. It links to the original decision record. The bank-authenticated test enrollment is not production customer-identity proof.
3. `SYNTHETIC_POSTING` records the artificial-money transfer ID, amount, decision and `PROCEED` acknowledgement receipt. A held or cancelled payment never receives this record.

Each decision, browser choice and allowed synthetic transfer commits atomically with its evidence record in SQLite. If the witness history is corrupt, that attempted local write rolls back. A `HOLD` cannot be overridden even by a valid device signature; `ALLOW` and `WARN` require a valid `PROCEED` choice before posting. This is a local prototype guarantee for this SQLite store, not a guarantee about an outside payment rail.

The records are signed by the local bank development key. Their hashes become leaves in an [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162.html)-shaped, domain-separated SHA-256 Merkle tree. A distinct local witness key signs each tree head. `GET /v1/preflight/receipts/{receipt_id}` returns the record and inclusion path against the latest signed checkpoint. A verifier can call `carapace_core.protection_proof.verify_protection_bundle(bundle, bank_public_key=..., witness_public_key=...)` with keys pinned outside the bundle. Changing a warning, verdict, amount, inclusion path or checkpoint causes verification to fail.

`GET /v1/preflight/log/checkpoint?from_size=N` publishes only signed tree heads and an RFC 9162 consistency proof; it does not publish customer receipts. An independent client must retain its previous signed head, pin the witness public key through a separate trusted channel, and verify the proof before replacing its saved state. The included `carapace-witness-audit` CLI does this with `--url`, `--state-file` and `--witness-public-key-file` (the latter contains the base64 raw Ed25519 public key, not a private key). On first use it pins the current signed head; later runs request proof from that size and reject rollback, fork or bad signature without advancing the state. Run the monitor from a different operator/storage domain for real assurance; a local file beside the API is only a test.

Authenticated `GET /v1/preflight/audit` checks every observed transfer in the CARAPACE synthetic ledger against a signed bank order and decision, registered-device `PROCEED`, and signed/included decision, choice and posting records. It reports `PASS`, `FAIL` or `NO_POSTINGS` and named issue codes. It is a coverage check over **this controlled gateway/database only**, not proof about an outside payment rail.

This establishes **integrity and inclusion in a signed checkpoint**, and lets a monitor verify append-only growth from a head it previously retained. It does not prove:

- The customer actually saw, understood or freely accepted the warning. A browser signature establishes key control over bytes only.
- The locally enrolled test key belongs to a verified customer. Production enrollment must be tied to strong bank authentication and device lifecycle controls.
- Every payment at a real bank was logged. The current audit only sees CARAPACE synthetic transfers and records; a bank-owned, independent payment or settlement feed is required for wider coverage.
- The witness is independent. Both local keys are operated on the same development machine.
- A monitor that did not previously save a trusted head can detect a historic fork. A first bootstrap accepts a valid signature from the pinned key; multiple isolated monitors need checkpoint sharing/gossip to detect split views.
- A local database rollback cannot be hidden from everyone. The current key and checkpoint live with the same operator, so only separately retained trusted checkpoint history can expose a rollback or fork to that observer.
- A synthetic posting settled with a real recipient or rail.

Raw screenshots and customer messages are not stored in the protection record; their digests allow a holder to match a voluntarily disclosed original later. The authenticated receipt endpoint returns private payee and warning details only to the bank tenant. Public transparency surfaces should expose only hashes and proofs, not customer details.

Next: bank-authenticated production device enrollment, independently operated witness/monitor with checkpoint sharing, and reconciliation against every transfer in an authoritative bank-owned rail or settlement feed.
