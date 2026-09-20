# CARAPACE architecture baseline

## Product promise

CARAPACE carries one verifiable payment promise from what a customer confirms,
through what a bank submits and records, into the tests that future software
releases must pass.

## Product planes

```text
UNTRUSTED CONTEXT
message / QR / invoice / webpage
              |
              v
CARAPACE LENS
Gemini proposes structured context and contradictions
              |
              v
BANK TRUST ZONE
PayShield shows bank-canonical fields and creates a confirmed PAC
              |
              v
DETERMINISTIC REFERENCE MONITOR
signature / expiry / nonce / payload / policy / idempotency checks
              |
              v
BANK PAYMENT SYSTEM
the bank continues to authenticate and execute the payment
              |
              v
LEDGER WITNESS
reconciles the PAC with processor, core, and ledger evidence
              |
        +-----+-----+
        |           |
      MATCH       MISMATCH
        |           |
Trust Receipt    Evidence Case
                    |
                    v
PROOFOPS PRIVATE RUNNER
reproduce -> explain -> patch proposal -> regression -> human approval
```

## Trust hierarchy

1. Human-approved financial contracts define intended behaviour.
2. Bank-canonical payment fields define what is being authorized.
3. Independently collected ledger state defines what was recorded.
4. Authenticated traces support reconstruction but do not establish financial
   correctness by themselves.
5. Application logs are debugging hints.
6. Gemini outputs are proposed interpretations, scenarios, causes, patches, or
   tests. They are never the final financial verdict.

## Current executable boundary

Milestones 0 and 1 implement the PAC, execution evidence, lifecycle machine,
request digest, deterministic verifier, authenticated REST boundary,
tenant-isolated storage, and automatic evidence-case creation. The first Lens
slice additionally implements a bounded Vertex Gemini adapter, an honestly
labelled local fallback, canonical UPI URI parsing and deterministic semantic
reconciliation. Later components must communicate through these versioned
schemas and API contracts rather than bypassing them.

```text
Authenticated tenant
        |
        v
POST Payment Assurance Contract
        |
        v
Strict schema + canonical digest validation
        |
        v
POST execution evidence
        |
        v
Deterministic verifier
        |
   +----+----+
   |         |
 MATCH    MISMATCH
   |         |
Stored run   +--> Stored critical evidence case
   |         |
   +----+----+
        |
        v
Stored Trust Receipt with explicit assurance stages
```

The public Lens path is intentionally separate:

```text
Untrusted message -> structured intent extraction (Gemini or labelled local mode)
Decoded UPI URI   -> deterministic canonical parser
                         |
                         v
               deterministic contradiction policy
                         |
              ALLOW / CAUTION / STOP / UNVERIFIED
```

The current SQLite adapter makes this flow real and persistent on a developer
machine or single-container demo. It is deliberately hidden behind the store
boundary so Firestore or another bank-approved database can replace it without
changing PAC or verifier semantics. Static API keys are only a local integration
mechanism; production deployments require managed identity and short-lived
credentials.

## Planned deployment shape

- Firebase: consumer and bank-facing user interfaces.
- Cloud Run: control-plane APIs and Google ADK orchestration.
- Gemini on Vertex AI or an approved Google AI endpoint: bounded semantic work.
- Firestore: workflow metadata, contracts, cases, and approvals.
- Cloud Storage: large traces and evidence bundles.
- Cloud KMS: PAC, receipt, and release-passport signatures.
- Customer-managed private runner: source analysis and isolated bank execution.

For the hackathon, Bank of Anthos is the authorized application under test and
all accounts and funds are artificial.
