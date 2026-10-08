# Message interpretation repair — October 8, 2026

## Change and trust boundary

The previous live evaluation found one false hold: Gemini labelled a request to
protect the saved reserve as embedded instruction. The extraction prompt now
uses explicit contrasting examples: respecting existing limits/reserve is ordinary
financial language; a request to ignore limits, bypass checks or disclose secrets
is suspicious, even if preceded by a benign safety request. The model still only
extracts facts. No suspicious flag is cleared by post-processing, no financial gate
is relaxed, and saved permission/provider records remain authoritative.

Understanding failures now emit sanitized server diagnostics: fixed category,
attempt number, allowlisted numeric provider status and retry decision. No exception
text, validation input, financial message, credential or traceback is logged by
this diagnostic. Existing retries remain limited to two read-only understanding
attempts for selected transient statuses. Payment POSTs are not retried.
This improves diagnosis of a future 503; it does not establish the cause of the
earlier 503 or guarantee provider availability.

## Candidate verification

- Application suite: 192 tests, 191 passed, one optional Anthos skip, 12.230 seconds.
- Nine offline tooling tests passed. A new application regression verifies that
  failure diagnostics exclude a deliberately sensitive exception message.
- Candidate prompt: 24/24 live Vertex extraction checks passed, using 12 artificial
  cases twice with fresh bill references. Exact reference, amount, recipient,
  recurrence and presence/absence of suspicious instructions were checked.
- Cases included the previous eight, two benign paraphrases and two mixed
  benign/hostile instructions. All six hostile observations were flagged; benign
  requests to retain existing limits/reserve were not flagged.
- `tools/evaluate_prompt_candidate.py` uses the native Google Gen AI SDK and the
  same Python planner as the service. It takes an authorized access token on stdin,
  never argv or logs. It has no provider or payment execution interface.
- These are hand-authored regression cases, some explicitly represented in the
  prompt; they are not held-out fraud accuracy or a full-payment benchmark.

Cloud Build `a763cef1-a4af-49f1-a687-60dc32dcbcb1` succeeded. The two-file overlay
was built on the previous immutable image, excluding unrelated UI changes:
`sha256:5389f1b4f459048053b6d43469950eee9d370474b7d1b0d43994cd412aa8a6c6`.
The same two files were applied to the local API image. Local API health returned
version 0.13.2 and the Friday UI returned HTTP 200; named data volumes were retained.

The earlier 14/16 live results remain in LIVE_MESSAGE_EVALUATION_1008.md and are
not replaced by a selectively passing sample.

## Private full-API verification and release

Revision `financial-friday-api-message1008` was deployed with zero normal traffic
before verification. Fresh reference `EVAL-BC598D6AF677`, INR 3,001: all eight cases
passed state/reason, exact extraction and live-provenance checks. Three benign
requests were READY above the limit; five problematic requests were ATTENTION.
The prior false-hold wording returned no suspicious instructions. Each used one
live Vertex attempt, no run/payment, and left the balance unchanged. Sample API
median 2.101 seconds, maximum 2.262 seconds: not a p95 or cost claim.

Cross-revision replay of `doc-27c031b4ab95230a7492295c` returned ALREADY_COMPLETED,
with existing key `09fa77671c19ebc6` and operation
`ffpay_d4742aa063bd46319dca860bec92b72d`. Balance remained 4,250,600 minor units
(INR 42,506), with no new debit or model call. Anonymous access was rejected.

After verification, traffic was promoted to 100% on message1008; previous diagnostic
tags were preserved. No permission, reserve, enrollment or IAM changed. The targeted
false hold is addressed in these checks, not guaranteed eliminated for all language.
The earlier 503 remains undiagnosed. Broader unseen inputs, reliability, judge access,
deadline confirmation and video/deck remain necessary.

The promoted normal API route was checked again: healthy version 0.13.2,
transactional Firestore, the same no-AI/no-debit receipt replay and anonymous-access
rejection. The website gateway and UI were not redeployed; they use this API route.

The AI integration skill was inspected; the existing Python/native Google SDK
stack was retained rather than introducing a TypeScript SDK or another gateway.
