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
