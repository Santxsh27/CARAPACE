# Financial Friday — Submission Pack

Use this folder for the final demo script, evaluation results, slides and submission links. Current build status is in [Start Here](../../START_HERE.md), [README](../../README.md) and [SPEC](../../SPEC.md).

Implemented evidence: [proposal safety evaluation](SAFETY_EVALUATION.md),
[security boundaries](SECURITY_BOUNDARIES.md), and [live demo script](DEMO_SCRIPT.md).
The generated safety corpus is not a live model benchmark.
Live multimodal evidence: [document verification](../FRIDAY_DOCUMENT_VERIFICATION_1008.md),
including the initial failure, fail-closed fix and two successful safety retests.

## Demo story

Save one instruction → supply a previously unseen bill → Gemini interprets it → provider evidence grounds it → the kernel checks the plan → one artificial payment completes → repeat the request and observe no new payment. Show a recipient mismatch, a recurring offer and an unknown previous outcome.

## Completion checklist

- Latest Google Cloud URL and verified version.
- Live Google AI calls with visible model provenance.
- New input supplied during the demo.
- Correct task completed and unsafe task held.
- Measured completion, false holds, unsafe actions, latency and cost.
- Architecture, threat model, limits and provider integration roadmap.
- Repository, video and organizer-required deck/document.
- Confirmed dashboard deadline, eligibility and team details.

This pack is complete only when these artifacts and checked links exist.
