# Milestone 1 report — 25 September 2026

## Outcome

The first Payment Intent Firewall path runs locally. A bank-side API signs a synthetic payment order, Gemini analyses customer-supplied context, deterministic policy returns a decision, and a server-side gate refuses a `HOLD` before a transfer row can be written. A matching bill can pass the same gate. This is a working **artificial-money** path, not a production bank integration or a claim of comprehensive fraud protection.

## Repositioning completed first

`README.md`, the served homepage, and the new single `SPEC.md` now lead with the Payment Intent Firewall & Proof of Protection. The old duplicate-debit demonstration is no longer the landing-page or specification story. The legacy research code remains available but is not presented as the new product.

The requested search was run against these three product surfaces:

```text
rg -n -i 'duplicate.?debit|second debit|two debits|retry fault|mismatch → match' README.md SPEC.md src/carapace_integrations/anthos_web.py
```

Result: **zero matches** (exit status 1, no output). This search is intentionally scoped to the primary product surfaces; it does not claim old research modules have been deleted.

## Working path

1. The server creates an Ed25519-signed order with amount, currency, direction, recipient, tenant, expiry and nonce. The key is a local development key, not a bank HSM or Cloud KMS key.
2. The browser demo shows the customer's supplied screenshot and the bank-signed fields side by side. It sends both an image and known fixture transcription text. The image is generated test material, not a captured real scam.
3. The Gemini adapter requests structured claims with an evidence span. Deterministic checks compare the claims and supplied text with the signed fields. Model output cannot turn a definite receive-versus-send contradiction into `ALLOW`.
4. The API signs the decision. The submit operation rechecks the signatures, expiry, tenant, order binding, verdict and replay state in a transaction. `HOLD` and `WARN` do not post in Milestone 1; `ALLOW` creates one row in the CARAPACE synthetic SQLite transfer ledger for that order.
5. The page shows the verdict, plain-English reason, whether a live model call completed, and the resulting synthetic transfer ID. A configured-but-failed provider cannot masquerade as successful live AI; provider failure holds the payment.

## Verification

```text
docker compose --profile test run --rm --build tests
Ran 63 tests in 1.255s
OK
```

The Docker Compose configuration also passed `docker compose --profile anthos-full config --quiet`. The optional full sample bank remains a separate readiness issue as noted below.

The suite covers tampered signatures, tenant isolation, HOLD non-posting, one-time ALLOW posting and replay refusal, amount/payee contradiction, provider failure, and image-only uncertainty. The final browser run used live Gemini Developer API (`gemini-3.5-flash-lite`), not Vertex AI:

| Case | Live call | Decision | Gateway result |
|---|---|---|---|
| Generated refund screenshot plus fixture text: “receive ₹4,999” against bank `SEND ₹4,999` | completed | `HOLD` | `BLOCKED`; no transfer ID |
| Generated genuine bill screenshot plus matching fixture text and signed bank payee | completed | `ALLOW` | `POSTED_SYNTHETIC`; one transfer ID for that order |

The 3.6 Flash image call intermittently returned a provider 503, so the locally configured demo model was changed to 3.5 Flash Lite after live checks succeeded for both cases. The local fallback remains available and is visibly labelled. No API key is committed.

## Boundaries and open questions

- The order, decision and transfer ledger are CARAPACE-controlled local development components. The new gate does **not** yet intercept Bank of Anthos's official transfer endpoint or a real bank/UPI payment. Bank of Anthos's separate sample UI and artificial ledger are not evidence of this gate being wired in-path.
- The screenshot cases include fixture transcription text. There is no independent OCR or claim grounding for image-only amount/payee values yet; image-only context is treated conservatively and cannot auto-allow.
- The visible warning/choice receipt, device acknowledgement, separately keyed witness, inclusion proof and reconciliation are Milestone 2. Do not claim Proof of Protection is complete.
- The decision is a demo policy; a bank must own the production policy, keys, identity, data retention, and payment gateway enforcement. Local development authentication is not production-grade.
- The optional full Bank of Anthos frontend showed `anthos-balance-reader:8080` connection refused on 24 September. The balance-reader log identified missing Google Application Default Credentials and then a Cloud Monitoring bean during local startup. Local-only settings now disable cloud core/tracing/metrics auto-configuration, and healthchecks prevent a started-but-unready Java service from being treated as ready. The full sample bank has **not yet passed an end-to-end readiness check** on this Apple Silicon Docker host. Use the smaller `anthos` profile for the Milestone 1 demonstration. This is a separate sample-bank issue, not a CARAPACE gate result.
- We could not confirm the team's private Hack2skill dashboard deadline because it required sign-in. The public event page currently gives **18 October 2026** for prototype submission; the team should check its dashboard for the binding date.

## Next build step

Before claiming a full bank integration, wire the signed decision into the **actual** artificial-money transfer path or create an explicit bank-owned gateway adapter with an independently controlled key. Then add a registered-device acknowledgement and signed receipt, followed by an independently verifiable witness log. In parallel, build a labelled evaluation set and measure scam detection, false holds, latency and per-check cost. Cloud Run deployment and Vertex AI require a Google Cloud project and authorised billing/identity; none is assumed here.
