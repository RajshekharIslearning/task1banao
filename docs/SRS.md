# SRS: Vireo Audio SLA Breach Report Tool

**Version:** 0.1 · **Author:** Rajshekhar · **Client:** Vireo Audio (via Banao Technologies) · **Stakeholder:** Neha Kulkarni, Support Ops Manager

## 1. Purpose

A small, runnable tool that turns the Vireo ticket export into a weekly first-response SLA breach report by agent and shift, plus a quantified business goal. Time cap: \~5 hours. Anything not built is listed in §9.

## 2. Stakeholders and constraints

| Who | Need / constraint |
| --- | --- |
| Neha (Support Ops) | Weekly breaches by agent and shift. "Nothing fancy." |
| Arjun (Finance) | No hiring (frozen to Q4). Wants the SLA credit line explained (\~3x since last summer). |
| Priya (Head of CX) | Report must not demoralise the morning chat team; say what they can control. Claims credits are flat, CSAT moved. |
| Sameer (IT) | Export is UTC, duplicates from migration, legacy csat 0, \~40 failed IVR transcripts. |

## 3. Scope

**In:** data cleaning, breach computation, agent x shift x week report, credit-cost quantification, root-cause analysis of breaches, validation, memo. **Out (see §9):** live helpdesk integration, dashboards with auth, full free-text mining beyond what the goal needs.

## 4. Data inputs

`tickets.csv`, `agents.csv`, `orders.csv`, `customers.csv`, `products.csv`, `support-policy.pdf`, `email-thread.txt`, `README.txt`.

## 5. Business rules (from policy)

- **Breach:** first_response_at − created_at > target. Targets: chat 15 min, voice 2 h, social 4 h, email 8 h.
- **Credit:** Rs 350 per breached ticket, issued regardless of cause, on resolution.
- **Shifts (IST):** Morning 06:00–14:00, Day 14:00–22:00, Night 22:00–06:00.
- **Costs:** chat 210, email 260, voice 520, social 240, blended 290 per contact; transfer Rs 305; agent-hour Rs 165; replacement = unit cost + Rs 340.
- **Repeat contact:** same customer, same issue, within 30 days of resolution; costed at that channel's contact cost.
- **Attendance:** status resolved or closed. Tier 2 is not compared with Tier 1 on volume.
- **CSAT:** blank = no response, exclude from averages.

## 6. Functional requirements

**FR-1 Ingest.** Load all CSVs; fail loudly on missing files or columns.

**FR-2 Clean.**

- FR-2.1 Convert all timestamps UTC → IST before any shift or weekday logic.
- FR-2.2 De-duplicate tickets re-imported under both `source_system` values (key on ticket_id + created_at; keep `helpdesk` row). Log count removed.
- FR-2.3 Legacy csat 0 → null.
- FR-2.4 Legacy monetary values: detect native unit mismatch (e.g. paise vs rupees) by comparing refund_amount_inr against order_value_inr; normalise and log.
- FR-2.5 Flag failed IVR transcripts (voice, unusable text); exclude from text analysis only, not from SLA counts.
- FR-2.6 Open/pending tickets with no first response: report separately, not as breaches unless the target has lapsed.

**FR-3 Attribute.**

- FR-3.1 Join agent to roster by agent_id **and** ticket date within from_date/to_date (agents have multiple rows; June moves).
- FR-3.2 Shift is assigned from the **ticket creation time in IST** (when the SLA clock started), and compared with the roster shift of the agent, so mismatches are visible.
- FR-3.3 Note that `agent_id` is the **resolver**, not necessarily the first responder. Report this limitation on every agent view.

**FR-4 Breach report.** Weekly (ISO week, IST) tables: breaches, tickets, breach rate by agent, by shift, by team, by channel; minimum-volume threshold to suppress noisy small-n agents; export as CSV and HTML.

**FR-5 Root cause.** Decompose breaches by hour of day (IST), channel, team, queue load (tickets created per hour vs staffed agents), transfers, and tier. Test whether "morning team breaches most" survives the UTC fix, normalisation by volume, and controlling for overnight backlog handed to the morning shift.

**FR-6 Cost.** Credits = breaches x Rs 350, by month; compare against the monthly trend to settle the Finance (tripled) vs CX (flat) dispute. Break down the driver (volume, rate, or channel mix).

**FR-7 Business-goal candidates.** Evaluate from data and pick one stated as "from X% to Y%, worth Rs Z a quarter":

- Breach rate or credit spend in the specific hour/channel causing most breaches.
- Refund + replacement both given on one order (policy forbids).
- Misused `GW-OTHER` reason code hiding real causes.
- Repeat contacts and unnecessary transfers (Rs 305 each).
- Recurring product/lot defects (via order lot_code) driving contact volume.

**FR-8 AI-assisted classification.** Use an LLM to tag `customer_message` / `agent_notes` for the chosen goal (e.g. true defect reason, mis-categorised intake tag). Output structured JSON with a confidence and a short rationale. Cache results; keep prompt versions in the repo.

**FR-9 Framing.** Report shows breach as a **system/queue** metric first, agent second; includes "what the team can control" and no red-wall styling. Hiring is never the recommendation.

## 7. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-1 | Runs from README on a clean machine: Python 3.10+, `pip install -r requirements.txt`, one command (e.g. `python run.py --data ./data`). |
| NFR-2 | Deterministic non-AI steps; LLM steps optional with a cached fallback so the tool runs without an API key. |
| NFR-3 | Every cleaning step logs row counts before/after. |
| NFR-4 | Full run under 5 minutes on a laptop. |
| NFR-5 | No secrets in repo; keys via environment variables. |

## 8. Validation requirements

- VR-1 Hand-check a random sample (\~30 tickets) of breach flags against raw timestamps; report error rate.
- VR-2 Hand-label \~50 tickets for the LLM task; report precision/recall and where it fails.
- VR-3 Unit tests: UTC→IST boundary cases, shift edge times (06:00, 14:00, 22:00), dedupe, roster date join.
- VR-4 Sensitivity: show how headline numbers change with and without each cleaning step (especially timezone).
- VR-5 State the cost estimate with a range and assumptions.

## 9. Deliverables map

| Brief item | Artifact |
| --- | --- |
| Working tool | Repo + README + `run.py` |
| Business goal as number | One line in memo and README, with derivation |
| Proof it works | `VALIDATION.md` (samples, error rates, tests) |
| Memo to Neha | 1 page, non-technical, under 11 min read |
| Screen recording | ≤3 min: prompts, version changes, discarded work |
| Submission form | `submission-form.md`: tools used, cost, discarded items |

**Deliberately left out (to be stated in memo):** live dashboard, per-agent coaching workflow, full NLP over all text, forecasting. Reason: cap, and the weekly CSV/HTML covers the ask.

## 10. Assumptions and decisions log (fill as you go)

| # | Decision | Why |
| --- | --- | --- |
| A1 | Shift judged by creation time in IST | SLA clock starts at creation |
| A2 | Keep `helpdesk` row on duplicates | Current system is source of truth |
| A3 | Resolver used as agent; limitation disclosed | No first-responder field exists |
| A4 | Min ticket volume per agent for ranking | Avoid unfair small-n conclusions |
| A5 | Tier 2 reported separately | Policy §6 |

## 11. Suggested 5-hour plan

1. 0:00–0:45 Read pack, profile data, find traps.
2. 0:45–1:45 Clean + breach logic + tests.
3. 1:45–2:45 Weekly report + root cause + cost trend.
4. 2:45–3:30 Pick goal, LLM classification, validate.
5. 3:30–4:30 Memo, README, form.
6. 4:30–5:00 Record walkthrough.

## 12. Risks

- Timezone error makes the "morning team" finding an artifact (most likely trap).
- Roster join by name or without dates misattributes June movers.
- Over-building past the 5h cap.
- Report tone harming morning team morale (Priya's explicit concern).