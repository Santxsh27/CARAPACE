# Friday: connected bill-handling journey — October 11

## Product decision

Keep the working engine. Do not pivot to an unbuildable universal banking agent.
Friday reduces the effort and risk of handling everyday bills: understand the
request, plan within a reserve, validate independent provider evidence, execute
only within saved authority and reconcile before reporting success. All payment
execution in this release uses artificial funds. User CSV analysis is real
read-only input processing, not a bank connection.

Google Gemini supplies semantic document/message interpretation and restricted
program generation and correction. The independent kernel checks monetary
effects and permission. The executor and journal perform actual bounded actions;
the interface never invents successful stages. Reserve planning is exact code,
not model arithmetic. That separation is necessary for a credible financial AI.

## UX audit and fixes

1. Home: readable and honest about the sandbox, but three equal tool choices hid
   the main outcome. Now one primary read-only Plan my bills action explains the
   reserve-aware journey. Existing message input remains secondary.
2. Planning: a result previously ended at totals and required retyping a bill.
   Selected rows now prepare the original bill form with exact decimal amounts.
   This never calls the checking or payment handler. Review/deferred/already-paid
   rows receive no preparation action.
3. Activity: hashes and machine case IDs dominated the page. New API metadata
   supplies provider and approved limit; presentation shows provider, time and
   understandable status. The limit is labelled, never called the paid amount.
4. Accessibility: focus-visible outlines, native buttons/disclosures, 44px-plus
   actions and existing reduced-motion behavior retained. Screenshot inspection
   is not a complete keyboard, screen-reader or WCAG conformance assessment.

## Official competition mapping

Checked October 11: https://aibuildercup.com/themes.html

- Technical Merit & Gen AI Implementation: 40%. Live Google model integration,
  working typed plans, independent verifier, recovery and durable cloud journal.
- Problem Alignment & Impact: 25%. Less bill administration, reserve protection
  and refusal of contradictory financial requests. User benefit still needs
  measured time/task success, not assumed savings.
- Innovation & Creativity: 25%. Show the complete constrained delegation loop
  on previously unseen inputs. Do not claim new cryptography, a novel DP method,
  universal fraud prevention or patent clearance.
- User Experience & Solution Design: 10%. One primary journey, minimal retyping,
  understandable outcomes and evidence behind disclosures.

The official public timeline lists October 18, 2026 for prototype submission and
October 11 for team formation. Confirm the exact cutoff/timezone and roster in
the participant dashboard. The public submission page contains category wording
that conflicts with its theme list; use the dashboard's BFSI category and obtain
organizer clarification if necessary.

## Not yet complete

- The 0.15.1 candidate is promoted; existing owner-only IAP remains unchanged.
- Judges need organizer-approved access. A protected owner-only URL is not enough.
- Required PDF proposal, public three-minute demonstration and submission fields.
- Broader unseen-input evaluation, real latency/cost data and task-time comparison.
- Real payment/biller connectors, settlement confirmation, compliant consumer
  consent/retention, production security review and durable proactive scheduling.

No UI improvement establishes real bank access, financial safety certification,
novelty or a guaranteed competition outcome. Do not add extra Google services
unless they solve a demonstrated part of the journey.

## Verification

Added tests cover prefill-only handoff, integer minor-unit formatting, rejection
of malformed records, tenant-scoped activity metadata and no payment on journal
reads. Existing financial gates and receipt/replay tests remain in the suite.
Browser checks must cover Home → Plan → Prepare → form (without submission),
Activity → existing receipt, and a phone-size layout.

Local browser checks completed all those paths. Home and planning are readable;
preparing populated INR 2499.00 and the selected recipient without running a
task. Activity loaded a held receipt read-only. A 390×844 home check showed
stacked controls and no horizontal overflow in the inspected viewport. This is
not a full accessibility certification or a measured usability study.

263 application tests ran: 262 passed and one optional test skipped. Eleven
tooling tests passed. The zero-traffic cloud candidate passed a live Vertex paid
notice check, unchanged balance, authenticated Firestore planning and anonymous
rejection with zero payment requests. Build and image are recorded in CLOUD_RUN.md.
