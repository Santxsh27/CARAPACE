# Financial Friday build sequence

## Current increment — bounded assistant sandbox

- [x] Make Financial Friday, rather than the earlier assurance dashboard, the local homepage.
- [x] Present one locked financial goal with five controlled evidence conditions.
- [x] Connect the page to real scenario, run and saved-run API routes.
- [x] Show Gemini provenance, the typed action program, deterministic proof, adversarial checks, executor events and signed receipt.
- [x] Preserve the earlier operations and payment-check labs under separate routes.
- [x] Verify configured Gemini, idempotent replay, safe subscription selection and recipient-mismatch refusal.
- [x] Run the full isolated Docker regression suite: 137 tests pass; one optional live Anthos test is skipped.
- [x] Add saved user-authored standing instructions with explicit reserve and automatic execution limits.
- [x] Accept unseen message, QR-text and browser voice-transcript inputs through one typed ingestion API.
- [x] Ground extracted references against dynamic enrolled test-provider bills and change the outcome on contradictions.
- [x] Execute eligible artificial-money bills automatically and persist the reduced sandbox balance.
- [x] Deploy the private Cloud Run API, verify a real Vertex-planned execution, and keep fail-closed behavior on provider errors.
- [x] Move authoritative identity contradictions ahead of AI and add bounded retry for transient Vertex server errors.
- [ ] Replace fixture evidence with an authorised bill/account connector and durable cloud state.
- [ ] Replace browser speech transcription with Gemini Live native audio after cloud persistence is durable.

See [Financial Friday sandbox milestone](FINANCIAL_FRIDAY_SANDBOX.md).

## Current increment — autonomous financial operations

The 27 September direction extends the existing foundations into everyday investigation and resolution. Older checklists below describe retained components.

- [x] Bounded Gemini plans and explicit no-model comparison mode.
- [x] Evidence lookup boundary, obligation graph and exact financial constraints.
- [x] Development mandate, atomic synthetic execution, signed result and concurrency protection.
- [x] Six runnable cases, saved investigations and a plain-language homepage.
- [x] Boundary tests and reproducible local retrieval comparison.
- [x] Gemini-generated typed resolution programs with bounded correction from verifier feedback.
- [x] Independent action checks, six negative guard challenges, atomic resolution journal and signed outcome readback.
- [x] Outcome-first result screen: completed actions, outstanding obligation and next step; expandable technical evidence.
- [ ] Authorised accounting connector and document upload with grounded extraction.
- [ ] Multiple obligations and contradictory evidence; compare AI with adaptive rules on unseen cases.
- [ ] Resume interrupted investigations and move durable state out of SQLite before Cloud Run scaling.
- [ ] Configure the user's GCP identity/project and measure Vertex AI.
- [ ] Deployed demo, deck, video and authenticated dashboard deadline verification.

See [operations milestone](OPERATIONS_MILESTONE_1.md) and [research boundaries](RESEARCH_AND_DIFFERENTIATION.md).

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

## 2. Evidence protocol — local integrity and audit slice implemented; independent assurance next

1. [x] Sign the exact issued warning, order digest, verdict, policy context and input hashes in a decision protection record. Sign synthetic posting separately; commit each with its corresponding gate action.
2. [x] Add a separately keyed **local** witness tree and inclusion proof. Verify bundles using externally supplied public keys; corrupt latest witness history fails the next write closed.
3. [x] Add a browser-signed test-device `PROCEED`/`CANCEL` record, bound to the exact payment and warning. HOLD remains non-overridable; posting now requires signed PROCEED. Development bank-key enrollment does not prove production customer identity or human understanding.
4. [x] Add RFC 9162 consistency proofs and a separate monitor that retains its last signed checkpoint with a pinned witness key. This is runnable local monitoring, not yet separately operated or gossiped across monitors.
5. [x] Audit every observed CARAPACE synthetic posting against its signed decision, browser choice, posting receipt and inclusion proof. Missing or altered records fail the audit. This cannot see an outside bank payment or detect a transfer and all of its records deleted from the same database.
6. [ ] Operate the witness/monitor under separate control, share checkpoints between observers, and reconcile with a bank-owned payment rail or settlement feed.

Current acceptance: warning, choice and receipt tampering or a corrupted current witness head is detected in tests, and the relevant local write rolls back. Retained-head consistency and synthetic posting coverage are also tested. Full milestone acceptance still requires production-grade device enrollment, independent operations and outside-rail coverage. See [Milestone 2A](MILESTONE_2A_REPORT.md), [Milestone 2B](MILESTONE_2B_REPORT.md) and [Milestone 2C](MILESTONE_2C_REPORT.md).

## 3. Stronger bank and document integration

1. Add independent image OCR (Google Cloud Vision or Document AI after project access) and ground model-extracted values against OCR spans.
2. [x] Add a **test-only** bridge after the CARAPACE gate: exact-bind the confirmed synthetic transfer to one direct-insert row in Bank of Anthos's artificial-money PostgreSQL ledger. Verify the amount and account fields and make retries idempotent. This is not the official transfer service and not a production bank-owned feed.
3. [x] Commit a local delivery outbox with each synthetic posting, retry the test bridge after failure, and re-read its exact row before displaying a recovered match. This is a same-operator development recovery mechanism, not settlement assurance.
4. [ ] Put the gate in front of an authorised Bank of Anthos LedgerWriter/payment path, or a bank-controlled processor adapter, with a durable request-to-ledger reference that is not created solely by CARAPACE's test harness.
5. Replace local API keys and signing files with bank identity and managed KMS keys; define privacy retention, consent and failure policies.
6. Build a labelled adversarial corpus including mismatched payee, amount, refund direction, low-quality images, prompt injection and benign lookalikes. Measure detection and false holds.

Acceptance: end-to-end test shows a held payment never reaches the bank's processor and an allowed test payment reaches it exactly once. Image-only values are either independently grounded or clearly unverified.

## 4. Google Cloud hackathon submission

1. Use a GCP project and available credits/billing approval to deploy the working Google-AI-powered prototype on Cloud Run or Firebase. Do not add paid services merely because they are suggested.
2. Run container and browser tests on the deployed URL; record latency, failure handling and provider mode.
3. Prepare an English public README, architecture/security limits, deck as PDF, and video under three minutes.
4. Submit before the team's binding Hack2skill dashboard deadline. The public event page currently says **18 October 2026**; the private dashboard needs the team account to confirm.

Acceptance: public repository and deployed URL show the same live two-case flow, with real Gemini provenance and no secret exposed to the browser or GitHub.
