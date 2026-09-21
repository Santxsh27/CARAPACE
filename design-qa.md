# CARAPACE Control Room — Design QA

## Evidence

- Source visual truth: `/Users/santosh/.codex/generated_images/01a08bb7-be0c-7b52-b8d7-6822ccaa0e37/exec-0f9b09d9-9134-497d-830b-7dc74df02d25.png`
- Initial implementation capture: `/Users/santosh/Desktop/CARAPACE/docs/control-room-implementation.png`
- Verified completed-state capture: `/Users/santosh/Desktop/CARAPACE/docs/control-room-complete.png`
- Normalized side-by-side comparison: `/Users/santosh/Desktop/CARAPACE/docs/design-qa-comparison.png`
- Source pixels: 1586 × 992.
- Comparison implementation pixels: 1584 × 1024, top-cropped to 1584 × 992 for comparison.
- Browser QA viewport: 1440 × 900 at device scale factor 1.
- Comparison normalization: source fit to 1584 × 992; implementation fit/cropped to the same content size. Browser chrome was excluded.
- Compared state: source depicts the full mismatch-to-repair story; the completed-state browser capture verifies the corresponding live state.

## Full-view comparison evidence

The implementation preserves the selected design's primary hierarchy: dark spatial environment, oversized plain-English promise, one left-to-right payment lifecycle, restrained cyan/red/mint evidence flow, contextual explanation panel, human approval boundary and a slim evidence timeline. The implementation intentionally uses less decorative density than the concept image so that live evidence and controls remain readable.

## Focused region comparison evidence

The central assurance flow and right evidence panel were inspected separately in both the initial and completed states. The live payment token, duplicate-debit fault path, verified-repair state, Gemini provenance, deterministic verdict and human-approval status remain readable without requiring the lower technical evidence section.

## Required fidelity surfaces

- Fonts and typography: system UI stack preserves the mock's strong grotesk-style hierarchy, heavy display heading and compact evidence labels. No clipping or truncation was observed at 1440 × 900 or in the 927-pixel in-app browser.
- Spacing and layout rhythm: major regions align with the reference. At narrower desktop widths the evidence panel moves below the flow rather than compressing the five checkpoints.
- Colors and visual tokens: near-black navy, cool blue, cyan evidence, red mismatch and mint verification semantics match the selected direction with accessible contrast.
- Image and asset fidelity: the spatial scene is rendered as a live Three.js environment rather than a flattened mock asset. The flowing evidence tube, particle field, checkpoint depth and fault strand respond to real UI state.
- Copy and content: the implementation uses the actual Bank of Anthos `$49.99` artificial-money value instead of the concept's illustrative rupee value, preventing a misleading mismatch between the visual story and the ledger evidence.

## Findings

- No actionable P0, P1 or P2 differences remain.
- [P3] The implementation is deliberately calmer than the concept render. This improves judge comprehension and runtime performance while preserving the selected spatial design language.
- [P3] Three.js is loaded from jsDelivr with a non-3D CSS/HTML fallback. Vendoring the pinned module is a later production-hardening improvement.

## Comparison history

1. First pass: payment token overlapped checkpoint copy and the central assurance ribbon was visually too faint (P2).
2. Fix: moved the token above the copy plane, corrected its idle position, and added a state-aware Three.js assurance tube plus red fault strand.
3. Post-fix evidence: `docs/control-room-implementation.png` and `docs/control-room-complete.png` show readable checkpoint copy, visible flow, mismatch evidence and verified repair.
4. First live interaction exposed a temporary Gemini 503 under provider demand (functional P1).
5. Fix: added a truthfully labelled `LOCAL_RULES` ProofOps fallback while keeping deterministic verification authoritative.
6. Post-fix browser run completed as `VERIFIED`; a later live run used `GEMINI_API · gemini-3.6-flash` and produced `MISMATCH → MATCH` with zero captured console errors.

## Primary interactions tested

- Loaded live AI, bank, ledger and assurance statuses.
- Ran the full artificial-money payment experiment.
- Observed one correct debit followed by the controlled duplicate debit.
- Verified ProofOps reached `MISMATCH → MATCH`.
- Confirmed human approval remains required.
- Toggled ambient motion off and verified `aria-checked=false`.
- Checked the browser console and page-error channel: no errors were captured.
- Ran 54 automated backend tests successfully.

## Implementation checklist

- [x] Responsive spatial assurance flow.
- [x] Live API data rather than a prerecorded animation.
- [x] Gemini provenance separated from deterministic authority.
- [x] Honest local fallback for temporary external-model failure.
- [x] Reduced-motion and manual ambient-motion controls.
- [x] Deep evidence, Lens, Bank of Anthos, ledger and FeeShield preserved.
- [x] Browser and automated verification complete.

## Follow-up polish

- Vendor the pinned Three.js module before a production or offline judging deployment.
- Add a dedicated guided presenter mode once the final hackathon narration is written.

final result: passed
