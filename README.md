# CARAPACE

## Continuous Assurance and Recovery Across Payments, Applications, Customers and Engineering

> **Know before you pay. Prove what happened. Prevent it happening again.**

CARAPACE is an AI-assisted financial-assurance platform for banking and payments. It protects one payment journey from the message, QR code or invoice that persuaded a customer to pay, through the exact payment that was approved, to the ledger entry the bank recorded and the software failure that could make the issue happen again.

It is not a generic fraud score, a chatbot, a replacement bank or a payment processor. CARAPACE connects the journey through one evidence object: the **Payment Assurance Contract**, shown to customers as a **Payment Promise**.

## Why CARAPACE exists

Customers can be tricked into authorising a payment themselves. A bank can also have a genuine software defect, for example a lost response causing a retry and two ledger debits instead of one. Most products address only one part of this story. CARAPACE creates one evidence chain across the customer, payment, ledger and engineering layers.

```text
Message / QR / invoice
        ↓
What the customer believes
        ↓
Payment Promise: what the customer confirms
        ↓
Bank request and ledger evidence
        ↓
Deterministic financial verification
        ↓
Trust Receipt or evidence incident
        ↓
AI-assisted root-cause hypothesis + isolated counterfactual test
        ↓
Permanent regression knowledge + human-reviewed repair
```

## The Payment Promise

A Payment Promise is a versioned, integrity-bound contract for what the customer approved. Example:

```text
Direction:       SEND
Amount:          ₹4,999
Recipient:       ABC Electronics
Purpose:         Order 7782
Expires:         7:30 PM
Maximum debits:  1
```

It includes a nonce, request digest, idempotency key, lifecycle state and evidence references. CARAPACE can then verify whether the bank posted one debit of the approved amount to the approved destination.

## What is implemented now

| Part | Working capability |
|---|---|
| **CARAPACE Lens** | Compares a message and decoded UPI request to find exact contradictions such as “refund expected” but “money will be sent.” |
| **Payment Promise + verifier** | Validates request digest, amount, currency, payee, lifecycle, idempotency, settlement evidence and maximum debits. |
| **Ledger Witness demo** | Reads authoritative artificial-money rows from Google’s official Bank of Anthos sample ledger; it does not scrape webpage pixels. |
| **Trust Receipts** | Shows payment fields bound, bank posting matched, settlement pending/confirmed, mismatch or unverified. |
| **FeeShield** | Deterministically calculates versioned UPI MDR policy and finds hidden customer surcharges or incorrect merchant deductions. |
| **ProofOps** | Converts a confirmed mismatch into a bounded AI hypothesis, isolated counterfactual safety search and regression scenarios. |
| **Control Room** | A visual local website that connects the bank, raw ledger rows, Promise, rules, receipts and ProofOps. |

All banking data and money in the current build are artificial and run locally through Docker.

## Complete demo workflow

The Control Room runs this end-to-end experiment:

1. A customer approves one artificial `$49.99` payment.
2. CARAPACE creates a Payment Promise with `maximum_debits = 1`.
3. The harness writes one real row to the local Bank of Anthos PostgreSQL ledger.
4. CARAPACE reads that exact server-side row and returns `MATCH`.
5. A deliberately simulated lost-response retry writes a second debit.
6. The deterministic verifier returns `MISMATCH` because two debits violated the one-debit promise.
7. CARAPACE preserves an evidence case and a red Trust Receipt.
8. ProofOps proposes a retry/idempotency cause, then searches isolated copies of the evidence for the smallest allowed intervention that restores every invariant.
9. The UI shows `MISMATCH → MATCH`, the tested intervention, regression scenarios and **Human approval required**.

This is more than an AI report: AI produces a constrained, testable hypothesis and CARAPACE independently reruns the financial verifier to check it.

## CARAPACE Lens: check before paying

Example:

```text
Story: “ABC Support will refund ₹4,999. Scan this QR and enter your UPI PIN.”
UPI request: upi://pay?pa=rktraders@upi&pn=R%20K%20Traders&am=4999&cu=INR

Intent extraction:       RECEIVE_EXPECTED · ABC Support · ₹4,999
Canonical UPI parser:    SEND · R K Traders · ₹4,999
Deterministic result:    STOP
```

The user sees the exact reason: an incoming-refund story conflicts with an outgoing payment, the named company and payee differ, and a PIN is requested for a supposed incoming transfer. CARAPACE never asks for a PIN, OTP, CVV, password or bank login.

## ProofOps: the difficult AI task

ProofOps starts only after deterministic verification has found a real mismatch. Gemini receives a minimised evidence bundle containing failed check codes, lifecycle states, debit counts and equality signals. Raw account identifiers are removed.

Gemini must return strict structured data containing only:

- a testable suspected component;
- the deterministic evidence codes supporting it;
- predefined repair directions;
- a patch strategy for human review; and
- adversarial regression scenarios.

Then **Counterfactual Safety Search** tests the proposal. It explores the smallest combination of these isolated, allowlisted interventions:

```text
DEDUPLICATE_LOGICAL_DEBITS
REUSE_CONTRACT_IDEMPOTENCY_KEY
RESTORE_BOUND_PAYMENT_REQUEST
```

Each candidate is rerun through the same deterministic financial verifier. The result records the original verdict, counterfactual verdict, number of experiments and minimal intervention. It never patches source code, modifies a real ledger, refunds money or authorises a production release.

## AI and trust boundaries

| Job | Decision-maker |
|---|---|
| Interpret untrusted message, invoice or refund story | Gemini or clearly-labelled local development provider |
| Parse UPI amount, direction and payee | Deterministic canonical parser |
| Decide whether story and payment contradict | Deterministic named rules |
| Check amount, duplicate debit, idempotency and lifecycle | Deterministic financial verifier |
| Rank a causal hypothesis and generate scenarios | Gemini or local development provider |
| Prove a repair direction restores a contract | Counterfactual Safety Search + verifier |
| Approve refunds, releases or production changes | Authorised bank human and bank policy |

AI output is always provenance-labelled. The no-cost fallback displays `LOCAL_RULES`; it never claims to be Gemini.

## Google Cloud and hackathon alignment

CARAPACE directly addresses fraud mitigation, transaction anomaly analysis, compliance automation, risk assessment and safer financial experiences.

| Google technology | CARAPACE role | Status |
|---|---|---|
| **Gemini on Vertex AI** | Structured Lens extraction; later ProofOps cause, patch and regression proposals | Adapter implemented; needs GCP identity for live calls |
| **Gemini Developer API / AI Studio** | No-cost development path for the same structured Gemini interface | Adapter implemented; needs backend-only API key |
| **Cloud Run** | API, Lens and orchestration services | Current API is containerised and Cloud Run-compatible |
| **Pub/Sub** | Processor, ledger, reversal and settlement event ingestion | Planned Ledger Witness milestone |
| **BigQuery / Vertex AI** | Event analytics, evaluation metrics, anomaly cohorts and calibrated risk models | Planned after event ingestion |
| **Document AI** | Invoice and statement extraction with evidence references | Planned Lens input |
| **Vertex AI Search** | Retrieval over approved policies, runbooks and prior incidents | Planned ProofOps capability |
| **Cloud SQL / Firestore / Storage / KMS** | Production metadata, evidence artifacts and signatures | Development SQLite adapter exists; production migration is planned |

CARAPACE does not claim live Vertex AI while credentials are absent. The active mode is visible at `GET /v1/ai/status` and in the Control Room.

## Architecture

```text
UNTRUSTED CONTEXT
message / QR / invoice / webpage
              │
              ▼
CARAPACE LENS
Gemini interprets context; deterministic code parses payment fields
              │
              ▼
PAYMENT PROMISE
customer-approved, versioned and integrity-bound payment facts
              │
              ▼
BANK PAYMENT SYSTEM
Bank of Anthos in this controlled demo; a bank system in production
              │
              ▼
LEDGER WITNESS
independent evidence collection and deterministic reconciliation
              │
       ┌──────┴──────┐
       ▼             ▼
     MATCH        MISMATCH
       │             │
Trust Receipt   Evidence Case
                     │
                     ▼
              PROOFOPS
        hypothesis → counterfactual test → regression plan
                     │
                     ▼
              HUMAN APPROVAL
```

## Run the full visual demo

### Requirements

- Docker Desktop
- At least 8 GB of available memory recommended for the full Bank of Anthos stack

### Start the environment

```bash
git clone https://github.com/Santxsh27/CARAPACE.git
cd CARAPACE
docker compose --profile anthos-full up --build
```

Keep the terminal open, then visit:

- [CARAPACE Control Room](http://localhost:8090)
- [Official Bank of Anthos sample website](http://localhost:8081)
- [CARAPACE API documentation](http://localhost:8080/docs)

The Bank of Anthos demo login is `testuser` / `bankofanthos`. It is a Google sample application running only on your Mac with artificial accounts and money.

In the Control Room:

1. Try **Check before paying** in Lens.
2. Run the **FeeShield** policy check.
3. Click **Run the bound safety test**.
4. Read the Payment Promise → ledger row → rule mapping.
5. Read the ProofOps counterfactual result below it.

### Run the automated tests

```bash
cd CARAPACE
docker compose --profile test run --rm --build tests
```

The suite currently has 53 automated tests covering contracts, verification, tenant isolation, Lens safety boundaries, Gemini adapters, FeeShield, Bank of Anthos mapping, Trust Receipts and Counterfactual Safety Search.

### Stop the local environment

```bash
docker compose --profile anthos-full down
```

Docker volumes retain local artificial demo data. No real bank or money is connected to this project.

## Enable live Gemini safely

The project works without cloud credentials. To use live Gemini, create an untracked `.env` from `.env.example`; never commit a key.

### Gemini Developer API / AI Studio

```text
CARAPACE_AI_PROVIDER=gemini
GOOGLE_API_KEY=your-ai-studio-key
CARAPACE_GEMINI_MODEL=gemini-3.6-flash
```

### Vertex AI

```text
CARAPACE_AI_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
CARAPACE_GEMINI_MODEL=gemini-3.6-flash
```

Restart the API after setting credentials and verify the selected mode:

```bash
curl -s http://localhost:8080/v1/ai/status
```

Keys remain backend-only. Gemini failures fail closed; CARAPACE does not silently switch to local mode and claim that live AI ran.

## Honest product boundary

CARAPACE does:

- make a suspicious payment story understandable before payment;
- bind confirmed payment fields to a contract;
- find exact financial mismatches such as duplicate debit;
- produce auditable receipts and incident evidence;
- use AI to form bounded, testable repair hypotheses; and
- preserve confirmed failures as future regression knowledge.

CARAPACE does not:

- promise zero fraud or universal safety;
- replace a bank’s authentication, fraud engine or payment rail;
- invisibly inspect unsupported banking apps;
- request payment secrets;
- automatically edit a production ledger, issue a refund or deploy a patch; or
- treat an AI explanation as proof.

## Current status and production path

| Stage | Scope |
|---|---|
| **Working hackathon vertical slice** | Lens, Payment Promise, verifier, artificial Bank of Anthos ledger integration, Trust Receipts, FeeShield, ProofOps, Control Room and tests run locally in Docker. |
| **Controlled bank pilot** | Private runner in staging, event observation without blocking payments or releases, measurement of false positives and time-to-detection. |
| **Integrated bank deployment** | PayShield SDK, canonical payee resolution, event ingestion, ledger/settlement adapters and approved containment rules. |
| **Production assurance network** | Cloud deployment, managed identity, data-residency controls, audit and resilience testing. |

## Repository map

```text
CARAPACE/
├── docs/                       Product, trust, cloud and implementation decisions
├── examples/                   Reproducible valid and failing payment evidence
├── schemas/                    Language-neutral payment and execution contracts
├── src/carapace_ai/            Gemini, local provider and redaction boundaries
├── src/carapace_api/           Tenant-isolated API, storage and endpoints
├── src/carapace_core/          Verifier, lifecycle, Lens, receipts and algorithms
├── src/carapace_integrations/  Bank of Anthos adapter and Control Room
├── tests/                      Executable unit and API acceptance tests
├── Dockerfile                  Reproducible non-root Python runtime
├── compose.yaml                Full local environment and test profiles
└── .env.example                Safe local Gemini / Vertex configuration template
```

## Further reading

- [Architecture and trust hierarchy](docs/architecture.md)
- [Lens safety boundary](docs/lens.md)
- [ProofOps and Counterfactual Safety Search](docs/proofops.md)
- [Bank of Anthos integration boundary](docs/bank-of-anthos.md)
- [Trust Receipts](docs/trust-receipts.md)
- [FeeShield policy and guardrails](docs/fee-shield.md)
- [Google Cloud alignment](docs/google-cloud-alignment.md)
- [API workflow](docs/api.md)

## Safety note

This repository is a controlled hackathon and engineering demonstration. It is not financial advice, a live banking service or a substitute for a bank’s security, regulatory and operational controls.
