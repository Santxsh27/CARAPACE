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
- [x] HOLD cannot post; the original gate allowed an ALLOW to post one synthetic ledger row. Milestone 2B now also requires a signed browser choice for ALLOW and WARN.
- [x] Refund and bill flows are run from a plain-language browser page.
- [x] Full Docker regression suite passes, including new gate tests.

Milestone 1 stops at a **CARAPACE local synthetic ledger**. The sample Bank of Anthos site can run beside it, but its official payment path is not yet controlled by this gate. The browser supplies generated test screenshots plus their text transcription. Independent OCR is not yet present.

## 2. Evidence protocol — local integrity slice implemented; independent assurance next

1. [x] Sign the exact issued warning, order digest, verdict, policy context and input hashes in a decision protection record. Sign synthetic posting separately; commit each with its corresponding gate action.
2. [x] Add a separately keyed **local** witness tree and inclusion proof. Verify bundles using externally supplied public keys; corrupt latest witness history fails the next write closed.
3. [x] Add a browser-signed test-device `PROCEED`/`CANCEL` record, bound to the exact payment and warning. HOLD remains non-overridable; posting now requires signed PROCEED. Development bank-key enrollment does not prove production customer identity or human understanding.
4. [ ] Add consistency proofs, externally monitored checkpoint history and an independently operated witness. Current inclusion proofs establish membership in one signed checkpoint only.
5. [ ] Reconcile every completed test payment against a decision ID so missing records cannot be hidden by a valid-looking log.

Current acceptance: warning, choice and receipt tampering or a corrupted current witness head is detected in tests, and the relevant local write rolls back. Full milestone acceptance still requires production-grade device enrollment, independent witnessing, consistency and coverage checks. See [Milestone 2A](MILESTONE_2A_REPORT.md) and [Milestone 2B](MILESTONE_2B_REPORT.md) reports.

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
