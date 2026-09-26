# Milestone 2B report — signed test-device choice

## What changed

The payment page now pauses a genuine bill after Gemini and the deterministic gate return `ALLOW`. The browser generates a temporary P-256 key and can sign `PROCEED` or `CANCEL` over a canonical statement containing the exact bank-controlled amount, direction, payee, order digest and nonce, the preflight decision, and the exact warning shown. The private key stays in the browser. The local server sends only the public key to a bank-authenticated **development** enrollment endpoint.

The API independently reconstructs that statement, verifies the browser signature and immutable enrolled key, then atomically adds a bank-signed `DEVICE_ACKNOWLEDGEMENT` record to the local witness tree. The synthetic gateway rechecks the choice, signatures and signed record before posting. `HOLD` cannot be overridden; `CANCEL` never posts; both `ALLOW` and `WARN` need a signed `PROCEED`. Replays and silent device-key replacement are rejected.

## Verification

```text
docker compose --profile test run --rm --build tests
Ran 75 tests in 2.500s
OK
```

The added tests include missing choice, forged device signature, altered amount in a signed statement, HOLD override, signed CANCEL, immutable development enrollment, tampered acknowledgement record, and rollback when the witness is corrupt. Existing refund, bill, tenant-isolation and protection-proof tests still pass.

The browser check used the local CARAPACE page with live Gemini Developer API: the genuine bill paused at `AWAITING_BROWSER_CONFIRMATION`; after browser signing `PROCEED` it returned `POSTED_SYNTHETIC` with a local witness checkpoint. Another bill signed `CANCEL` and returned `CANCELLED_NO_POSTING` with a choice receipt. The refund still returned `HOLD` / `BLOCKED` without a transfer. These are generated test scenarios and artificial money only.

## What this does not prove

- A human saw, understood or freely accepted the statement. The signature proves control of a browser key over bytes.
- The test key belongs to a production-verified bank customer. Enrollment currently uses a local bank development API key, not real customer authentication, WebAuthn or a bank device lifecycle.
- The separate Bank of Anthos site or any real bank/UPI rail is intercepted. The signed gate still controls only the CARAPACE synthetic ledger.
- The local witness is independently operated, every bank payment is logged, or checkpoints are externally monitored for consistency.

Next: production-grade device enrollment and identity binding, externally monitored witness checkpoints with consistency proofs, gateway-to-log coverage reconciliation, measured evaluation cases, then authorised cloud deployment.
