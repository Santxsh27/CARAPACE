# Friday task-first UX — October 10

## Audit scope and findings

Current-run screenshot audit of Home and My money, followed by implementation
and browser checks. References were official Google Pay bill-payment help and
Paytm's bill-payment guide, not their private mobile applications. No claim of
having audited every competitor or full WCAG compliance is made.

1. **Home, before: overloaded.** Seven navigation choices, an assistant command,
   four capability cards, sample household records and engineering activity
   compete with the user's task. Strength: task buttons and scope labels exist.
2. **My money, before: overloaded.** Upload forms, personal inputs, artificial
   balance, commitments, capability descriptions and technical limits form one
   long page. The repeated explanations obscure the useful action. Strength:
   imported information is distinguished from bank evidence.
3. **Home, after: focused.** Three task cards; everyday navigation is Home,
   My money and Activity. Settings, documents, bills and safety tests remain
   reachable through More. Demo bills and briefing are collapsed.
4. **My money, after: focused.** Choose Review spending or Saved inputs. A
   separately labelled demo wallet remains optional. Uploaded statement results
   replace the form; totals and review candidates are visible, while monthly
   breakdowns and processing details are expandable.
5. **Task outcomes: simplified.** Outcome summary first, engineering evidence
   collapsed. Original approval handlers are retained, with exact artificial
   amount and recipient visible outside the engineering panel.

## Safety and accessibility boundaries

- Same authenticated API and original execution/approval handlers.
- Statement processing consent remains explicit and visible before upload.
- Artificial-money and no-bank-connection labels remain visible.
- Native details/summary controls allow keyboard-accessible disclosure.
- Existing focus styling, labelled inputs and reduced-motion preference retained.
- Narrow-screen styles added, but device/assistive-technology coverage remains
  limited; screenshots do not establish full accessibility compliance.
- No new bank connector, automatic financial permission or cloud IAM change.

## Verification

Full native suite: 253 tests run, 252 passed, one optional Anthos test skipped.
Includes generated JavaScript syntax, existing backend/financial tests and
additional checks that the simplified layer retains consent and approval.
The approval presenter is also executed in a Node test to confirm the canonical
amount and recipient stay visible and stale approval buttons are removed.
Local API and web containers rebuilt without resetting stored records.
Browser statement upload used explicitly labelled example rows, not personal data.
Verified the input-to-results transition, clearing results, return navigation,
and loading saved inputs in their separate view.
Existing cloud release remains unchanged; this UI update is local only.

## Current-run captures

Screenshots are temporary audit artifacts on this Mac, not committed financial data:

- `/private/tmp/friday-ux-before-home.png`
- `/private/tmp/friday-ux-before-money.png`
- `/private/tmp/friday-ux-after-home.png`
- `/private/tmp/friday-ux-after-money.png`
- `/private/tmp/friday-ux-after-statement.png`
