# CARAPACE

## Autonomous financial operations guardian

**Resolve the obligation. Execute permitted actions. Verify the outcome.**

CARAPACE turns financial requests into checked, executable resolution plans. Gemini gathers evidence across supplier, purchase-order, warehouse and accounting records, then generates a typed action program: defer undelivered goods, apply approved credits, recognise earlier payments and pay the supported remainder. An independent verifier rejects unsupported instructions. A mandate-limited executor records the permitted effects, creates an artificial-money posting and checks the stored outcome. Routine cases complete without another customer confirmation. Unsupported beneficiary changes, missing evidence and conflicting records stay stopped.

**Current scope:** a runnable development workbench with six server-owned synthetic cases, live Gemini and explicit local-rule modes, saved resolution programs, a financial evidence graph, and a separate synthetic operations ledger and action journal. It does not yet connect to real supplier systems, read arbitrary uploaded invoices, or move real funds. Credits and deferrals are recorded locally, not written to an external accounting system. The previous signed payment-check and Anthos experiments remain at `/payment-check` as reusable foundations. No capability is called live solely because an adapter exists.

## Start with the operations workbench

Open [localhost:8090](http://localhost:8090) after starting Docker with the command below. Select **Google AI · configured provider** for Gemini, or **Local demo · no AI call** for a no-model comparison. Try:

- **Routine supplier invoice:** retrieve the five required records and post ₹4.8 lakh under a fixed development mandate.
- **Changed beneficiary:** retrieve the previously enrolled account, expose the contradiction and make no posting.
- **Partial delivery + credit:** establish 80 of 100 units received, record a ₹96,000 deferral, apply a ₹24,000 approved credit and post the supported ₹3.6 lakh. Partial payment is explicitly allowed by the test order. The deferred amount remains an obligation, not money saved.
- **Missing evidence / conflicting records / hidden document instructions:** investigate and stop without inventing a financial fact.

The first result shows completed actions and what remains outstanding; technical evidence is expandable. Each run exposes the actual tool trace, retrieved records, model-generated program, independent checks, policy, signed result and persisted run ID. Repeating a completed invoice returns its original checked posting without applying the credit twice. The model has no direct payment access and cannot write a new beneficiary. All accounts and connector records in these examples are artificial.

```text
Invoice → Gemini investigation → bounded evidence lookups
                   ↑                        ↓
              missing facts ← exact obligation checks
                                            ↓
                         HOLD / no payment due / supported payable
                                            ↓
                         Gemini generates a typed resolution program
                                            ↓
                     exact verifier + six bounded negative guard tests
                                            ↓
                       mandate-limited executor + atomic action journal
                                            ↓
                      signed resolution + posting + exact local readback
```

See [the operations milestone report](docs/OPERATIONS_MILESTONE_1.md) for implementation and evaluation, and [research and differentiation](docs/RESEARCH_AND_DIFFERENTIATION.md) for existing products and the unproven research hypothesis. We do not claim that invoice automation, evidence graphs or agentic investigations are new inventions.

## Earlier payment-check foundation

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
| Bank test environment | A permitted synthetic posting atomically creates a durable delivery item. The development worker retries an exact-bound insert/readback in Bank of Anthos's artificial-money PostgreSQL ledger after an outage; a repeat reuses the same row. This is a **direct test insert**, not Bank of Anthos's official transfer service or a production bank integration. |
| Deterministic verification | Existing contract, receipt and test modules remain in the repository as reusable engineering foundations. |
| Milestone 1 | Ed25519-signed bank payment order, signed decision, server-side `HOLD` gate, one-time synthetic transfer, screenshot-capable Gemini adapter, and two interactive cases are implemented. A successful live Google call is reported separately from provider configuration. |
| Evidence slices | The gate atomically issues bank-signed decision, browser-choice and posting records. A temporary P-256 browser key signs the exact test statement; a second local key signs Merkle tree heads. RFC 9162 consistency proofs let a separate checker compare a new signed head with one it retained. A read-only audit verifies every observed CARAPACE synthetic posting has its signed decision, choice and posting evidence. This does not prove human comprehension, complete outside-rail coverage or production customer identity. |
| Operations resolution | Six development cases, Gemini evidence planning and executable program synthesis, exact obligation arithmetic, bounded adversarial checks, mandate-limited action journal, persistent runs and signed synthetic execution results. |
| Next product milestones | Real authorised accounting connector, grounded document extraction, richer obligations, independent evaluation, resumable jobs and cloud persistence. Existing payment identity and witness hardening remain integration work. |

The operations workbench is the homepage and current build focus. Payment checks and earlier engineering modules remain available; they are not yet a single production integration.

## Run locally

Docker Desktop is recommended. Start the local workspace:

```bash
docker compose --profile anthos up --build
```

Open [CARAPACE's local page](http://localhost:8090) and the [API documentation](http://localhost:8080/docs). The operations cases execute in their own synthetic ledger; they do not use Anthos. For the earlier refund/bill experiment, open [Payment check](http://localhost:8090/payment-check). That flow still requires a browser-signed choice and uses a durable, exact-bound **direct test insert** into the Anthos sample ledger. It is not Anthos's official transfer route.

The optional full sample bank can be started with `docker compose --profile anthos-full up --build` and opened at [localhost:8081](http://localhost:8081) using `testuser` / `bankofanthos`. Its x86 Java services can be slow or unavailable on an Apple Silicon Docker host; if the balance-reader is unhealthy, use the CARAPACE path above and do not count the separate bank website as a Milestone 1 integration result.

Run the automated suite with:

```bash
docker compose --profile test run --rm --build tests
```

The local AI provider is deliberately labelled `LOCAL_RULES`. To use live Gemini, configure an untracked `.env` from [.env.example](.env.example); never commit an API key. `/v1/ai/status` reports the configured provider. Operations runs report their own successful live model-call count. A model timeout stops investigation; it does not silently switch to local rules. Explicit local mode is available for free repeatable testing.

Run the small local comparison with `docker compose exec api python -m carapace_core.operations_benchmark`. This compares early stopping against fetching all five sources on six hand-authored fixtures; it is not a real-world fraud accuracy claim.

The bank API requires the tenant headers documented in [docs/api.md](docs/api.md). The current sequence is signed order → evaluation → test-device enrollment and exact-statement challenge → browser signature and recorded choice → submission. The browser page calls the bank API through its local server so no bank API key is exposed to JavaScript. `GET /v1/preflight/transfers` shows artificial-money effects; `GET /v1/preflight/audit` checks their evidence chain. The public hash-only checkpoint endpoint and independent monitor are described in [docs/protection-proof.md](docs/protection-proof.md). These development credentials and enrollment rules must be replaced before any hosted pilot.

## Hackathon submission target

CARAPACE targets **BFSI: Intelligent Risk, Fraud & Financial Experiences** at Google Cloud AI Builder Cup 2026. The submission must show a working Google-AI-powered prototype deployed on Google Cloud, plus a public repository, short video and deck. The published prototype deadline is **18 October 2026**; the team should confirm its binding deadline on the Hack2skill dashboard.

The prototype uses synthetic financial data and clearly labelled integration limits. Cloud deployment still needs durable external storage and managed identity: the current SQLite file must not be treated as durable Cloud Run storage or shared across replicas. A real integration needs authorised connectors and a bank-owned payment adapter. CARAPACE does not promise zero fraud, automatic reimbursement, a legal finding, patentability or a hackathon prize.

## Documentation

- [Product specification and milestone plan](SPEC.md)
- [Step-by-step build plan](docs/BUILD_PLAN.md)
- [Milestone 1 implementation report](docs/MILESTONE_1_REPORT.md)
- [Milestone 2A protection-proof report](docs/MILESTONE_2A_REPORT.md)
- [Milestone 2B device-choice report](docs/MILESTONE_2B_REPORT.md)
- [Milestone 2C checkpoint and audit report](docs/MILESTONE_2C_REPORT.md)
- [Milestone 3A Anthos test-ledger bridge report](docs/MILESTONE_3A_REPORT.md)
- [Milestone 3B recoverable test-delivery report](docs/MILESTONE_3B_REPORT.md)
- [Protection-proof guarantees and limits](docs/protection-proof.md)
- [Milestone 1 implementation decisions](docs/DECISIONS.md)
- [Existing Bank of Anthos integration boundary](docs/bank-of-anthos.md)
- [Existing API reference](docs/api.md)
- [Security policy](SECURITY.md)
