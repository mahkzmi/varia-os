# Varia Studio — Phase 1 Founder Operating System

**Status:** Active operating plan  
**Owner:** Founder  
**Commercial focus:** Varia Vision  
**Team model:** Founder-led, one-person operation  
**System of record:** Varia OS (GitHub + Supabase + Render)

## Phase 1 outcome

Build a repeatable founder-led sales process before adding more products, tools, or headcount. The system must make the next action for every promising account visible and prevent research volume from being mistaken for revenue.

## Current baseline (6 Nov 2026)

Snapshot from the connected Supabase project:
- 23 company records
- 37 lead records; all are Varia Vision
- 32 leads are marked `qualified`; 5 are `researching`
- 0 contacts
- 36 message drafts awaiting review; 1 approved
- 0 follow-ups

Interpretation: the CRM has accumulated research output, but the sales process is not yet operational. In particular, there are no contact records and no scheduled follow-ups. The current `qualified` label should be audited; it must not be treated as a buyer-confirmed opportunity until the qualification evidence is recorded.

## Operating principles

1. One source of truth: company, contact, lead, activity, draft, and follow-up records live in Varia OS.
2. No lead without a next action: every active lead must have an owner (the founder for now), a dated next action, and evidence.
3. Research is not qualification: a company is only qualified after a real buyer/use case and a credible route to a conversation are verified.
4. No unapproved external communication: Natasha may research and draft; a human approves and sends.
5. No invented commercial claims: do not publish pricing, performance, customer outcomes, integrations, or delivery commitments unless supported by approved product evidence.
6. Quality over volume: prioritize a small, reviewable batch of accounts rather than maximizing records created.

## Varia Vision target account hypothesis

Initial target segments to validate:
- AgTech businesses offering crop monitoring or precision-agriculture services
- Drone and aerial-imagery service providers serving agriculture
- Crop consultants and agronomy service businesses using field imagery
- Agricultural software/platform vendors who may need a weed/crop vision capability

An account is a fit hypothesis, not a qualified opportunity, until evidence supports the use case and a relevant contact or buying path is identified.

## CRM pipeline and exit criteria

Use the existing lead stages, with these rules:

| Stage | Entry / evidence required | Exit condition |
|---|---|---|
| `new` | Account discovered; source URL captured | Initial research started |
| `researching` | Product/use-case research underway | Evidence and relevant contact path recorded |
| `qualified` | ICP fit, specific use case, plausible buyer/contact route, and reason to engage documented | First personalized outreach approved and sent |
| `contacted` | Actual outreach date and channel recorded | Human reply received or outreach sequence closed |
| `replied` | Buyer/contact replied | Need and next step clarified |
| `meeting` | Meeting actually booked or held; record which | Discovery completed and next commercial step agreed |
| `proposal` | Proposal with scope, price, validity and assumptions sent | Buyer decision / negotiation |
| `pilot` | Pilot scope and written acceptance agreed | Pilot outcome and payment status recorded |
| `won` | Signed agreement or confirmed paid order; attach evidence | Handoff and delivery |
| `lost` | Opportunity explicitly declined or closed | Loss reason recorded |
| `disqualified` | Clear mismatch, invalid account, or no credible buying path | No further active work |

Never move a lead to `qualified` just because an LLM assigned a high fit score. Stage is based on observed evidence; fit score is only a prioritization aid.

## Required lead record

For each active Varia Vision lead, capture:
- Company and canonical website
- Country and segment
- Source URL(s) and date checked
- Evidence of relevant agricultural imagery / crop monitoring workflow
- Likely use case for Varia Vision
- Relevant person, role, and verified contact route (if found)
- Fit score and concise rationale
- Current stage
- Last activity
- One next action and due date
- Estimated value only when supported by a real commercial conversation or approved offer

## Founder daily operating rhythm

**Start of day — 20 minutes**
- Review overdue and due-today follow-ups.
- Review new Natasha research; reject duplicates and weak evidence.
- Pick the three highest-value actions for the day.

**Sales block — 60–90 minutes**
- Research or contact a small number of high-fit accounts.
- Personalize outreach to the account's evidenced use case.
- Record every sent message and response in the CRM.
- Set the next action before closing each record.

**Product / delivery block**
- Maintain a demo-ready Varia Vision workflow and evidence pack.
- Record blockers and decisions; avoid building features without a buyer signal.

**End of day — 10 minutes**
- Update lead stages and follow-up dates.
- Record any cash movement or committed expense in the finance ledger.
- Leave tomorrow's top three actions visible.

## Weekly review

Once per week, review:
- New accounts researched
- Accounts accepted / rejected after human review
- Verified contacts found
- Personalized messages actually sent
- Replies, positive replies, meetings booked and meetings held
- Proposals sent, pilots agreed, revenue received
- Overdue follow-ups
- Cash received, cash spent, upcoming obligations

Do not set arbitrary conversion targets until a baseline exists. For the first two weeks, measure actual rates and identify the biggest drop-off.

## Natasha operating contract

Natasha may:
- Discover accounts and collect public evidence
- Suggest fit scores with explicit rationale
- Identify likely roles and publicly available contact routes
- Draft personalized first-touch messages
- Flag duplicates and missing evidence

Natasha may not, without explicit approval:
- Send email, LinkedIn messages, or other external communications
- Promise pricing, discounts, timelines, accuracy, integrations, or custom work
- Mark an account as buyer-qualified without human-reviewed evidence
- Create commercial commitments or alter financial records

Daily research cap: maximum 10 new AI-research leads per user/product per UTC day, subject to the deployed API quota enforcement. Do not interpret the cap as a target; stop earlier if review capacity is full.

## Phase 1 implementation order

1. Audit the existing 37 leads and 36 drafts. Do not bulk-send or bulk-approve.
2. Deduplicate company and lead records; verify each company website and evidence.
3. Promote only evidence-backed accounts; demote weak or incomplete records to `researching` or `disqualified`.
4. Find and verify relevant contacts for the strongest accounts.
5. Review a maximum of five high-priority drafts per working session; personalize before approval and sending.
6. Create a dated follow-up for every message sent and every active buyer conversation.
7. Add a simple founder task list and cash-in/cash-out ledger to Varia OS.
8. Only after the workflow is used consistently, automate reminders and weekly reporting.

## Phase 1 definition of done

- Every active lead has evidence, a stage, and a dated next action.
- No account is called qualified solely because of AI scoring.
- The first five target accounts have a verified contact path and tailored outreach.
- Every sent outreach has a recorded activity and follow-up date.
- Founder can see today's actions, overdue follow-ups, pipeline stage counts, and cash position from one workspace.
- No external message is sent without human approval.
