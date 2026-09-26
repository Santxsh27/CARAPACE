# CARAPACE API

The primary v3.1 path is pre-payment protection. A bank-authenticated local
gateway signs the payment details, evaluates customer-supplied context, and
requires the resulting decision before it can insert a synthetic transfer.
The earlier post-payment assurance API is retained as legacy engineering work.

## Milestone 1 preflight sequence

All three write calls require the tenant and API-key headers shown below.
The browser at `http://localhost:8090` calls them server-side, so it never
exposes the key in JavaScript.

1. `POST /v1/preflight/orders` with ten-digit `payer_account` and
   `payee_account`, `payee_display_name`, positive integer `amount_minor`,
   `currency: "INR"`, and `reference`. The response contains the canonical
   envelope and a bank-development-key Ed25519 signature.
2. `POST /v1/preflight/orders/{order_id}/evaluate` with `context_text` and
   optional Base64 PNG/JPEG/WebP screenshot plus `image_mime_type`. It returns
   `ALLOW`, `WARN`, or `HOLD`, reason codes, a customer message, actual AI
   mode, `live_model_called`, and a bank-signed decision protection bundle. A
   provider error is an explicit `HOLD`. The bundle records what warning was
   **issued**, not proof that a customer saw or understood it.
3. `POST /v1/preflight/orders/{order_id}/submit` with the stored `decision_id`.
   The gateway rechecks both signatures, tenant, expiry and decision in one
   SQLite transaction. `HOLD`, unresolved `WARN`, changed, expired and replayed
   orders cannot post. An `ALLOW` posts one local synthetic transfer row and
   atomically appends a separately signed synthetic-posting protection bundle.

Each protection bundle contains the bank-signed record, a witness-signed tree
head, and a Merkle inclusion path. `GET /v1/preflight/receipts/{receipt_id}`
returns the current proof for the authenticated tenant. `GET
/v1/preflight/public-keys` exposes key material for pinning in this local demo;
a verifier must obtain trusted key fingerprints through an independent channel
in a real deployment. See [protection-proof.md](protection-proof.md).

`GET /v1/preflight/orders/{order_id}` reads the signed order and decision.
`GET /v1/preflight/transfers` reads only the authenticated bank's synthetic
ledger rows. Neither endpoint is a real-money transfer integration. The Bank
of Anthos sample remains a separate artificial-money environment; its official
transfer service is not yet in the preflight gate.

## Legacy assurance API

## Start the service

```bash
docker compose up --build api
```

The first `data-init` container only grants UID `10001` ownership of the
dedicated evidence volume and then exits. The API itself still runs as the
unprivileged `carapace` user. This also repairs volumes created by older
CARAPACE builds.

Wait for this line:

```text
Uvicorn running on http://0.0.0.0:8080
```

Docker will not open a browser automatically. Leave that terminal running while
using the API, and press `Control+C` when you want to stop it.

Useful URLs:

- Interactive OpenAPI: `http://localhost:8080/docs`
- Readiness: `http://localhost:8080/health/ready`
- Alternative documentation: `http://localhost:8080/redoc`

## Easiest complete demonstration

With Docker Desktop running, this single command builds what is needed, starts
the API dependency, and performs the complete synthetic workflow:

```bash
docker compose --profile tools run --rm --build demo
```

It creates new IDs on every run, so it can be repeated without database
conflicts. Success ends with output similar to:

```text
CARAPACE DEMO RESULT
  Correct payment: MATCH
  Duplicate debit: MISMATCH
  Incident: case_... (OPEN)
  Failed rules: AT_MOST_ONE_POSTED_DEBIT, DEBIT_AMOUNT_MATCH
  Overall: PASS
```

Health, AI status and public Lens checks are unauthenticated. Bank-specific
`/v1` endpoints require both headers:

```text
X-Carapace-Tenant: demo-bank
X-Carapace-API-Key: local-demo-key-change-me
```

These values are intentionally limited to the local Compose environment. Never
copy the demo key into a hosted deployment.

## End-to-end proof

Create the customer-confirmed Payment Assurance Contract:

```bash
curl -X POST http://localhost:8080/v1/contracts \
  -H 'Content-Type: application/json' \
  -H 'X-Carapace-Tenant: demo-bank' \
  -H 'X-Carapace-API-Key: local-demo-key-change-me' \
  --data-binary @examples/payment-promise.json
```

Submit matching execution evidence:

```bash
curl -X POST http://localhost:8080/v1/contracts/pac_demo_0001/runs \
  -H 'Content-Type: application/json' \
  -H 'X-Carapace-Tenant: demo-bank' \
  -H 'X-Carapace-API-Key: local-demo-key-change-me' \
  --data-binary @examples/execution-valid.json
```

The report returns `"verdict":"MATCH"` and no case ID.

The valid and duplicate fixtures use different run IDs, so you can next submit
`examples/execution-duplicate-debit.json` to the same endpoint. The exact
verifier returns `MISMATCH`, identifies `AT_MOST_ONE_POSTED_DEBIT` and
`DEBIT_AMOUNT_MATCH`, and returns a generated `case_id`. Retrieve that case with:

```bash
curl http://localhost:8080/v1/cases/CASE_ID \
  -H 'X-Carapace-Tenant: demo-bank' \
  -H 'X-Carapace-API-Key: local-demo-key-change-me'
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health/live` | Process liveness |
| `GET` | `/health/ready` | API and evidence-store readiness |
| `POST` | `/v1/contracts` | Validate and persist a PAC |
| `GET` | `/v1/contracts/{contract_id}` | Read the tenant's PAC |
| `POST` | `/v1/contracts/{contract_id}/runs` | Verify and persist execution evidence |
| `GET` | `/v1/runs/{run_id}` | Retrieve evidence and exact verdict |
| `GET` | `/v1/cases/{case_id}` | Retrieve an automatically opened mismatch case |
| `POST` | `/v1/cases/{case_id}/analyze` | Persist AI hypothesis plus deterministic counterfactual result |
| `POST` | `/v1/cases/{case_id}/approve` | Record one human release decision and issue a passport only for verified approval |
| `GET` | `/v1/release-passports/{passport_id}` | Retrieve and cryptographically re-verify a Release Passport |

## Security properties already enforced

- Unknown or incorrect credentials receive `401`.
- Record lookup always includes the authenticated tenant ID.
- Extra JSON fields and malformed identifiers are rejected.
- The PAC request hash is recomputed before storage.
- The URL contract ID must match the evidence contract ID.
- Run IDs cannot be silently overwritten.
- A mismatch and its evidence case are committed atomically.
- ProofOps analyses are persisted before they can be approved.
- A human decision cannot be silently overwritten.
- Only a verified `MATCH` counterfactual plus explicit approval can produce a Release Passport.
- Passport tampering is detected by signature verification.

The API does not yet authenticate real bank workloads, use Cloud KMS signatures,
or ingest production ledger events. Those are explicit adapters planned after
the hackathon vertical slice, not behaviours hidden behind a mock success state.
