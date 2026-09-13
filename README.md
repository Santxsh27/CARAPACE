# CARAPACE

**Continuous Assurance and Recovery Across Payments, Applications, Customers and Engineering**

> Know before you pay. Prove what happened. Prevent it happening again.

CARAPACE is a payment-assurance platform built around one shared object: the
Payment Assurance Contract (PAC). A PAC records what a customer confirmed and
gives deterministic components a stable statement to compare with the payment
request, ledger evidence, customer receipt, and future release tests.

This repository starts with the trust core. The first milestone deliberately
contains no chatbot and no decorative dashboard. It implements:

- a versioned PAC schema;
- a versioned execution-evidence schema;
- canonical request hashing;
- a deterministic payment lifecycle state machine;
- exact checks for request mutation, duplicate debit, amount, currency,
  destination, idempotency, and settlement evidence;
- passing and deliberately failing sample executions;
- executable tests and a command-line demonstration.

Gemini integration, the consumer Lens, the bank SDK, Ledger Witness, ProofOps,
and the Firebase experience will be added on top of these stable contracts.
Gemini will produce proposed structured data and code changes; it will never
replace the verifier implemented here.

## Open in Visual Studio Code

Open the `CARAPACE` folder itself as the workspace. The included VS Code tasks
provide one-click commands for tests, the valid-payment demo, and Docker. No
extension is mandatory; the recommendations only improve Python, YAML, and
container editing.

## Run the foundation locally

Python 3.11 or newer is sufficient. The current milestone has no external
runtime dependencies.

```bash
cd outputs/carapace
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m carapace_core verify \
  examples/payment-promise.json \
  examples/execution-valid.json
PYTHONPATH=src python3 -m carapace_core verify \
  examples/payment-promise.json \
  examples/execution-duplicate-debit.json
```

The duplicate-debit verification is expected to exit with a failure verdict.
That is the controlled counterexample proving that the core detects a duplicate
financial effect.

## Run with Docker

Docker is the recommended team workflow because it fixes the Python version and
runtime environment for every contributor.

```bash
docker compose build
docker compose run --rm tests
docker compose run --rm verifier
docker compose --profile counterexample run --rm duplicate-debit-demo
```

The last command intentionally exits with code `1`: CARAPACE found the seeded
duplicate debit. The container runs as a non-root user and contains no secrets.

## Repository map

```text
carapace/
├── .github/workflows/          Automated GitHub checks
├── .vscode/                    Shared editor tasks and recommendations
├── docs/                       Product, architecture, and trust decisions
├── examples/                   Reproducible valid and failing payment evidence
├── schemas/                    Language-neutral JSON contracts
├── src/carapace_core/          Deterministic trust core
├── tests/                      Executable acceptance tests
├── Dockerfile                  Reproducible non-root runtime
└── compose.yaml                Team test and demonstration commands
```

## Frozen product boundary

- CARAPACE does not move money.
- CARAPACE does not request PINs, OTPs, CVVs, or banking passwords.
- AI output is a proposal, never authoritative payment evidence.
- A green result means named checks passed against supplied evidence; it does
  not mean the recipient is honest or that every possible threat was excluded.
- Production remediation remains subject to bank policy and human approval.

See [docs/architecture.md](docs/architecture.md) for the product planes and
[docs/roadmap.md](docs/roadmap.md) for the incremental build order.
