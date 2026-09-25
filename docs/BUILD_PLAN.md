# CARAPACE v3.1 build sequence

This is the short execution checklist for the existing repository. Each stage ends with a demonstrated behaviour and a test report; a checked code item is not a claim of production readiness.

## 0. Repositioning — complete

- [x] README, served homepage and SPEC lead with the Payment Intent Firewall.
- [x] The legacy engineering demos are no longer the judging story or homepage.
- [x] Search these three primary files for old duplicate-payment framing and report the zero-match result.

## 1. Pre-payment gate — implemented locally

- [x] Authenticated development bank gateway signs an immutable payment envelope.
- [x] A second signed decision binds the same envelope.
- [x] Gemini Developer API accepts text plus a test screenshot; local rules are visibly labelled.
- [x] Deterministic checks compare receive/send, amount and named payee with the signed order.
- [x] HOLD and unresolved WARN cannot post; ALLOW posts one synthetic ledger row; replay and tampering fail.
- [x] Refund and bill flows are run from a plain-language browser page.
- [x] Full Docker regression suite passes, including new gate tests.

Milestone 1 stops at a **CARAPACE local synthetic ledger**. The sample Bank of Anthos site can run beside it, but its official payment path is not yet controlled by this gate. The browser supplies generated test screenshots plus their text transcription. Independent OCR is not yet present.

## 2. Evidence protocol — next

1. Define exact warning templates and customer-choice fields. Sign a protection receipt covering the order, decision, displayed warning, choice and outcome.
2. Add registered-device acknowledgement without claiming that a device signature proves human understanding.
3. Add an append-only Merkle log, inclusion/consistency proofs and a separately keyed witness; verify log and receipt changes in independent tests.
4. Reconcile every completed test payment against a decision ID so missing records cannot be hidden by a valid-looking log.

Acceptance: tampering with the warning, choice, order, decision, receipt or log history is detected; unsigned or missing evidence is visibly unverified.

## 3. Stronger bank and document integration

1. Add independent image OCR (Google Cloud Vision or Document AI after project access) and ground model-extracted values against OCR spans.
2. Put the gate in front of an authorised Bank of Anthos transfer path, or a bank-controlled processor adapter, rather than only CARAPACE's local ledger.
3. Replace local API keys and signing files with bank identity and managed KMS keys; define privacy retention, consent and failure policies.
4. Build a labelled adversarial corpus including mismatched payee, amount, refund direction, low-quality images, prompt injection and benign lookalikes. Measure detection and false holds.

Acceptance: end-to-end test shows a held payment never reaches the bank's processor and an allowed test payment reaches it exactly once. Image-only values are either independently grounded or clearly unverified.

## 4. Google Cloud hackathon submission

1. Use a GCP project and available credits/billing approval to deploy the working Google-AI-powered prototype on Cloud Run or Firebase. Do not add paid services merely because they are suggested.
2. Run container and browser tests on the deployed URL; record latency, failure handling and provider mode.
3. Prepare an English public README, architecture/security limits, deck as PDF, and video under three minutes.
4. Submit before the team's binding Hack2skill dashboard deadline. The public event page currently says **18 October 2026**; the private dashboard needs the team account to confirm.

Acceptance: public repository and deployed URL show the same live two-case flow, with real Gemini provenance and no secret exposed to the browser or GitHub.
