# Real-input release — October 10

## What changed

The existing Gemini bill-image/PDF interpreter remains in place. An enrolled
artificial biller is still necessary for a sandbox payment, but no longer the
only useful experience: My money displays saved interpretations separately and
offers a new read-only bank-statement CSV analyzer.

CSV analysis accepts previously unseen user rows, computes exact integer-paise
cash flow, monthly totals, largest outgoing entries and exact repeated-row review
candidates. It never calls an LLM for arithmetic, trusts a recipient, submits a
payment, changes account balances or removes suspected duplicates. Gemini is
still responsible for existing document understanding and bounded task planning;
this feature does not falsely claim to be an additional AI call.

## Using it

1. Open My money on the local Friday website.
2. Export an INR bank statement and normalize its CSV column names to
   `date,description,debit,credit`. Debit/credit values are rupees, not paise.
3. Remove unnecessary account identifiers and personal information.
4. Select the CSV and consent to temporary Friday server processing.
5. Analyze, review the results, and clear them when finished.

The application does not persist the raw CSV or analysis result. Results remain
in the current browser page until cleared/reloaded. Files are not sent to Gemini.
This is not a direct bank feed; bank-specific CSV formats may need normalization.
An optional currency column must say INR. Mixed currencies are rejected.

## Verification evidence

- Full native suite: 249 tests run, 248 passed, one optional Anthos test skipped.
- Arbitrary unseen amounts, Indian grouping, monthly splits and repeated rows tested.
- Malformed dates, dual debit/credit, invalid amounts, extra fields, unsupported
  currency, oversized statements and over 5,000 rows rejected without partial totals.
- API requires tenant authentication; before/after mandate and balance remain identical.
- Local browser → web proxy → authenticated API → deterministic parser → UI verified.
- Browser test used the clearly labelled `examples/statement-format.csv`, not the
  owner's personal data: five rows, ₹45,300.50 in, ₹14,934.50 out, net ₹30,366.00.
  Two matching grocery entries remained included and were labelled review candidates.
- JavaScript syntax checks and existing read-only workspace rendering tests passed.

## Release boundary

Implemented in the existing repository and rebuilt local Docker API/web containers.
The existing Cloud Run release has not yet been upgraded with these additions.
No IAM permissions, bank integrations, subscriptions or cloud billing were changed.
