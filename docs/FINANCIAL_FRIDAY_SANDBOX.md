# Financial Friday sandbox milestone

## Outcome

The local homepage is now the first product surface for Financial Friday. It is
an interface over the real bounded agent pipeline, not a visual mock-up.

```text
locked goal → Gemini typed plan → deterministic proof
            → hostile-plan challenges → restricted executor
            → reconciliation / signed artificial-money result
```

Open `http://localhost:8090` after starting Docker. The older operations lab is
still available at `/operations`, and the older payment-check flow is at
`/payment-check`.

## What the interface proves

- A user delegates an outcome rather than approving every internal lookup.
- Gemini can propose only schema-valid financial actions.
- The safety kernel—not the model—controls execution.
- Changed payees, excess amounts, extra data, recurring mandates, repeated
  effects and missing confirmation are independently rejected.
- Unknown provider outcomes are reconciled before any retry.
- The sandbox executor is tenant-scoped and idempotent and returns signed
  artificial-money evidence.
- The interface reports a hold as a completed safety outcome rather than asking
  the user to solve the technical problem.

## Verified runs

- Configured Gemini produced a valid one-time bill program with one successful
  model call. A previously completed goal was detected and not executed again.
- The subscription-trap comparison selected the authenticated one-time option
  instead of the highlighted recurring option; all six hostile mutations were
  rejected.
- A changed-recipient case stayed `HELD` after both allowed planning attempts;
  no money moved.
- The website health, scenario catalogue and run proxy returned valid responses.
- Full Docker result: **129 tests passed, 1 optional live Anthos database test
  skipped**.

## Scope

This milestone uses controlled fixtures and artificial money. It does not read a
real bank account, hold real credentials, move real funds or grant Gemini a bank
tool. That boundary is part of the product design, not a missing safety check.

## Next engineering milestone

Build a goal compiler that converts a short user instruction into a proposed,
human-readable mandate. The mandate must be deterministically validated and
confirmed before it becomes executable. Then replace one fixture source with an
authorised provider connector while keeping the same proof and executor layers.
