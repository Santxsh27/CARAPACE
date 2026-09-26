# CARAPACE

## Payment Intent Firewall & Proof of Protection

**Know what a payment will actually do. Stop a dangerous mismatch. Keep fair evidence of the warning.**

CARAPACE is a bank-integration product for authorised-push-payment scam prevention. Before a transfer, it compares the story that persuaded a customer to pay—a message, bill, QR or screenshot—with the amount, direction and recipient supplied by the bank's payment gateway. Gemini interprets the untrusted story; deterministic rules decide whether the bank's gateway may proceed. The local gate now signs a protection record and adds it to a separately keyed local witness tree; independent operation and customer acknowledgement are still future work.

This repository is being repositioned from earlier financial-assurance experiments. **Milestone 1 now has a working local pre-payment gate**, but it is not a completed bank deployment. All current accounts and money are synthetic. CARAPACE has no access to live banks, UPI funds or customer accounts.

## The product in one example

A screenshot promises a ₹4,999 refund, but the bank-controlled payment order says **SEND ₹4,999**. Gemini extracts the refund claim with its source text. Code detects `RECEIVE_EXPECTED` versus `SEND`, returns `HOLD`, and the integrated test gateway refuses to submit the transfer. A genuine bill whose amount and recipient match the bank order can proceed. The gate now signs a record of the warning and decision and includes it in a locally witnessed log; customer acknowledgement and independently operated witnessing are still future work.

```text
Customer-shared context ──→ Gemini extracts supported claims ──┐
                                                              ├─→ deterministic comparison → ALLOW / WARN / HOLD
Bank-signed payment envelope ──→ trusted amount and payee ─────┘                              │
                                                                                              ↓
                                                                               bank-controlled test transfer
                                                                                              ↓
                                                                            signed receipt and witness evidence
```

CARAPACE does not itself move real funds. A bank must integrate its own gateway and honour `HOLD`; a standalone checker can only provide advice. Future registered-device signatures could prove a key acknowledged bytes, not that a human read or understood them. See [SPEC.md](SPEC.md) for the exact trust boundaries and build milestones.

## What exists today and what is next

| Area | Current state |
|---|---|
| Context analysis | Existing Lens parses user-supplied text and UPI request fields. Gemini Developer API and Vertex AI adapters exist, with an honestly labelled local fallback. |
| Bank test environment | The Bank of Anthos PostgreSQL test ledger and CARAPACE demo run locally with artificial data. Its optional full banking website is a separate sample and is **not** the current in-path payment gate. |
| Deterministic verification | Existing contract, receipt and test modules remain in the repository as reusable engineering foundations. |
| Milestone 1 | Ed25519-signed bank payment order, signed decision, server-side `HOLD` gate, one-time synthetic transfer, screenshot-capable Gemini adapter, and two interactive cases are implemented. A successful live Google call is reported separately from provider configuration. |
| Evidence slice | The gate atomically issues bank-signed decision and posting records. A second local key signs Merkle tree heads, and an inclusion bundle can be verified with externally pinned public keys. This is not yet an independently operated witness or proof the person saw the warning. |
| Later milestones | Registered-device acknowledgement, independent witness operation and consistency auditing, dispute workbench, and human-approved rule learning. |

Earlier research modules are retained while the new payment path is built; they are not the product's homepage or judging story. No feature is described as live merely because an adapter or mock exists.

## Run locally

Docker Desktop is recommended. Start the reliable Milestone 1 path first:

```bash
docker compose --profile anthos up --build
```

Open [CARAPACE's local page](http://localhost:8090) and the [API documentation](http://localhost:8080/docs). On the CARAPACE page, run **Fake refund** and **Genuine bill**. Each creates a new signed order, sends a generated test screenshot and transcribed fixture text to Gemini or the visibly labelled local fallback, then tries the server-side payment gate. The first must be blocked; the second posts one row to the **CARAPACE local synthetic ledger**. That gate is not yet wired to Bank of Anthos's official transfer service.

The optional full sample bank can be started with `docker compose --profile anthos-full up --build` and opened at [localhost:8081](http://localhost:8081) using `testuser` / `bankofanthos`. Its x86 Java services can be slow or unavailable on an Apple Silicon Docker host; if the balance-reader is unhealthy, use the CARAPACE path above and do not count the separate bank website as a Milestone 1 integration result.

Run the automated suite with:

```bash
docker compose --profile test run --rm --build tests
```

The local AI provider is deliberately labelled `LOCAL_RULES`. To use live Gemini, configure an untracked `.env` from [.env.example](.env.example); never commit an API key. `/v1/ai/status` reports the configured provider. A configured provider alone is not proof that a successful live model call has occurred.

The bank API requires the tenant headers already documented in [docs/api.md](docs/api.md). The new sequence is `POST /v1/preflight/orders` → `POST /v1/preflight/orders/{id}/evaluate` → `POST /v1/preflight/orders/{id}/submit`. The browser page calls those through its local server so no bank API key is exposed to JavaScript. `GET /v1/preflight/transfers` shows the artificial-money effects; protection bundles are described in [docs/protection-proof.md](docs/protection-proof.md). These are development credentials and must be replaced before any hosted pilot.

## Hackathon submission target

CARAPACE targets **BFSI: Intelligent Risk, Fraud & Financial Experiences** at Google Cloud AI Builder Cup 2026. The submission must show a working Google-AI-powered prototype deployed on Google Cloud, plus a public repository, short video and deck. The published prototype deadline is **18 October 2026**; the team should confirm its binding deadline on the Hack2skill dashboard.

The prototype uses synthetic financial data and clearly labelled integration limits. A real bank pilot would require the bank's consent, secure identity and key management, independent witness operation, privacy/security review, and production payment-gateway integration. CARAPACE does not promise zero fraud, automatic reimbursement, a legal finding or patentability.

## Documentation

- [Product specification and milestone plan](SPEC.md)
- [Step-by-step build plan](docs/BUILD_PLAN.md)
- [Milestone 1 implementation report](docs/MILESTONE_1_REPORT.md)
- [Milestone 2A protection-proof report](docs/MILESTONE_2A_REPORT.md)
- [Protection-proof guarantees and limits](docs/protection-proof.md)
- [Milestone 1 implementation decisions](docs/DECISIONS.md)
- [Existing Bank of Anthos integration boundary](docs/bank-of-anthos.md)
- [Existing API reference](docs/api.md)
- [Security policy](SECURITY.md)
