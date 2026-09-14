# CARAPACE

**Continuous Assurance and Recovery Across Payments, Applications, Customers and Engineering**

> Know before you pay. Prove what happened. Prevent it happening again.

CARAPACE is a payment-assurance platform built around one shared object: the
Payment Assurance Contract (PAC). A PAC records what a customer confirmed and
gives deterministic components a stable statement to compare with the payment
request, ledger evidence, customer receipt, and future release tests.

This repository starts with the trust core and the first production-shaped API.
The current milestone deliberately contains no chatbot and no decorative
dashboard. It implements:

- a versioned PAC schema;
- a versioned execution-evidence schema;
- canonical request hashing;
- a deterministic payment lifecycle state machine;
- exact checks for request mutation, duplicate debit, amount, currency,
  destination, idempotency, and settlement evidence;
- a Cloud Run-compatible REST API with strict request validation;
- tenant-isolated contract, verification-run, and incident storage;
- automatic critical evidence-case creation for deterministic mismatches;
- live, readiness, and generated OpenAPI endpoints;
- passing and deliberately failing sample executions;
- executable unit/API tests and command-line demonstrations.

Gemini integration, the consumer Lens, the bank SDK, Ledger Witness, ProofOps,
and the Firebase experience will be added on top of these stable contracts.
Gemini will produce proposed structured data and code changes; it will never
replace the verifier implemented here.

## Open in Visual Studio Code

Open the `CARAPACE` folder itself as the workspace. The included VS Code tasks
provide one-click commands for tests, the valid-payment demo, and Docker. No
extension is mandatory; the recommendations only improve Python, YAML, and
container editing.

## Fastest start: Docker

Docker is the recommended team workflow. It gives every contributor the same
Python version and starts the API with a persistent local evidence volume.

```bash
cd /path/to/CARAPACE
docker compose up --build api
```

Then open [http://localhost:8080/docs](http://localhost:8080/docs) for the live
interactive API. The Compose configuration uses the explicitly non-production
demo tenant `demo-bank` and key `local-demo-key-change-me`.

In a second terminal, run all tests or either deterministic CLI demonstration:

```bash
docker compose --profile test run --rm --build tests
docker compose --profile tools run --rm verifier
docker compose --profile tools run --rm duplicate-debit-demo
```

The duplicate-debit demonstration intentionally exits with code `1` because
CARAPACE found the seeded financial mismatch.

## Run without Docker

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m unittest discover -s tests -v
carapace-api
```

The service uses SQLite locally and listens on port `8080` by default. See
[docs/api.md](docs/api.md) for the authenticated end-to-end workflow.

## Repository map

```text
carapace/
├── .github/workflows/          Automated GitHub checks
├── .vscode/                    Shared editor tasks and recommendations
├── docs/                       Product, architecture, and trust decisions
├── examples/                   Reproducible valid and failing payment evidence
├── schemas/                    Language-neutral JSON contracts
├── src/carapace_api/           Tenant-isolated assurance API and evidence store
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
- The local API key and SQLite store are development adapters, not production
  identity or storage controls.

See [docs/architecture.md](docs/architecture.md) for the product planes and
[docs/roadmap.md](docs/roadmap.md) for the incremental build order.
