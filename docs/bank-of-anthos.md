# Bank of Anthos integration

## What is connected now

The local demonstration uses Google's published Bank of Anthos `ledger-db`
container at version `v0.6.10`, pinned to its immutable image digest. Bank of
Anthos describes itself as a sample HTTP-based banking application composed of
independent services that run on Kubernetes. The complete upstream application
contains a frontend, user and contacts services, ledger writer, balance reader,
transaction history service, load generator, and two PostgreSQL databases.

CARAPACE currently runs the **official ledger slice**, not that entire
Kubernetes application. This is intentional: it creates a real external-system
boundary on a small laptop without requiring a paid GKE cluster or pretending
that example JSON came from a bank.

Upstream references:

- [Bank of Anthos repository](https://github.com/GoogleCloudPlatform/bank-of-anthos)
- [Official Kubernetes configuration](https://github.com/GoogleCloudPlatform/bank-of-anthos/blob/main/kubernetes-manifests/config.yaml)
- [Official ledger database schema](https://github.com/GoogleCloudPlatform/bank-of-anthos/blob/main/src/ledger/ledger-db/initdb/0_init_tables.sql)
- [Official LedgerWriter transaction model](https://github.com/GoogleCloudPlatform/bank-of-anthos/blob/main/src/ledger/ledger-writer/src/main/java/anthos/samples/bankofanthos/ledgerwriter/entities/Transaction.java)

## What one click actually does

1. The demo creates a fresh CARAPACE Payment Assurance Contract for a $49.99
   artificial-money transfer.
2. A controlled test harness inserts the transfer into Bank of Anthos's
   append-only `transactions` table and captures the returned transaction ID.
3. The adapter reads that exact row back from PostgreSQL and converts it to
   CARAPACE execution evidence.
4. The deterministic verifier returns `MATCH` because one approved payment
   produced one debit with the expected amount and payee.
5. The harness simulates a faulty retry by adding a second transaction row.
6. The adapter reads both explicitly bound transaction IDs. CARAPACE returns
   `MISMATCH` and opens a persisted evidence case for a duplicate debit.

Start it with:

```bash
docker compose --profile anthos up --build anthos-demo
```

Then open [http://localhost:8090](http://localhost:8090) and press **Run the
live safety test**. Docker must remain running. The first start can take longer
because the official image is `linux/amd64` and Apple-silicon Macs emulate it.

Stop it with `Control+C`. The artificial Anthos ledger and CARAPACE evidence
are retained in separate Docker volumes.

## Trustworthy mapping

| Bank of Anthos ledger field | CARAPACE meaning |
|---|---|
| `transaction_id` | Authoritative external entry ID |
| `from_acct` | Debited account reference |
| `to_acct` | Counterparty/payee reference |
| `amount` | Amount in minor units |
| `timestamp` | Ledger write time |
| returned ID captured by trusted harness | Binding to the Payment Assurance Contract |

Two facts are supplied by the adapter policy rather than the upstream table:

- **Currency:** the Bank of Anthos ledger does not store a currency column. The
  current demo uses USD, matching the sample application's dollar-oriented UI.
- **Logical payment ID:** LedgerWriter uses a request UUID for duplicate-request
  handling, but the transaction entity marks that UUID as non-persistent. The
  demo therefore binds the `RETURNING transaction_id` value to the contract at
  the trusted test boundary. It never guesses by amount or timestamp.

The evidence lifecycle stops at `ACCEPTED`. A row in this ledger proves that a
posting exists; it is not authoritative evidence of an external payment rail's
final settlement. CARAPACE therefore leaves `settlement_reference` empty.

## Production upgrade path

The direct insert method is named `insert_controlled_test_transaction` and is
only for artificial-money fault injection. In a real bank:

- CARAPACE receives a trusted processor/event reference or instrumented request
  binding;
- the ledger connector is read-only;
- raw bank credentials and production data remain in a bank-controlled private
  runner;
- only the minimum evidence required by the contract leaves that boundary;
- CARAPACE observes transactions but does not write, move, refund, or correct
  real funds.

The later full Bank of Anthos milestone will replace the controlled writer with
the upstream LedgerWriter and supporting services on Kubernetes. The
deterministic verifier and adapter mapping introduced here remain usable.
