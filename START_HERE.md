# Financial Friday — Start Here

Working folder: `/Users/santosh/Desktop/CARAPACE`. The product is Financial Friday; Python module names retain CARAPACE for compatibility.

## What it does

Save an instruction such as “Handle verified bills up to ₹3,000, protect ₹10,000 and never create subscriptions.” Gemini reads a new message, QR text, transcript, bill photo or PDF. Friday matches it to an enrolled provider record, creates a restricted plan, verifies the plan against your limits, then completes one artificial-money payment or explains why it stopped. It checks uncertain previous outcomes before retrying.

## Run and explore

1. Start Docker Desktop and open this folder in Visual Studio Code.
2. Run `docker compose up -d --build api anthos-demo`.
3. Open http://localhost:8090 for Friday and http://localhost:8080/docs for the API.
4. Open **My rules** to inspect/save standing permission. Open **Bills → Demo provider setup** to publish a fresh artificial bill.
5. Use **Bills** for a new message or **Documents** for its image/PDF.
6. Friday opens a separate **Run** screen. Change the amount or recipient and check that it stops.
7. Use **Safety lab** for controlled subscription/timeout cases, and **Activity** to reopen existing receipts without paying again.
8. Home's **Your sandbox briefing** counts recent recorded outcomes, not all-time totals. Use Activity search and outcome filters to find a receipt. **How Friday works** explains the journey; Escape closes help and `/` focuses the home command outside text fields.

`docker compose stop` preserves the named data volume. Keep `.env`, credentials and signing keys out of GitHub.

## Implemented capabilities

- Typed goals, provider evidence and Gemini action programs.
- Vertex AI and Gemini Developer API adapters, plus a labelled local comparison.
- New message, QR-text and transcript interpretation; PNG/JPEG/WebP/PDF interpretation with quotations.
- Saved limits, reserve protection and opt-in automatic artificial payments.
- Independent checks for recipient, amount, fees, currency, recurrence, privacy and action order.
- Restricted execution, tenant isolation, idempotency and signed receipts.
- Plan repair, six hostile mutations and reconciliation before retry.
- Background sandbox inbox with bounded retries and claim recovery.
- Optional Firestore storage for instructions, bills, signals, cases and run evidence.
- Friday UI, API docs and automated tests.

Local SQLite mode runs the complete artificial-money journey. Version 0.13.2 includes an atomic Firestore payment journal and receipt-first replay: an already-paid bill is confirmed without another AI call or debit. The Mumbai database and persistent signing keys are provisioned; cloud verification and release results are recorded in docs/CLOUD_RUN.md. Real UPI, GPay, SMS and bank accounts are not connected.

## Technology inventory

Python, FastAPI, Pydantic, SQLite, cryptography/Ed25519, Google Gen AI SDK, Google Firestore client, Docker Compose, HTML/CSS/JavaScript and browser speech transcription. The repository retains earlier Bank of Anthos artificial-bank work.

Google Cloud includes Vertex AI, private Cloud Run, Artifact Registry, Cloud Build, service identity, Secret Manager and budget alerts. The API is version 0.13.2, using Gemini 3.5 Flash-Lite and transactional Firestore. Real owner Google login through IAP and a fresh ₹2,487 browser-to-cloud bill journey now work; replay reused the receipt without another debit, and a changed recipient was held. Access is owner-only. Cloud Tasks and native Gemini Live voice remain planned. BigQuery, Document AI, ADK and Agora are not implemented.

## Verification

Version 0.13.2 plus the cloud gateway and multi-screen UI: 186 tests ran, 185 passed, one optional Anthos test skipped. Tests include concurrency, durable restart, corrupted receipts, replay while AI is unavailable, identity/tenant isolation, same-origin protection, read-only briefing/filtering and no automatic gateway payment retry. Browser evidence is in `docs/FRIDAY_BROWSER_VERIFICATION_1008.md` and `docs/FRIDAY_MULTISCREEN_1008.md`.

```bash
docker compose run --rm --build -e CARAPACE_TEST_ANTHOS_BRIDGE_ENABLED=false api python -m unittest discover -s tests
```

## Remaining submission work, in order

1. Confirm dashboard deadline/eligibility and explicitly arrange judge access; record the live story in docs/submission/DEMO_SCRIPT.md.
2. Verify live document uploads and a second enrolled cloud identity; owner sign-in and new-bill execution already work.
3. Connect an independently authenticated sandbox provider.
4. Connect durable orchestration if promising continuous background operation.
5. Measure unseen-case completion, unsafe actions, false holds, latency and AI cost against plain Gemini.
6. Finish demo video, deck, architecture, limitations and submission links.

Confirm deadline and eligibility in your Hack2skill dashboard. Production launch additionally requires authorized providers and security/compliance review.

## Folder map

- `README.md`: public overview, architecture and running instructions.
- `SPEC.md`: technical and product contract.
- `docs/CLOUD_RUN.md`: cloud deployment status.
- `docs/submission/README.md`: submission checklist.
- `src/carapace_ai`: Gemini integrations.
- `src/carapace_core`: rules and models.
- `src/carapace_api`: API, storage and executor.
- `src/carapace_integrations`: UI and provider/Anthos adapters.
- `tests`: automated verification.
