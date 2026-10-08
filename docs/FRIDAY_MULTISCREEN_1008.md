# Financial Friday — multi-screen experience

October 8, 2026. This is the existing application, not a disconnected visual mock.

## Flow

Friday home → Bills or Documents → dedicated Run → Activity / receipt.
My rules contains standing permission; Safety lab contains the five controlled scenarios.
Home commands transfer text to Bills without submitting or granting permission.
All existing provider, Gemini, verifier and executor APIs remain unchanged.

The flow audit identified mixed settings, input, demos and old results on one long
page. The redesign gives each screen one purpose and keeps evidence behind a
disclosure. Rounded dark surfaces, a reused animated core and short transitions
provide the requested assistant feel without fake payment progress.

## Verified locally

- Home, Bills, Documents, Activity, My rules and Safety lab navigation; browser Back.
- Only one task screen visible at a time; no horizontal overflow on the checked view.
- Activity fetched actual recorded runs. Reopened `ff_c3b789450a5d405695b1c95a9847f35e`:
  RECONCILED_COMPLETED, original outcome, zero new money effects.
- Executed controlled recipient-swap scenario `ff_f1968ef1e42944ae9fd7fa3eb93827ab`:
  HELD, zero planning calls, zero money effects, dedicated red outcome.
- New refund-message input, not a stored sample: Gemini extracted ₹5,000 and
  `stranger@upi`; missing authoritative provider evidence produced ATTENTION,
  with no payment. This does not establish broad scam-detection accuracy.
- Home inspected at normal desktop size and 390 × 844 phone viewport; temporary
  viewport restored. Reduced-motion CSS disables animations; focus outlines and
  route announcements included. Not a formal accessibility certification.
- No browser console errors in the inspected local journey.
- Full Docker suite: 183 tests, 182 passed, one optional Anthos test skipped.

Run labels turn green only for known completed backend statuses. Unknown outcomes
remain attention, not success. Client single-flight guards prevent another task
while the current task handler is running; server idempotency remains authoritative.
Opening recorded evidence uses GET only and never automatically retries a payment.

## Release and limits

The web image includes the gateway, existing UI and `friday_experience.py` through
`Dockerfile.web`. No new CDN dependency, secret, IAM grant or public access is added.
The private API and financial safety kernel are unchanged. Cloud deployment and
authenticated browser evidence are recorded below.

## Deployed cloud verification

- Cloud Build `aee109f0-0a4f-4809-abdb-bf14c9477b2a`: SUCCESS.
- Immutable web digest: `sha256:448b5ff09d62ab107d8b9897a637e376f699b546b10ad153c8fbbb32c7bcbc87`.
- Cloud Run `financial-friday-web-screens1008`: 100% traffic; IAP remains enabled
  and the existing web service identity is unchanged. Private API unchanged.
- Signed-in owner browser loaded the new Home and live Gemini readiness; Activity
  fetched actual Firestore runs through the protected gateway.
- Opened existing cloud run `ff_853200a2dfae4f4890970089539c725d` via Activity:
  COMPLETED_SYNTHETIC, one original artificial-money effect, Vertex AI model
  provenance and a dedicated green outcome. This was GET-only viewing, not a new
  cloud payment or proof of fresh execution after this UI release.
- No console errors during the inspected cloud navigation/receipt path.
- Final isolated suite: 183 tests in 13.028 seconds, OK (one skipped); generated
  JavaScript also passed Node syntax checking. Local API and UI containers healthy.

This remains an artificial-money pilot. Native Gemini voice, authorized real-bank
connectors, durable cloud scheduling, a broad evaluation and judge enrollment are
separate remaining submission/production gates. Document-screen navigation was
checked; a fresh live document upload is not claimed by this report.

## Motion and colour polish

The next presentation-only pass adds pointer-position 3D tilt (maximum 3.5°/4.5°),
layered task headings, hover light, subtle button lift/press, focus glow and active
stage shimmer. No Three.js or external CDN dependency is used: CSS perspective
plus bounded pointer-event JavaScript is sufficient for this interface.
No new AI, bank or provider feature is implied by these visual changes.

Local browser verified real mouse hover: `data-tilting=true`, rotation 1.40°/2.70°
and an actual `matrix3d` transform. Motion off removed transforms; re-enabling it
restored the preference. OS reduced motion remains authoritative. Touch devices
do not receive pointer tilt. Held and completed saved runs remain read-only;
Activity rows and the briefing/receipt surfaces use backend-derived outcome colours.
The red held screen retained zero money effects and its mismatch explanation.

Full isolated suite: 184 tests in 16.291 seconds, OK (one optional test skipped).
Generated JavaScript syntax also passed. Cloud Build
`89b3b452-8919-4109-af60-cc8c0aa3e2d9` succeeded with web digest
`sha256:9875bd4ac219b9c2d3aaddeb8ff35b45677657cf1f2d97d67152fe237e2102d3`.
Revision `financial-friday-web-motion1008` serves 100% traffic with IAP still enabled.
Signed-in cloud navigation fetched Activity and reopened held run
`ff_04a4490d13a14fa1bff69696ca465809`: red result surfaces, original mismatch reason,
zero original money effects, no new payment submitted and no browser console errors.
The Product Design brief kept the existing screen structure and added interaction
feedback rather than rebuilding the app. The verification story was Activity →
authenticated gateway GET → existing Firestore run → coloured outcome, with local
pointer and display-preference checks kept separate from financial execution.
