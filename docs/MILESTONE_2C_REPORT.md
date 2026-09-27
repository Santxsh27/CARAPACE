# Milestone 2C — retained checkpoint verification and local posting audit

26 September 2026. This is an incremental security slice, not a production-bank deployment.

## What changed

- Added RFC 9162-style consistency proof generation and verification to the existing domain-separated Merkle tree. Tests exercise every pair of tree sizes through 33 leaves and reject altered roots and shortened proofs.
- Added public, hash-only `GET /v1/preflight/log/checkpoint?from_size=N`. The API validates both signed heads against its local leaves and returns the proof that the newer head extends the requested older size. Customer receipts, account numbers and messages are not on this endpoint.
- Added `carapace-witness-audit`, a separate client that uses an independently pinned public key and a retained state file. It verifies the next head and proof before atomically replacing that file. It rejects rollback, a conflicting prior head, invalid signature and forged proof.
- Added authenticated, read-only `GET /v1/preflight/audit`. It checks each **observed CARAPACE synthetic transfer** against the signed bank order and decision, registered-device `PROCEED` statement, and bank-signed decision, choice and posting receipts with witness inclusion proofs. `NO_POSTINGS` is distinct from `PASS`; missing or altered evidence is `FAIL`.

## Verification

The full Docker regression suite passed: **83 tests**, including new consistency, fork/rollback, retained-state, checkpoint endpoint, malformed witness, and synthetic posting coverage cases. The rebuilt API returned a healthy readiness response and a live signed checkpoint. The local browser page at `http://localhost:8090/` loaded with its two interactive test cases and no visible error page.

The persisted local development database currently has **five older synthetic transfers without the new complete evidence chain**. The live audit therefore returned `FAIL` with five issue entries. This is expected for records created before the newer evidence protocol; it is not legitimate to relabel them `PASS` or delete them to improve the demo. Tests with a new clean database show a fully signed transfer returns `PASS`, and deleting its posting receipt or altering its amount returns `FAIL`.

## Trust limits

- The local bank and witness keys are distinct but still controlled by the same operator. The monitor is runnable separately; **it has not been deployed under an independent operator**.
- A first checkpoint is only as trustworthy as the separately pinned public key and the operator's initial trust decision. A later proof detects a fork or rollback only relative to a checkpoint the monitor retained. Isolated monitors need checkpoint sharing/gossip to detect different views.
- The local audit observes only transfers and evidence in CARAPACE's controlled synthetic database. It cannot detect payments outside this gate, or prove that a transfer and every related record were never jointly deleted from the same operator's database. Authoritative bank-rail/settlement reconciliation is still required.
- The current Merkle implementation recomputes roots and proofs from all local leaves. It is adequate for a small hackathon demonstration, not a production-scale log.
- Browser-device enrollment is still a development mechanism; its key signature does not prove customer identity, sight or comprehension.

## Next milestone

Connect a bank-owned artificial-money payment path or independent event feed to the gate and reconcile those events against the logged decisions and choices. In parallel, run the witness monitor in a distinct trust domain with pinned keys and shared checkpoints, then add a measured labelled scam/benign evaluation set. Do not present these as implemented until demonstrated.
