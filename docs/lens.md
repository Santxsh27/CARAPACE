# CARAPACE Lens

Lens is the consumer entry point for **Check before you pay**. It accepts the
surrounding message and a decoded UPI payment URI, then separates two jobs:

1. an intent provider extracts what the message appears to promise;
2. deterministic code parses the real UPI fields and applies named
   contradiction rules.

This separation is the security boundary. Gemini can understand phrases such
as “we are refunding you,” but it cannot rewrite the payee, amount, direction,
or final CARAPACE decision.

## Working example

```text
Message: ABC Support says it will refund INR 4,999 and asks for a UPI PIN.
UPI URI: upi://pay?pa=rktraders@upi&pn=R%20K%20Traders&am=4999&cu=INR

AI/local extraction: RECEIVE_EXPECTED, INR 4,999, ABC Support
Canonical URI:       SEND, INR 4,999, R K Traders
Deterministic result: STOP
```

The result names the exact reasons: direction contradiction, payee identity
contradiction, and PIN-to-receive deception. It does not output a mysterious
fraud percentage.

## Run the local no-cost mode

The Docker configuration defaults to `CARAPACE_AI_PROVIDER=local`. This uses a
small deterministic extraction fixture and returns provenance
`mode=LOCAL_RULES`. It makes the complete workflow reproducible with no cloud
account and never pretends to be Gemini.

```bash
curl -s http://localhost:8080/v1/lens/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "message_text": "ABC Support: We are refunding INR 4,999. Enter your UPI PIN now.",
    "payment_uri": "upi://pay?pa=rktraders@upi&pn=R%20K%20Traders&am=4999&cu=INR"
  }'
```

## Use Gemini on Vertex AI

The same endpoint can use Gemini without changing the deterministic policy:

```text
CARAPACE_AI_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
CARAPACE_GEMINI_MODEL=gemini-3.6-flash
```

## Use the Gemini Developer API free tier

During development, the same hardened boundary can call Gemini through Google
AI Studio without waiting for event Cloud credits:

```text
CARAPACE_AI_PROVIDER=gemini
GOOGLE_API_KEY=your-local-ai-studio-key
CARAPACE_GEMINI_MODEL=gemini-3.6-flash
```

Put these values in an untracked `.env` file. The API key must never appear in
browser JavaScript, Git history, screenshots or logs; Docker passes it only to
the backend API. AI Studio and Vertex use the same strict schema and
deterministic reconciliation, so moving to Vertex later is configuration—not a
product rewrite.

Use Application Default Credentials locally or a least-privilege service
identity on Cloud Run. Do not commit credential files. Vertex mode fails closed
if Gemini is unavailable; it does not silently label local rules as AI.

### Safe live setup

CARAPACE is intentionally **local-first**: the running Docker demo stays on
the no-cost fallback until an operator deliberately configures a Google Cloud
project. To enable live Gemini, the project owner must enable Vertex AI,
ensure billing and model access are available, and authenticate using their own
Google identity. Locally, that normally means `gcloud auth application-default
login`; on Cloud Run, use the service's attached least-privilege identity.

Set the four variables above in your local environment or deployment secret,
then restart the API. Never mount, paste, or commit a service-account key into
this repository. Confirm the selected mode at:

```bash
curl -s http://localhost:8080/v1/ai/status
```

`VERTEX_CONFIGURED` means the API selected the Vertex adapter; the first Lens
request proves that the configured identity can actually call the model. If
that call fails, Lens returns an explicit unavailable result rather than
silently switching to local rules. The Control Room shows the same mode and
model beside the Lens demo.

The Vertex adapter uses:

- a system instruction that treats message content as untrusted data;
- temperature zero;
- a strict JSON schema;
- Pydantic validation;
- credential redaction before the model boundary (OTP, PIN, CVV, password and
  card-number values are removed, while the surrounding safety warning stays
  available);
- provider/model/mode provenance in every response;
- deterministic reconciliation after model output.

## Current and next boundary

Implemented now:

- text story input;
- decoded `upi://pay` and `upi://mandate` input;
- user-selected QR image decoding in supported Chromium browsers;
- structured local or Vertex intent extraction;
- exact amount, direction and payee parsing;
- direction, amount, identity, PIN and pressure findings;
- `ALLOW`, `CAUTION`, `STOP`, or `UNVERIFIED` decisions;
- beginner-facing Control Room workflow and API tests.

Next:

- optional live-camera QR capture with an explicit permission prompt;
- Document AI invoice extraction;
- Web Risk signal ingestion;
- evidence spans and evaluation dataset;
- rate limiting, abuse controls and consented retention;
- bank-canonical payee resolution through PayShield.

An `ALLOW` result means only that the named checks found no contradiction. It
is never a guarantee that a recipient is honest.
