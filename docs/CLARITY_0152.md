# Friday 0.15.2 — colour and evidence, not additional authority

The UI keeps the same pages and original financial handlers. Violet identifies
the primary plan action; teal, violet and amber distinguish bill, document and
money tasks. Outcome colours are paired with text, never the only indicator.
Reduced-motion preferences and visible keyboard focus remain supported.

Task results now expose actual recorded planning calls, rejected proposals and
confirmed new artificial payments. A correction is shown only if a rejected
proposal precedes an accepted one and successful live-model planning is recorded.
Local rules, receipt reconciliation and evidence-only holds are labelled separately.
This exposes existing bounded plan correction; it does not add autonomous code
repair, real banking access or a novel fraud detection algorithm.

The previous scenario timer advanced labels regardless of server progress. It
has been removed. The request stays pending until returned evidence is available;
unknown outcomes cannot produce a completed execution stage. Loading a receipt
and rendering its work summary are read-only.

Validation: 265 application tests ran (264 passed, one optional skip); eleven
tooling tests passed. The new runtime presenter tests cover rejected→accepted
correction, all-rejected holds, local rules, wrong event order, missing evidence
and receipt replay. Existing execution, permission and tenant-isolation tests pass.

Competition priorities remain unchanged: clear user benefit, meaningful live
Gemini use, measured results and an accessible deployed demo. Judge access,
submission PDF and three-minute video are still required. This release alone
does not make the entry submission-complete or guarantee an award.

## Deployment evidence

Clean source commit: `0181807`. Cloud Build:
`e5abb76a-afc5-4505-95c4-6a424112da04`.
Image digest: `sha256:ad482b9aec29cbd56494f1492a7f6bbbca5f17e24e5c6e5abb10ee45538132a9`.
Both `financial-friday-api-clarity1011` and `financial-friday-web-clarity1011`
were promoted to 100% traffic after zero-traffic checks passed.

Candidate checks confirmed version 0.15.2, transactional Firestore, 13 bill
records, read-only reserve planning, unchanged balance and rejected anonymous
access. One live Vertex paid-notice interpretation returned NOT_A_PAYMENT_REQUEST
without creating a case or requesting a payment. Production connectors remain
explicitly unavailable. Private access was not weakened.

Local browser checks covered home, read-only activity→held receipt and a 390px
mobile home with no horizontal overflow. Docker tests also passed with the
optional Anthos bridge disabled for the isolated test process: 265 ran, 10 skips
because optional local tooling is not installed in the runtime image. An initial
run with application bridge settings inherited failed two tests expecting no
bridge; the test-only override resolves that without changing runtime settings.
