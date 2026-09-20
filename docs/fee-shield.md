# CARAPACE FeeShield — UPI MDR assurance

## Verified policy context

India's Ministry of Finance announced on 15 September 2026 that the new UPI
MDR framework applies to specified person-to-merchant transactions, not every
UPI transfer and not as a customer tax. The announced rules include:

- P2P transactions remain free at every amount.
- P2M transactions up to INR 2,000 remain free.
- eligible standard P2M transactions above INR 2,000 use 0.4% MDR, capped at
  INR 300;
- eligible P2PM small merchants receiving up to INR 1 lakh per month remain
  under zero MDR;
- railways, telecom, insurance, fuel, and agricultural inputs use a flat INR 5
  above the threshold;
- capital-market payments use 0.02%, capped at INR 300;
- MDR is borne inside the merchant ecosystem. It must not be added as a hidden
  customer charge.

The reported effective date is 15 October 2026. A production rollout must
ingest and approve the final NPCI circular rather than relying on documentation
text or an AI model.

Official source: [Ministry of Finance / PIB release](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2310586)

## Product solution

FeeShield extends the Payment Promise with a versioned charge assessment:

```text
Invoice amount
  + payment kind (P2P / P2M / P2PM)
  + verified merchant category and sector
  + transaction date
  + small-merchant eligibility evidence
  ↓
Deterministic MDR policy engine
  ↓
Customer debit = invoice amount; customer MDR = INR 0
Merchant MDR = exact allowed value
  ↓
Signed Promise → processor evidence → settlement reconciliation
```

For a standard INR 10,000 merchant purchase, FeeShield displays:

```text
Customer pays: INR 10,000
Customer MDR/platform surcharge: INR 0
Expected merchant MDR: INR 40
Expected merchant settlement: INR 9,960
Policy: india-upi-mdr-2026-10-15-v1
```

CARAPACE rejects or escalates:

- an MDR or platform surcharge added to the customer's debit;
- P2P QR codes used to disguise a merchant payment;
- an incorrect merchant category or essential-sector exemption;
- processor deductions that differ from the versioned policy;
- duplicate deduction of MDR during retry or settlement;
- repeated split payments used to evade the threshold (risk signal requiring
  invoice and time-window evidence, not an automatic accusation).

AI can explain invoices, infer a candidate merchant/sector from messy content,
and detect likely split-payment patterns. AI does not calculate or approve the
fee. The deterministic engine in `carapace_core.fee_policy` makes that decision
from bank-confirmed fields and a human-approved policy version.
