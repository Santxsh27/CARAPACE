# CARAPACE v3.1 — Payment Intent Firewall & Proof of Protection

Status: approved product direction; implementation is incremental. This document is the single product specification for the existing CARAPACE repository. It describes intended behaviour, not a claim that every capability already exists.

## Product promise

For a bank-integrated payment, CARAPACE compares the meaning of customer-supplied context with bank-controlled payment details, enforces a deterministic pre-payment decision, and preserves a verifiable record of the warning and choice. It does not move real funds, guarantee that a person understood a warning, or decide legal liability.

## One end-to-end path

1. An authenticated bank gateway creates a canonical payment envelope: transaction ID, customer reference, amount in minor units, currency, direction, recipient ID, expiry, nonce and policy version. A bank-controlled signing key signs the envelope.
2. The customer voluntarily supplies the message, screenshot, bill or QR that influenced them. No background access to messages, calls or other banking apps is assumed.
3. Gemini extracts structured, evidence-linked claims from that untrusted material. Deterministic code validates the claims and compares them with the signed payment envelope.
4. The policy returns ALLOW, WARN or HOLD. A definite receive-versus-send contradiction is HOLD. AI can add a supported concern but cannot cancel a deterministic HOLD.
5. The payment gateway requires the decision token before submitting the artificial-money transfer. HOLD cannot be submitted. ALLOW can proceed. WARN requires an explicit recorded choice under bank policy.
6. A protection receipt binds the envelope, exact warning, choice, policy and outcome. Bank and registered-device signatures are checked independently. A later witness log makes included records tamper-evident.
7. A dispute workbench reports verified facts and uncertainty. Gemini may draft an explanation but does not determine liability.

## Trust boundaries

- Bank payment fields originate from the bank gateway, never from the message or customer-controlled web fields. The gateway pins the bank signing key and checks the decision token against the same envelope before moving artificial funds.
- Untrusted context is data, never instructions to the model or policy engine. Values used in a customer warning need source evidence and deterministic grounding.
- Browser-device signing proves that a registered device key acknowledged bytes. It does not prove a human saw, understood, or freely chose them. Local development keys are not production identity assurance.
- A Merkle inclusion proof proves inclusion in a particular signed tree head. It does not prove that all payments were logged. Complete coverage requires a bank payment gate and reconciliation of completed payments against decision IDs.
- The demo witness is separately keyed and can reject inconsistent history, but is not operationally independent while run by the same team.
- A receipt holder may disclose a full evidence bundle; public verification endpoints expose hashes and proofs, not private context or payment details.

## Core algorithm: Intent-to-Instruction Engine

Gemini converts supplied context into claims `{action, amount, entity, urgency, authority, evidence_span}`. The parser output is schema-validated. A deterministic normaliser checks each cited span against the supplied text or OCR result; unsupported values are discarded. The comparison engine forms named contradictions between supported claims and the signed envelope: receive versus send; stated versus actual amount; represented entity versus bank-verified recipient; QR payload versus canonical order. Each rule produces a reason code and severity. The final verdict is the maximum severity and cannot be reduced by an AI output or a customer answer. In degraded mode, deterministic checks continue and the limitation is shown.

## Milestones

### Milestone 0 — repositioning

README, served homepage and this specification describe the Payment Intent Firewall as the primary product. Earlier engineering demonstrations remain available only as legacy code until safely retired. No prior claim of a working pre-payment gate is made.

### Milestone 1 — working pre-payment protection

- Bank-signed canonical payment envelope, verified before evaluation and again at submission.
- A bank-controlled artificial-money transfer gate that refuses HOLD, rejects changed/expired/replayed envelopes, and records a successful ALLOW transfer.
- One live Gemini context check for a refund screenshot or supplied image; a genuine bill case passes. Local fallback remains explicitly labelled and must never masquerade as a live call.
- Automated tests cover signing, tampering, HOLD non-posting, ALLOW posting, isolation, provider failure and both scenarios.
- A simple customer page demonstrates the path and states what is simulated.

The local Bank of Anthos ledger is an authorised artificial-money test integration. Until its official transfer path is wired into the gate, a controlled test adapter may write the sample ledger behind the gate; that limitation must be displayed and documented.

**Implementation state (25 September 2026):** the signed local order, signed decision, enforced HOLD/ALLOW gate, screenshot-capable Gemini adapter and browser demo are implemented. The full 63-test Docker suite passed. A live Gemini 3.5 Flash Lite call held the generated refund screenshot and another allowed the generated bill. The gate currently posts to a transactionally protected **CARAPACE synthetic SQLite ledger**, not Bank of Anthos's official transfer path. Independent OCR for image-only value grounding, signed customer protection receipts and Bank of Anthos in-path posting remain open integration work.

### Milestone 2 — evidence protocol

Registered device acknowledgement, signed protection receipts, independent receipt verifier, append-only Merkle log, separately keyed witness, tamper demonstration and payment-to-decision reconciliation.

**Incremental evidence state (26 September 2026):** the local gate now issues a bank-signed warning/decision record and, only for an allowed synthetic posting, a separate bank-signed posting record. Both are appended inside the same SQLite transaction as their respective decision or transfer. A second local signing key authenticates Merkle tree heads, and a verifier can check inclusion using externally pinned keys. This proves record integrity and inclusion in one checkpoint, not that the customer saw the warning, that all payments were logged, or that successive checkpoints are append-only. Device acknowledgement, consistency proofs, reconciliation and an operationally independent witness remain open Milestone 2 work.

### Milestone 3 — learning and dispute tools

Gemini-assisted rule proposal with deterministic held-out replay and human approval; evidence-grounded dispute summaries. These do not alter production policies or make legal determinations autonomously.

### Milestone 4 — submission

Deploy a working Google-AI-powered prototype to Cloud Run or Firebase, measure on a labelled corpus, document limitations, and provide a public repository, PDF deck and video under three minutes. Published prototype submission deadline: 18 October 2026; verify the team's binding date in the Hack2skill dashboard.

## Technology choice

Keep the existing Python/FastAPI, Docker and Bank of Anthos test environment. Use the existing Gemini provider abstraction. Add a small browser UI; do not rewrite the repository into a new language solely for presentation. Local signing uses an isolated development key; a hosted bank pilot requires managed signing keys, authenticated device enrolment, durable storage, independent witness operations, privacy review and security assessment. Suggested Google Cloud services are selected only when they serve a real role; Gemini plus Cloud Run are essential to the hackathon submission.

## Claims we will not make

No zero-fraud promise; no claim of access to a real bank or UPI rail; no statement that browser signing proves human comprehension; no assertion that a missing log entry proves a warning was absent; no automatic legal verdict; no guaranteed patent novelty, prize or zero cloud cost. Show only measured performance numbers.
