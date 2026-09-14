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
- Scope every stored contract, run, and case to an authenticated bank tenant.
- Reject malformed or unbound contracts before they become trusted evidence.
- Use the bundled static API key only for local development. Production identity
  must use short-lived, managed credentials and bank-approved authorization.

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

## Current versus production controls

| Concern | Current executable adapter | Production target |
| --- | --- | --- |
| Tenant identity | Explicit local API key | Workload identity/OIDC plus authorization |
| Evidence persistence | Tenant-scoped SQLite | Firestore or bank-approved managed store |
| Signing | Schema and hash validation only | Cloud KMS or bank HSM signatures |
| Payment data | Synthetic fixtures | Minimized, tokenized, authorized bank evidence |
| AI | Not in the verdict path | Structured, redacted proposals outside trust gates |

The development adapter proves system behaviour, not production accreditation.
It contains no real customer funds, credentials, or banking secrets.
