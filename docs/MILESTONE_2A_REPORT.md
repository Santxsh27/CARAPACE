# Milestone 2A report — signed local protection evidence

## Outcome

The existing pre-payment gate now produces a bank-signed `DECISION` record when it evaluates a payment. A held refund has a record of the exact warning issued, but no posting record. An allowed bill produces that decision record and, only after the local synthetic transfer succeeds, a separate bank-signed `SYNTHETIC_POSTING` record. The decision/write and transfer/write pairs are atomic in the local SQLite database.

A second local key signs a SHA-256 Merkle checkpoint after each record. The API can return an inclusion bundle against the latest checkpoint. A verifier supplied with previously pinned bank and witness public keys can check the signatures and inclusion without trusting public keys inside the bundle. The page displays the checkpoint after each test.

## Verification

```text
docker compose --profile test run --rm --build tests
Ran 68 tests in 1.563s
OK
```

The added tests cover both signatures, all inclusion indices across small uneven trees, wrong pinned keys, altered warning/proof, tenant isolation, proof retrieval against a later checkpoint, and rollback of a decision or allowed synthetic transfer when the latest witness signature is corrupt.

The local browser path was also exercised with the live Gemini Developer API: the generated refund case returned `HOLD` / `BLOCKED` and displayed checkpoint 1; the matching bill returned `ALLOW` / `POSTED_SYNTHETIC` and displayed checkpoint 3. These are artificial-money cases. A configured provider is not equated with a successful model call; the page reports whether the call completed.

## Exact claim boundary

This slice proves the integrity of a disclosed record and its inclusion in **one signed local checkpoint**. It does not prove that a customer saw or understood the warning, that every bank payment was logged, that checkpoints form one append-only history, or that the witness is operated by an independent party. It also does not connect to a real bank or Bank of Anthos's official transfer route. The two keys are separate but managed by the same local operator. The current tree recomputes its root from all leaves on append, so it is suitable for this small demo, not a scalable production log.

## Next build decision

Before claiming a complete Proof of Protection, add an explicit registered-device acknowledgement/choice record, external checkpoint monitoring with consistency proofs, and gateway-to-log reconciliation. Separately, create a labelled evaluation corpus and measure false holds, model latency and cost. Cloud deployment and any Vertex AI pilot require an authorised GCP project and billing/credits decision; the local Gemini Developer API path is already real.
