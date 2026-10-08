# Financial Friday household bill journey

Financial Friday should help a household answer three questions: **What is due? Is this bill safe and expected? What happened after I acted?** The product should save time on routine bills while making unusual ones easier to understand. The current prototype uses artificial money and an enrolled test provider; customer value is demonstrated through that boundary, not through a claim of bank access.

## Customer promise

This is one journey within the broader **Understand / Handle / Protect / Resolve**
product. My money supplies a read-only reserve/bill/shortfall overview; it does not
replace statements or imply access to every financial account. Bill execution is
the first supported adapter. The separately shaped bank/biller resolution kernel
is tested but provider reconciliation execution is not connected yet.

“Show me the bills that matter, handle the ordinary ones within my rules, and stop when a detail needs my attention.”

A successful experience ends with a bill-specific outcome: paid in the sandbox once, waiting for explicit approval, or held with a clear reason and next step. Friday must distinguish a message’s claim from the provider’s record and a submitted payment from a confirmed outcome.

## Journey to demonstrate

1. **See the task.** A household bill arrives as a message or document. Friday shows the biller, reference, due date, amount, recipient and source before proposing action. The customer can review or correct the input.
2. **Compare expectations.** Friday checks the enrolled provider record, the previous bill amount when available, the saved automatic limit and protected balance. A changed recipient, unexpected increase or recurring request stops before payment. An increase is a review signal, not a fraud verdict.
3. **Act inside permission.** A routine one-time bill may complete automatically only when the saved artificial-money permission allows it. Otherwise Friday presents the exact payment details for explicit approval. The model cannot raise limits or change the payee.
4. **Know the outcome.** Friday shows whether one artificial payment was recorded, whether an earlier operation was reconciled, or whether the outcome remains unknown. Reopening Activity never repeats the operation.
5. **Resolve the exception.** For a changed recipient or unusual amount, the next step is to verify with the biller through a known channel. Do not send the customer to a link or number contained only in the suspicious message.

## Implemented customer examples

The home screen lists upcoming artificial provider bills for review. Selecting one prepares a request but never submits payment. The Bills screen can create a fresh artificial provider record and editable message for three cases: a routine bill, an unexpected increase, and a changed recipient. Preparing an example does not submit payment. The result shows due date and previous amount. A configurable bill-increase threshold defaults to 30%; exceeding it holds the task, including at the final execution check. These records remain same-operator demo data, so they are not proof of an independently authenticated biller.

## Next build priorities

1. **Independent biller sandbox.** Move bill publication behind a separately authenticated simulator or an authorized provider sandbox. Demonstrate a message-payee swap and a provider-side change between planning and execution. Record the source identity and fetch time.
2. **Bill status.** Connect the read-only home list to actual Friday outcomes so a card can say due soon, handled or needs review. The current list shows provider records only; it does not infer whether a bill was paid.
3. **Payment review and handoff.** For customers without a connected bank, offer a safe, read-only summary of the verified bill so they can pay in their own banking app. Do not call that bill “paid” until provider or bank confirmation is available. Keep sandbox execution as the clearly labelled end-to-end demonstration.
4. **Useful explanations.** Put the customer decision first: “₹2,487 due in three days; 55% above the previous bill; no payment submitted.” Put model calls, mutations and signature details in expandable evidence.
5. **Held-out evaluation.** Compare Friday with rules-only processing on unseen routine, ambiguous and hostile bills. Report valid completion, false holds, unsafe actions allowed, duplicate effects, unavailable outcomes, latency and cost. A bill increase alert should be measured for usefulness, not presented as fraud-detection accuracy.

## Three-minute demo

Start with a routine bill and show one bounded artificial payment. Reopen it to show no repeat. Then use the unexpected-increase example to show a bill-specific hold and the customer's next step. Finally, use the changed-recipient example to show why source text cannot override the enrolled biller record. End with the honest boundary: real bank and biller access requires authorized connectors; the prototype demonstrates the customer workflow and its safety controls with synthetic data.
