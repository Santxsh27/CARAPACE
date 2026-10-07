# Financial Friday — live demo script

## Before recording

Open the protected Cloud Run website using the enrolled owner's Google account. Do not show credentials, OAuth downloads, Secret Manager values or personal bills. This demo uses artificial funds and a development test provider. A real bank integration is not claimed.

Use a fresh bill reference each time. In **Demo provider setup**, publish a TN Power test bill with a new reference, amount ₹2,487 and payee `tnpower@upi`. These are explicitly test-provider records, not records fetched from the real utility. Keep standing permission enabled only for artificial one-time payments within ₹3,000, no fee, with the existing protected reserve.

## Three-minute story

**0:00–0:25 — The problem.** “An assistant that understands a bill is useful only if it can complete the allowed task without treating the bill as permission to spend. Friday separates understanding, verified provider evidence, standing permission and execution.”

**0:25–1:15 — New input, live AI.** Publish the fresh test bill on screen, then type: “Please handle my one-time TN Power electricity bill [fresh reference] for INR 2487.00. Payee: tnpower@upi. Check the provider record before paying and protect my reserve.” Click **Handle this safely**. Wait for the actual response. Show the extracted facts, stored run, model provenance, independent checks and signed receipt. Do not claim success before the response.

**1:15–1:45 — No duplicate.** Submit the same bill again. Show **Already handled—nothing repeated**, zero new money effects and the original receipt. A cached/reconciled outcome is expected, not a new AI-generated payment.

**1:45–2:15 — A changed recipient.** Change only the payee in the message to `someoneelse@upi`, keeping the registered bill unchanged. Show the mismatch and no new payment. Friday must not silently replace the recipient or relax the standing permission.

**2:15–2:40 — Useful recovery, not just alerts.** Run **Recover after a timeout**. This is a labeled controlled scenario: the provider already processed the simulated earlier operation. Explain that Friday reconciles that outcome before any retry. It is not evidence that Friday can reverse a real bank transfer.

**2:40–3:00 — Architecture and limits.** “Gemini on Vertex AI interprets the request and proposes a typed program. Python/FastAPI checks permission and evidence; transactional Firestore commits the artificial effect and receipt; an IAP-protected Cloud Run gateway keeps credentials server-side.” Mention authorized provider connectors and durable background scheduling as remaining rollout work.

## Evidence versus aspiration

The cloud browser journey and regression suite are real evidence. A broad unseen-case evaluation, comparison with plain Gemini, per-run AI cost, native voice assistant and continuous cloud monitoring are not yet completed. Do not substitute a test count for measured fraud detection accuracy or promise a hackathon win.

## Submission gates

- Confirm the deadline, eligibility and build-window rules on the organizer dashboard.
- Decide how judges receive authorized demo access; the current site is owner-only.
- Record the actual working app, including one fresh input and one held action.
- Include README, SPEC, architecture, threat boundaries, evaluation limitations and repository link.
- Retain an offline video fallback in case Google login or AI availability delays a live demonstration.
