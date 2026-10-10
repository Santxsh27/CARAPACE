# Friday 0.15.0 — personal planning and visible assurance

## User value

One click on My money → Plan my bills answers which recorded bills fit above
the protected reserve, which need verification and which cannot fit. This
connects personal financial assistance to the existing guarded payment workflow
without adding a chat-only feature or changing payment permissions.

## Algorithm and boundaries

The pure planning kernel uses integer minor units and exact Pareto-frontier
dynamic programming. Its objective is lexicographic: maximise bill count on the
earliest due date, then the next date, and so on; minimise cost on equal scores.
It does not infer essentials, penalties or future income. These priorities are
explicit product policy, not universal financial advice or an invented algorithm.

The solver handles at most 32 eligible bills and 10,000 frontier states.
Truncated/ambiguous records or exceeded search bounds return no complete plan.
Signed internally paid records are excluded; receipt conflicts, unusual increases,
invalid financial fields/dates and bills above the saved single-payment limit
are separated for review. Provider data remain artificial and same-operator.

GET /v1/friday/bill-plan requires existing tenant authentication. The cloud
gateway derives the tenant from IAP and allowlists only GET. No model, payment
executor, database write or permission update is called by the planning path.
The snapshot is not atomic and the plan reserves no money. Execution still
requires the existing independent gate to recheck current records and balance.

## Google AI role

Live Gemini on Vertex AI continues to interpret unfamiliar text/images/PDFs and
propose typed, restricted payment programs. Independent code grounds provider
facts, verifies effects and exact limits, and reconciles previous operations.
This plan does not fabricate an AI call: optimisation and money arithmetic are
intentionally deterministic. The visible task journey shows actual backend
evidence, not timed success animations.

## Verification

- 80 generated eight-bill cases matched a separately written exhaustive oracle.
- Expensive-first greedy counterexample: budget 1,000; bills 800/500/500 due on
  the same date. Exact plan selects two 500 bills rather than one 800 bill.
- Earlier due date takes precedence over a larger count of later bills.
- Tests cover reserve bounds, invalid values, record ambiguity, paid exclusion,
  conflicts, unusual increases, search limits and authenticated GET routing.
- Full suite and deployment evidence are appended after runtime verification.

## Submission positioning

Keep consumer screens simple. Demonstrate a fresh bill input with live Vertex,
its independent grounding and restricted execution, a changed-recipient hold,
receipt-first replay and the personalised plan. Present actual metrics and
clearly label artificial funds. This is evidence of engineering depth, not a
guarantee of selection, a new cryptographic primitive or a world-first claim.
