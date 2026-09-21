# BFSI track and Google Cloud alignment

CARAPACE addresses the track through one connected assurance loop rather than
independent AI demos:

```text
customer context -> payment promise -> bank execution -> anomaly/mismatch
-> incident explanation -> tested repair -> permanent regression knowledge
```

## Track fit

| Track direction | CARAPACE evidence |
|---|---|
| Fraud detection | Lens finds intent-versus-action contradictions before payment. |
| Transaction anomaly analysis | Ledger Witness supplies exact contract violations; BigQuery adds population-level behavioural anomalies. |
| Document intelligence | Document AI will extract merchant, amount, invoice and account evidence before reconciliation. |
| Financial assistance | The customer receives one plain-language action and evidence, not an unconstrained chatbot answer. |
| Personalized recommendations | Bank policy can require different confirmation or review based on consented risk context. |
| Compliance automation | FeeShield versions the UPI MDR policy and creates auditable violations. |
| Risk assessment | The Assurance Fusion Engine combines semantic, document, behavioural and deterministic evidence. |

## Google Cloud implementation map

| Technology | Concrete role | Status |
|---|---|---|
| Gemini on Vertex AI | Strict structured intent extraction; later scenario, cause, patch and regression proposals | Adapter implemented; needs project credentials for live calls |
| BigQuery | Event history, benchmark metrics, fee analytics and incident cohorts | Planned next data milestone |
| BigQuery ML / Vertex AI | Unsupervised anomaly score plus a calibrated transaction-risk model; never the only blocking rule | Planned after event ingestion |
| Document AI | Invoice/statement field extraction with source evidence | Planned Lens input |
| Vertex AI Search | Retrieval over approved bank policy, prior incidents and runbooks with citations | Planned for ProofOps |
| Pub/Sub | Auth, request, processor, ledger, reversal and settlement event ingestion | Next Ledger Witness milestone |
| Cloud Run | Lens, assurance API and witness services | API is Cloud Run-compatible; deployment pending |
| Cloud SQL | Production contracts, incidents, approvals and receipt metadata | SQLite development adapter exists; migration pending |
| Cloud Storage | Redacted evidence bundles and large artifacts | Planned |
| Cloud KMS | Signed Payment Promises, Trust Receipts and Release Passports | Local signing/verification boundary implemented; KMS adapter planned |
| Cloud Build | Isolated reproduction, tests and candidate-patch verification | Planned for ProofOps |

Suggested services are used only when they improve the evidence chain. The
financial verdict remains deterministic, explainable and human-governed.

## Distinctive algorithmic contribution

The proposed **Assurance Fusion Engine** does not average opaque risk scores.
It evaluates evidence in trust order:

1. authoritative contradictions (signed payment fields or ledger invariants);
2. canonical document/payment field mismatches;
3. behavioural anomaly evidence;
4. semantic context evidence;
5. availability and freshness of every source.

The output is a response policy (`ALLOW`, `WARN`, `EXTRA_CONFIRMATION`, `HOLD`,
`REJECT`, or `UNVERIFIED`) plus a minimal evidence set explaining why. Missing
evidence lowers the assurance level instead of being treated as safety.

This architecture and its dated implementation history may support a later IP
review, but “patent-worthy” cannot be guaranteed. A proper prior-art search and
qualified patent counsel are required before making novelty claims.
