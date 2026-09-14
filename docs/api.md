# Assurance API

The API is the first real integration boundary for CARAPACE. A participating
bank tenant registers what its customer confirmed, submits independently
collected execution evidence, and receives an exact `MATCH` or `MISMATCH`.
Mismatches automatically become evidence cases.

## Start the service

```bash
docker compose up --build api
```

Useful URLs:

- Interactive OpenAPI: `http://localhost:8080/docs`
- Readiness: `http://localhost:8080/health/ready`
- Alternative documentation: `http://localhost:8080/redoc`

Health endpoints are public. Every `/v1` endpoint requires both headers:

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

## Security properties already enforced

- Unknown or incorrect credentials receive `401`.
- Record lookup always includes the authenticated tenant ID.
- Extra JSON fields and malformed identifiers are rejected.
- The PAC request hash is recomputed before storage.
- The URL contract ID must match the evidence contract ID.
- Run IDs cannot be silently overwritten.
- A mismatch and its evidence case are committed atomically.

The API does not yet authenticate real bank workloads, verify KMS signatures,
or ingest production ledger events. Those are explicit adapters planned after
the hackathon vertical slice, not behaviours hidden behind a mock success state.
