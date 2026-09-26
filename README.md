# CARAPACE

## Payment Intent Firewall & Proof of Protection

**Know what a payment will actually do. Stop a dangerous mismatch. Keep fair evidence of the warning.**

CARAPACE is a bank-integration product for authorised-push-payment scam prevention. Before a transfer, it compares the story that persuaded a customer to pay—a message, bill, QR or screenshot—with the amount, direction and recipient supplied by the bank's payment gateway. Gemini interprets the untrusted story; deterministic rules decide whether the bank's gateway may proceed. The local gate signs a decision record; a temporary browser key signs an explicit test-device choice; and both enter a separately keyed local witness tree. Independent witness operation and production customer identity are future work.

This repository is being repositioned from earlier financial-assurance experiments. **Milestone 1 now has a working local pre-payment gate**, but it is not a completed bank deployment. All current accounts and money are synthetic. CARAPACE has no access to live banks, UPI funds or customer accounts.

## The product in one example

A screenshot promises a ₹4,999 refund, but the bank-controlled payment order says **SEND ₹4,999**. Gemini extracts the refund claim with its source text. Code detects `RECEIVE_EXPECTED` versus `SEND`, returns `HOLD`, and the test gateway refuses to submit the transfer. A genuine bill pauses for an explicit browser-signed `PROCEED` choice before one artificial-money transfer is posted. The exact warning, test-device choice and posting have separate signed records in the local witness log.

```text
Customer-shared context ──→ Gemini extracts supported claims ──┐
                                                              ├─→ deterministic comparison → ALLOW / WARN / HOLD
Bank-signed payment envelope ──→ trusted amount and payee ─────┘                              │
                                                                                              ↓
                                                                          browser-signed choice → test transfer
                                                                                              ↓
                                                                            signed receipt and witness evidence
```

CARAPACE does not itself move real funds. A bank must integrate its own gateway and honour `HOLD`; a standalone checker can only provide advice. The local browser signature proves a test key signed specified bytes, not that a human read or understood them. See [SPEC.md](SPEC.md) for the exact trust boundaries and build milestones.

## What exists today and what is next

| Area | Current state |
|---|---|
| Context analysis | Existing Lens parses user-supplied text and UPI request fields. Gemini Developer API and Vertex AI adapters exist, with an honestly labelled local fallback. |
| Bank test environment | The Bank of Anthos PostgreSQL test ledger and CARAPACE demo run locally with artificial data. Its optional full banking website is a separate sample and is **not** the current in-path payment gate. |
| Deterministic verification | Existing contract, receipt and test modules remain in the repository as reusable engineering foundations. |
| Milestone 1 | Ed25519-signed bank payment order, signed decision, server-side `HOLD` gate, one-time synthetic transfer, screenshot-capable Gemini adapter, and two interactive cases are implemented. A successful live Google call is reported separately from provider configuration. |
| Evidence slices | The gate atomically issues bank-signed decision, browser-choice and posting records. A temporary P-256 browser key signs the exact test statement; a second local key signs Merkle tree heads. A test posting requires a verified `PROCEED` choice. This does not prove human comprehension or production customer identity. |
| Later milestones | Authenticated device enrollment, independent witness operation and consistency auditing, coverage reconciliation, dispute workbench, and human-approved rule learning. |

Earlier research modules are retained while the new payment path is built; they are not the product's homepage or judging story. No feature is described as live merely because an adapter or mock exists.

## Run locally

Docker Desktop is recommended. Start the reliable Milestone 1 path first:

```bash
docker compose --profile anthos up --build
```

Open [CARAPACE's local page](http://localhost:8090) and the [API documentation](http://localhost:8080/docs). Run **Fake refund** and **Genuine bill**. Each creates a signed order and sends a generated screenshot plus fixture text to Gemini or the visibly labelled local fallback. The refund must be blocked. The bill waits for you to click **Confirm this artificial-money payment**; only then does the browser sign a test-device choice and one row post to the **CARAPACE local synthetic ledger**. The gate is not wired to Bank of Anthos's official transfer service.

The optional full sample bank can be started with `docker compose --profile anthos-full up --build` and opened at [localhost:8081](http://localhost:8081) using `testuser` / `bankofanthos`. Its x86 Java services can be slow or unavailable on an Apple Silicon Docker host; if the balance-reader is unhealthy, use the CARAPACE path above and do not count the separate bank website as a Milestone 1 integration result.

Run the automated suite with:

```bash
docker compose --profile test run --rm --build tests
```

The local AI provider is deliberately labelled `LOCAL_RULES`. To use live Gemini, configure an untracked `.env` from [.env.example](.env.example); never commit an API key. `/v1/ai/status` reports the configured provider. A configured provider alone is not proof that a successful live model call has occurred.

The bank API requires the tenant headers documented in [docs/api.md](docs/api.md). The current sequence is signed order → evaluation → test-device enrollment and exact-statement challenge → browser signature and recorded choice → submission. The browser page calls the bank API through its local server so no bank API key is exposed to JavaScript. `GET /v1/preflight/transfers` shows artificial-money effects; protection bundles are described in [docs/protection-proof.md](docs/protection-proof.md). These development credentials and enrollment rules must be replaced before any hosted pilot.

## Hackathon submission target

CARAPACE targets **BFSI: Intelligent Risk, Fraud & Financial Experiences** at Google Cloud AI Builder Cup 2026. The submission must show a working Google-AI-powered prototype deployed on Google Cloud, plus a public repository, short video and deck. The published prototype deadline is **18 October 2026**; the team should confirm its binding deadline on the Hack2skill dashboard.

The prototype uses synthetic financial data and clearly labelled integration limits. A real bank pilot would require the bank's consent, secure identity and key management, independent witness operation, privacy/security review, and production payment-gateway integration. CARAPACE does not promise zero fraud, automatic reimbursement, a legal finding or patentability.

## Documentation

- [Product specification and milestone plan](SPEC.md)
- [Step-by-step build plan](docs/BUILD_PLAN.md)
- [Milestone 1 implementation report](docs/MILESTONE_1_REPORT.md)
- [Milestone 2A protection-proof report](docs/MILESTONE_2A_REPORT.md)
- [Milestone 2B device-choice report](docs/MILESTONE_2B_REPORT.md)
- [Protection-proof guarantees and limits](docs/protection-proof.md)
- [Milestone 1 implementation decisions](docs/DECISIONS.md)
- [Existing Bank of Anthos integration boundary](docs/bank-of-anthos.md)
- [Existing API reference](docs/api.md)
- [Security policy](SECURITY.md)
