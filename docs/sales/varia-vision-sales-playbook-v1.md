# Varia Vision — Sales Playbook v1
**Owner:** Founder  
**Version:** 1.0  
**Date:** 2026-11-06  
**Commercial status:** Hypothesis-testing; no single offer selected yet

## 1. Commercial strategy

Do not market Varia Vision as three unrelated products. Position it as one capability — computer-vision support for agricultural imagery — with three engagement formats chosen by the buyer's maturity and integration needs.

### Offer A — Varia Vision Audit (fastest path to first revenue)
**Buyer:** Drone service provider, crop consultant, agronomy service company, farm-management business, or AgTech team with a small set of field images and a concrete weed/crop monitoring question.

**Customer provides:** A small, agreed image sample, context (crop, location/season if shareable), and the question they need answered.

**Varia delivers:** A scoped technical assessment/report. The report must describe the input sample, processing performed, observed detections, limitations, and recommended next step. Include annotated examples only when actually generated and checked.

**Commercial unit:** Fixed-fee, fixed-scope assessment. Quote only after sample size, image quality, crop/context, turnaround, and deliverables are agreed.

**Boundary:** Not a guarantee of field-wide accuracy, yield improvement, herbicide savings, or production readiness. Do not promise performance outside the validated test conditions.

### Offer B — Paid Pilot / Proof of Concept
**Buyer:** AgTech vendor, agricultural software platform, drone analytics provider, or larger agronomy service business with a defined workflow and a technical/business sponsor.

**Discovery requirements:** Their current workflow, image source and volume, crop/weed classes, geography/season, current alternative, decision affected, success metric, stakeholders, data rights, security requirements, budget owner, and decision timeline.

**Varia delivers:** A written pilot plan with scope, dataset responsibilities, evaluation protocol, baseline, metrics, milestones, exclusions, acceptance criteria, and commercial terms.

**Commercial unit:** Paid, time-boxed pilot. Payment milestones and acceptance criteria must be agreed in writing before work begins.

**Boundary:** No free custom development disguised as a pilot. No use of customer images beyond the agreed purpose and retention terms.

### Offer C — API / White-label evaluation
**Buyer:** AgTech software vendor or drone analytics platform with an existing product, engineering capacity, and a need to add or evaluate weed/crop detection.

**Discovery requirements:** API/integration environment, input/output format, latency/volume expectations, deployment preference, data residency, support expectations, ownership/licensing, security review, and expected commercial scale.

**Varia delivers first:** A technical fit assessment and integration discovery. A sandbox/API proposal only if the current model and infrastructure can support it.

**Commercial unit:** Do not quote a subscription or licence before validating model quality, inference infrastructure, support burden, service levels, data rights, and expected usage.

**Boundary:** API availability, uptime, throughput, SLA, model update cadence, and exclusivity are not promised until technically verified and contractually defined.

## 2. Offer selection logic

| Buyer signal | Route |
|---|---|
| Has images and one concrete question; low integration complexity | Audit |
| Has a business workflow and wants measurable evaluation | Paid Pilot |
| Has an existing platform/product and engineering team | API / White-label evaluation |
| Need, buyer, data, or workflow is unclear | Discovery first; do not quote |
| No agricultural imagery use case or no credible buying path | Nurture or disqualify |

The three offers are alternatives within one sales motion, not three simultaneous pitches to the same buyer. Start with the buyer's problem; select the offer after discovery.

## 3. Ideal customer profile (ICP)

### Primary segments to test first
1. Agricultural drone / aerial-imagery service providers.
2. Crop-monitoring and precision-agriculture service companies.
3. Agronomy and crop-consulting businesses that use field imagery.
4. AgTech software vendors whose product could incorporate weed/crop image analysis.

### Initial exclusions
- General AI companies with no agriculture workflow.
- Consumer gardening apps without a commercial field-imagery use case.
- Companies with no identifiable product/service, no relevant imagery workflow, and no plausible buyer.
- Research-only organizations unless there is a funded commercial project or a clearly identified industry partner.

### Account qualification score (0–100)
Use this as prioritization only; it does not prove purchase intent.

| Criterion | Points |
|---|---:|
| Direct agricultural imagery / drone / crop-monitoring workflow evidenced | 0–25 |
| Clear weed/crop detection or adjacent decision problem | 0–20 |
| Commercial service/product and plausible ability to pay | 0–15 |
| Relevant team / buyer role identifiable | 0–15 |
| Evidence of active projects, partnerships, product expansion, or buying trigger | 0–10 |
| Geographic / operational fit for a remote pilot | 0–10 |
| Evidence freshness and source quality | 0–5 |

**Triage:** 75–100 = founder review priority; 55–74 = research further; below 55 = hold/disqualify. Missing evidence receives zero, not an assumed score. Even a score above 75 remains a target account until a real person engages and need is confirmed.

## 4. Buyer roles to identify

- Founder / CEO / Managing Director (small service providers and early-stage AgTech).
- Head of Product / Product Manager (platform vendors).
- Head of Agronomy / Agronomy Lead / Crop Consultant (workflow owner).
- Head of Drone Operations / Remote Sensing Lead / GIS Lead (imagery owner).
- CTO / Engineering Lead (API and white-label route).
- Innovation / Digital Agriculture Lead (larger agribusiness).

Do not guess personal email addresses. Save a contact only when the person's name and role are supported by a source; distinguish verified email from contact form or generic inbox.

## 5. Sales stages and CRM rules

Use the existing `natasha_leads.stage` values. Keep stages aligned with observable buyer progress:

| CRM stage | Entry evidence | Next action / exit |
|---|---|---|
| `new` | Account discovered and source URL captured | Research fit and use case |
| `researching` | Relevant company/product evidence being checked | Identify buyer/contact route; decide pursue or disqualify |
| `qualified` | Founder reviewed fit evidence; a specific plausible use case and contact path exist | Approve tailored first outreach |
| `contacted` | Actual message/call sent; date and channel logged | Follow up or record response |
| `replied` | A human at the account replied | Clarify need, role, process, and next step |
| `meeting` | Discovery meeting actually held or booked (record which in activity) | Confirm requirements and offer route |
| `proposal` | A scoped written proposal was sent | Record review date, decision process, and objections |
| `pilot` | Pilot scope and commercial terms accepted in writing | Deliver agreed pilot and track payment/outcome |
| `won` | Signed agreement or confirmed paid order exists | Handoff and delivery |
| `lost` | Buyer declined or opportunity closed without sale | Record loss reason |
| `disqualified` | Clear mismatch, invalid account, or no plausible buying path | Stop active pursuit |

Important: Natasha currently assigns `qualified` automatically based on fit score. Treat those records as **AI-prioritized, founder-unreviewed** until the evidence is checked. Do not treat an LLM score as a buyer qualification event.

## 6. Required CRM fields using the current schema

The current database already supports:
- `natasha_companies`: company name, website, industry, country, notes, source.
- `natasha_contacts`: full name, role, email, LinkedIn URL, decision-maker flag, notes.
- `natasha_leads`: product, stage, offer route, source, fit score/rationale, estimated value, currency, next action, next-action date, last-contacted date, notes, primary contact.
- `natasha_activities`: activity type, subject, body, occurred-at, metadata.
- `natasha_follow_ups`: title, due date, status.
- `natasha_message_drafts`: recipient, subject, body, approval/sent status.

Use the dedicated `natasha_leads.offer_route` field for the provisional suggested commercial route. Allowed values are `audit`, `pilot`, `api_white_label`, and `discovery_pending`. The database defaults existing and new manually created leads to `discovery_pending`; Natasha may suggest a route, but the founder must review and confirm it before treating it as the commercial choice.

Store evidence as source URLs and short factual observations. Do not put unverified assumptions into the company description as facts.

### Minimum record standard
An active lead cannot remain active without:
1. Linked company.
2. Source URL and evidence.
3. Fit rationale.
4. Founder-reviewed stage.
5. Next action and due date.
6. Contact record or an explicit next action to identify one.

Every actual outbound contact must create an `email_sent`, `call`, or other appropriate activity and a dated follow-up. Draft approval is not sending; the database already distinguishes `draft`, `approved`, and `sent`.

## 7. Founder-led sales workflow

1. Natasha researches no more than a small reviewable batch. Research volume is not the KPI.
2. Founder reviews company evidence and deduplicates the account.
3. Founder identifies a relevant role and verifies a contact route.
4. Founder selects Audit, Pilot, API/White-label, or Discovery pending.
5. Natasha drafts a message tied to one observed company-specific signal.
6. Founder edits and approves. Approval does not send the message.
7. Founder sends through the chosen channel and logs the actual event.
8. Create a follow-up with a due date before leaving the lead.
9. If a buyer replies, move to discovery and document need, budget path, authority, timing, data, and success criteria.
10. Send a proposal only after scope and acceptance criteria are agreed.
11. Mark won only after signed agreement or confirmed paid order.

## 8. First-touch message framework

Subject: A question about [specific evidenced workflow]

Hi [Name],

I came across [specific product/service/project] at [Company]. I noticed that your team [specific factual observation from source].

I'm building Varia Vision at Varia Studio, a computer-vision capability focused on crop/weed detection from agricultural imagery. I'm exploring whether this could support workflows like [carefully stated use case].

Would it be useful to compare notes on how your team currently handles [specific problem]? If there is a fit, we could start with a small, clearly scoped image assessment rather than assume a larger integration is needed.

Best regards,  
Mahdieh Kazemi  
Founder, Varia Studio

Personalize the observation and use case for every account. Remove any sentence that cannot be supported by evidence. Do not send generic bulk outreach.

## 9. Discovery call guide

1. What crop / geography / season / field workflow is in scope?
2. Where do images come from (drone, phone, satellite, other), and who owns them?
3. What decision is currently made from those images?
4. How is weed/crop identification done today? What fails or costs time?
5. Which weed/crop classes matter, and what ground-truth labels exist?
6. What would a useful evaluation look like? Which metric and acceptance threshold matter to you?
7. Who owns the problem, technical evaluation, budget, and final approval?
8. What are the data rights, privacy, security, and retention constraints?
9. Is there a project budget and decision date?
10. Which next step would the buyer commit to, and by when?

Do not pitch all three routes. Recommend one route based on answers and document why.

## 10. Proposal templates and pricing discipline

### Audit proposal must specify
- Number and format of images / sample selection
- Scope of analysis and exact deliverables
- Turnaround after complete data receipt
- What is excluded
- Price, currency, tax/payment terms, validity
- Data handling and deletion/retention
- Limitations and acceptance criteria

### Pilot proposal must specify
- Problem statement and baseline
- Dataset ownership, volume, labels, permitted use
- Model/evaluation scope and metrics
- Milestones and timeline
- Deliverables and acceptance criteria
- Customer responsibilities and dependencies
- Price and payment milestones
- Change-control, data, IP, confidentiality, and termination terms

### API / White-label proposal must specify
- Technical discovery outcome
- API and deployment feasibility
- Expected volume, latency, integration, security, support
- Licensing and IP terms
- Usage pricing / minimum commitment only after cost modelling
- SLA only if operationally supportable

**Pricing policy:** No invented public price list yet. Quote each first engagement after scope and delivery effort are understood. Record actual hours, compute/API cost, review effort, and gross margin. After 3–5 comparable paid engagements, use the evidence to establish a repeatable price floor and package.

## 11. First 14-day validation sprint

### Days 1–2: CRM hygiene
- Review all existing Varia Vision leads; deduplicate companies.
- Reclassify AI-generated `qualified` records to `researching` unless founder-reviewed evidence meets the rules above.
- Reject wrong-company URLs and unsupported claims.
- Do not approve or send all existing drafts in bulk.

### Days 3–4: Account shortlist
- Build a shortlist of 15 accounts across the four ICP segments.
- Pick the 5 strongest accounts based on evidence and plausible buyer access.
- Identify one relevant role and contact route per account.

### Days 5–8: Discovery-oriented outreach
- Personalize and send up to 5 carefully reviewed first-touch messages.
- Log the sent event and schedule follow-up.
- Record responses and objections verbatim where useful.

### Days 9–11: Buyer conversations
- Seek discovery calls, not premature commitments.
- Identify which of Audit, Pilot, or API/White-label is actually requested.
- Ask for image sample / workflow context only when appropriate and with permission.

### Days 12–14: Offer test
- Produce one scoped proposal for a real buyer need if evidence supports it.
- Compare objections, urgency, delivery effort, and willingness to pay across routes.
- Select a temporary primary offer only if buyer evidence supports it; otherwise continue the test.

## 12. Metrics for the first sprint

Track counts, not vanity targets:
- Accounts researched and founder-reviewed
- Accounts rejected / duplicate
- Verified contacts / contact routes
- Personalized messages actually sent
- Replies and positive replies
- Discovery meetings booked / held
- Offer route selected by buyer
- Proposals sent
- Paid pilots / audits won
- Cash received
- Hours spent per account and per delivery

After the first 5–10 real conversations, compare which route has the clearest pain, fastest decision path, strongest willingness to pay, and feasible delivery margin. Do not declare a winning business model before that evidence exists.

## 13. Definition of done

The first sales system is operational when:
- Every active lead has source evidence, founder-reviewed stage, offer route, and dated next action.
- The top 5 accounts have relevant contact routes.
- No AI-generated score alone marks a lead as qualified.
- Every sent message is logged and followed up.
- At least one real buyer conversation has tested the offer framing.
- Any quote sent is scoped and cost-aware.
- Natasha research volume stays within the founder's review capacity.
