# Financial Friday — security and launch boundaries

## Trust model

Documents and messages are untrusted content, not payment permission. Gemini
produces typed proposals, not executable code. The deterministic safety kernel
checks identity, exact amounts, fees, recurrence, data scope and action order.
Standing permission and independent provider evidence are separate inputs.
The executor accepts only approved operations. Transactional storage and signed
receipts support replay/reconciliation; signatures prove integrity, not merchant
honesty or universal correctness.

The cloud website is IAP protected and maps the signed-in identity to a tenant
server-side. API credentials remain in Secret Manager/server memory. The private
API and existing Cloud Run service identities stay unchanged. Browser mutations
require the approved origin. Opening Activity and receipts is read-only.

## Important threats and controls

- Source prompt injection: source text is data; structured model output remains
  subject to independent checks. Model compliance alone is not a security gate.
- Recipient/amount substitution: compare the candidate against saved scope and
  provider evidence. Never silently broaden the instruction.
- Unexpected recurrence/data collection: reject recurring actions and data fields
  outside the saved scope. Friday never needs a PIN, OTP or bank password.
- Lost response/replay: reconcile the durable outcome before a repeat. A local
  database transaction cannot roll back an external bank payment.
- Tenant spoofing: server-side identity mapping and tenant-qualified storage;
  caller-supplied identity is not authority.
- Forged/corrupt receipts: verify signatures; do not let AI repair financial truth.
- Model unavailability/invalid output: stop or use an explicitly labelled local
  comparison, never pretend a live model completed the task.

## Not yet production guarantees

The current provider is an enrolled development test provider with artificial
money. It is not independent bank evidence. Authorized provider authentication,
idempotency, settlement/reversal semantics, uncertain-outcome handling and contract
tests must be implemented before real financial execution. No scraping bank logins
or bypassing app isolation is planned.

Continuous cloud monitoring, native voice, official banking/SMS connectors and
unrestricted trading are not live. Judge access needs explicit enrollment; making
the financial API public is not a shortcut. Data-retention controls, independent
penetration review, operational monitoring and applicable Indian privacy/payment
compliance review are required before a production pilot. No claim of zero fraud,
guaranteed recovery, legal certification or guaranteed hackathon selection is made.
