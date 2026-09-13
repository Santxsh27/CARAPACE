# Trust and safety model

## Non-negotiable rules

- Never send a PIN, OTP, CVV, password, reusable credential, or signing key to
  Gemini.
- Treat messages, webpages, QR contents, invoices, source comments, logs, and
  model responses as untrusted input.
- Use schema-constrained model output and validate it before storage or use.
- Do not let Gemini authenticate customers, sign evidence, alter a ledger,
  execute a refund, freeze an account, or deploy production code.
- Do not inject faults into production.
- Do not label a payment safe merely because no risk signal was found.
- Preserve explicit states such as `UNVERIFIED`, `PENDING`, and `NEEDS_REVIEW`.

## Evidence levels

| Level | Meaning |
| --- | --- |
| Context checked | User-shared context was analysed; advisory only. |
| Payment fields bound | A participating bank bound canonical fields to the PAC. |
| Bank posting matched | Independent bank ledger evidence matches the PAC. |
| Settlement confirmed | The relevant rail supplied authoritative final evidence. |
| Mismatch | At least one named deterministic contract failed. |
| Unverified | Required evidence was unavailable or could not be trusted. |

## Failure handling

- If Gemini is unavailable, the deterministic bank flow continues under the
  bank's last approved policy and the additional context check is marked
  unavailable.
- If evidence is delayed, show `PENDING`; do not manufacture success.
- If the verifier detects a mismatch, create an evidence case and invoke only
  bank-approved reversible containment.
- Generated patches remain isolated until all gates pass and a human approves.

