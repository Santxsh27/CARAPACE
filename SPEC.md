# CARAPACE — Autonomous financial operations guardian

Version 3.2 · updated 28 September 2026 · incremental implementation in the existing repository.

## Purpose

Resolve financial requests with executable, independently checked action plans. Establish the supported obligation, resolve routine exceptions within an agreed mandate and verify the resulting action. Investigation supports execution; it is not the product's final outcome. The everyday problem is the work and risk between a request for money and the records that justify it. Bank downtime is a supporting resilience concern, not the primary use case.

Initial users are business finance teams and, later, banks serving those businesses. CARAPACE is not a universal consumer banking overlay and has no ability to inspect unrelated banking apps.

## End-to-end product

1. An authorised connector receives an invoice or financial request.
2. Document extraction links claims to their source locations; Gemini interprets ambiguous descriptions and relationships. This extraction stage is still planned.
3. A bounded investigator chooses evidence lookups from enrolled supplier, procurement, warehouse and accounting systems.
4. An exact obligation engine reports contradictions and the remaining evidence needed. An AI explanation is never a financial fact.
5. The investigator retrieves further evidence until the obligation is supported, contradicted, unavailable or the investigation budget is exhausted.
6. Gemini generates a typed resolution program. The verifier checks supported amounts, identity, evidence citations, required steps, ordering and the balancing of the obligation. One correction attempt can use explicit verification errors; persistent errors or model failure stop execution.
7. A scoped mandate permits routine actions. A separate executor validates current evidence, recipient, amount, currency, limits and original operation identity before acting. It executes only allowlisted verbs, never model-generated Python, SQL, shell commands or arbitrary URLs.
8. The executor checks the recorded result and preserves the evidence and signed receipt. Unknown outcomes require reconciliation before retrying a non-idempotent operation.
9. Unsupported identity changes or unresolved contradictions remain held. Bank-required authorisation and business approval policies are not bypassed.

## Implemented operations slice

The homepage exposes six cases: routine, redirected beneficiary, partial delivery plus credit, missing delivery evidence, conflicting delivery evidence, and instructions embedded in an invoice. Data comes from server-owned Python fixtures, not real companies or external connectors.

The invoice is already structured. Gemini plans read-only evidence lookups with cited observed source keys and a bounded rationale. Each request's output schema limits lookups to missing sources and citations to already observed sources. Unknown tools, repeated tools and invented citations are rejected before execution; one bounded planning correction can use explicit error feedback, after which invalid output stops the run. Successful schema-parsed model responses are counted; this is not a billing-call count, and rejected responses may still incur provider cost. Configured-provider failures do not silently fall back. Explicit LOCAL_RULES mode uses a deterministic comparison planner.

The graph has typed evidence nodes and links to one invoice; it is not a full enterprise knowledge graph or learned causal model. Rule-specific conflict witnesses list records establishing a contradiction, not globally minimal unsatisfiable cores.

The single-line-item payable is: received quantity × agreed unit price − approved invoice-specific credits − prior allocations. Amounts use integer minor units. Checks bind supplier, order, invoice, currency and beneficiary. Partial payment requires explicit agreed terms. Taxes, FX, rounding, withholding, multiple line items and split allocations are not yet implemented.

A resolution program has up to four positive, evidence-linked actions: DEFER_UNDELIVERED, APPLY_APPROVED_CREDIT, RECOGNISE_PRIOR_PAYMENT and POST_PAYMENT. The exact verifier independently derives supported amounts from source records and requires the necessary actions exactly once in order. Six bounded negative guard tests check changed destinations, excess amount, missing delivery evidence, changed supplier identity, repeated payment and an omitted action. These are not a complete bank simulation or universal safety proof. A rule-generated program remains available as an explicitly labelled baseline; the live Gemini path does not receive that program as its answer.

A fixed development mandate permits only the enrolled supplier/account in INR with per-payment and aggregate limits. A separate SQLite operations gate rechecks the source snapshot and constraints, serialises posting with BEGIN IMMEDIATE, deduplicates tenant/invoice identity, signs the result and reads back the posting. The action journal, signed resolution receipt, posting and completed run commit together. An existing posting and action journal are checked against current evidence and their signatures before reuse; retries do not reapply credits. Signing or journal failure rolls the transaction back. A deferral is outstanding debt, not a saving or write-off.

This gate writes only the OPERATIONS_SYNTHETIC_LEDGER and SYNTHETIC_RESOLUTION_JOURNAL. It does not mutate warehouse records or external accounting systems. It is not the previous browser-confirmation gate, Anthos payment path, real bank transfer, settlement or production mandate service. Development routes are absent outside development/test environments.

Progress is saved in SQLite. Interrupted investigations remain incomplete; background resume, distributed job leases and cloud queue delivery are future work. Real connectors need versioned reads, freshness policies and write-side preconditions.

## Existing foundations retained

/payment-check retains the v3.1 experiment: bank-signed order, Gemini context extraction, enforced HOLD, browser-signed PROCEED/CANCEL, synthetic posting, separate local witness, Merkle inclusion/consistency checks and posting audit. Browser signing proves key control over bytes, not comprehension. The witness is not independently operated.

The optional Anthos bridge directly inserts and reads an exact-bound row in its artificial-money PostgreSQL sample ledger. A transactional outbox recovers interrupted delivery. It does not use the official LedgerWriter route or currently receive operations-workbench postings. These are distinct test integrations.

Previous fault analysis, counterfactual and release-passport modules remain research foundations. Autonomous production code repair and bank-ledger correction are not implemented.

## Research contribution to test

Can a constraint-driven evidence frontier reduce investigation work while retaining financial correctness under conflicting, missing and malicious evidence? Compare fixed complete retrieval, adaptive rules and Gemini-guided retrieval using identical gates, sources and budgets. Measure correct resolutions, false holds, unsupported execution, evidence calls, latency, cost and manual escalations.

Novelty, commercial advantage and patentability are unproven. Accounts-payable automation, fraud detection, evidence graphs and tool-using agents already exist. See [research and differentiation](docs/RESEARCH_AND_DIFFERENTIATION.md).

## Google technology and deployment

Use Gemini Developer API now, the existing Vertex AI adapter after project/identity setup, and Document AI when actual document ingestion is built. Cloud Run can host APIs and workers; select durable external storage first. The current SQLite file is not durable shared Cloud Run storage. Queue delivery, secret management and managed signing remain integration work.

No GCP billing or paid deployment is enabled by this milestone. Free-tier eligibility and costs need checking against the actual project. The team's binding deadline still needs confirmation in its authenticated Hack2skill dashboard.

## Acceptance and next milestones

1. Operations foundation: all six visible cases resolve or hold correctly; supported cases have a generated, verified and executed program; unsupported cases never post; retries, concurrency, malformed model output, model failure, tampering, atomic rollback and tenant isolation have tests. UI leads with completed outcomes and outstanding work, with evidence available on demand.
2. Real input: consented upload, grounded extraction and one authorised accounting connector. Model claims remain separate from connector authority.
3. Deeper reasoning: multiple obligations, partial allocations, contradictory versions and targeted evidence acquisition. Demonstrate improvements over deterministic baselines on unseen cases.
4. Durable automation: resumable jobs, managed identity, versioned mandates, external persistence and an authorised payment-provider sandbox.
5. Submission: deployed Google-AI workflow, measured evaluation, architecture/limits, video, deck and current README.

No zero-fraud, guaranteed recovery, universal safety proof, autonomous production patching, guaranteed prize or patent claim is part of the product promise.
