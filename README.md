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
- a real adapter for Google's official Bank of Anthos ledger database;
- the full official Bank of Anthos sample website and service stack in Docker;
- a visual control room showing raw ledger rows, contract binding, and verdicts;
- FeeShield: deterministic UPI MDR calculation, customer-surcharge protection,
  and merchant-settlement reconciliation for the October 2026 India policy;
- CARAPACE Lens: a working message-plus-UPI-request workflow that finds exact
  direction, amount, payee, PIN and pressure contradictions;
- a Gemini on Vertex AI structured-output adapter with prompt-injection
  boundaries and explicit provider/model provenance;
- an honestly labelled no-cost local intent provider so the demo remains fully
  runnable without cloud credentials;
- executable unit/API tests and command-line demonstrations.

Camera QR decoding, Document AI, BigQuery analytics, the bank SDK, the remaining
Ledger Witness stages, ProofOps, and the Firebase experience will be added on
top of these stable contracts. Gemini produces proposed structured data and
code changes; it never replaces the verifier implemented here.

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

Docker does not automatically open a browser. Keep the terminal running after
it prints `Uvicorn running on http://0.0.0.0:8080`, then open the documentation
link yourself. Stop the service later with `Control+C`.

In a second terminal, run all tests or either deterministic CLI demonstration:

```bash
docker compose --profile tools run --rm --build demo
docker compose --profile test run --rm --build tests
docker compose --profile tools run --rm verifier
docker compose --profile tools run --rm duplicate-debit-demo
```

The first command is the easiest complete check. It creates fresh synthetic
identifiers every time, proves a correct payment returns `MATCH`, proves a
duplicate debit returns `MISMATCH`, retrieves the persisted critical incident,
and prints `Overall: PASS`.

The duplicate-debit demonstration intentionally exits with code `1` because
CARAPACE found the seeded financial mismatch.

## See the Bank of Anthos connection

This is the easiest visual demonstration for a beginner. It starts Google's
official Bank of Anthos frontend, user, contacts, balance, history and ledger
services, both official PostgreSQL databases, the CARAPACE API, and a guided
control room:

```bash
docker compose --profile anthos-full up --build anthos-frontend anthos-demo
```

Keep that terminal open. Then use these two sites:

- [http://localhost:8081](http://localhost:8081) — the official Bank of Anthos
  website. Sign in with `testuser` / `bankofanthos`.
- [http://localhost:8090](http://localhost:8090) — the CARAPACE control room.
  It embeds the bank, identifies the exact database and table being read,
  shows recent raw rows, and maps a Payment Promise to deterministic checks.

Click **Run the bound safety test** in the control room. It creates a Payment
Promise, stores one artificial payment in the official ledger, verifies it,
forces a second retry debit, highlights both rows, and shows the incident and
failed rule.

This runs the official application containers locally through Docker Compose;
it is not a GKE deployment or a production bank. No cloud account, GCP billing,
or real money is used. A smaller ledger-only profile remains available as
`--profile anthos` for CI and low-memory checks. See
[docs/bank-of-anthos.md](docs/bank-of-anthos.md) for the exact boundary and the
production upgrade path.

The control room also includes a live **FeeShield check**. It submits a
₹10,000 merchant payment with an intentionally hidden ₹40 customer MDR to the
real CARAPACE API and shows the deterministic violation. The policy and
production boundary are documented in
[docs/fee-shield.md](docs/fee-shield.md).

The first section is now **CARAPACE Lens**. Run the prefilled refund example to
see a promised incoming refund compared with an actual outgoing UPI payment.
The local demo labels its extraction as `LOCAL_RULES`; configure Vertex AI to
use real Gemini structured output. See [docs/lens.md](docs/lens.md) and
[docs/google-cloud-alignment.md](docs/google-cloud-alignment.md).

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
├── src/carapace_ai/            Gemini provider boundary and local demo provider
├── src/carapace_core/          Deterministic trust core
├── src/carapace_integrations/  Bank adapters and isolated local demo
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
