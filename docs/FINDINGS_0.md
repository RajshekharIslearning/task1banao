# FINDINGS_0 — Vireo Audio SLA Data Orientation
**Generated:** 2026-10-02 (Step 1 only — no tool code yet)
**Analyst:** Antigravity (AI-assisted; all numbers verified against raw data by `recheck.py`)

---

## A. Data Quality — Counts

### tickets.csv  (11 816 raw rows → 11 200 after dedup · 21 columns · 1 Jan 2025 – 30 Jun 2026 UTC)

| Issue | Count | Notes |
|---|---|---|
| Total raw rows | 11 816 | |
| Unique ticket_ids | 11 200 | |
| Rows duplicated across source systems | **616** | Same ticket_id in both `helpdesk` and `legacy_fd`; keep `helpdesk` row per FR-2.2. All breach rates below are on the deduplicated 11 200. |
| `helpdesk` rows | 8 079 | |
| `legacy_fd` rows | 3 737 | |
| `resolved_at` null (open/pending) | 624 | 372 open + 252 pending |
| `order_id` missing | **4 021** (34.0%) | Policy notes `customer_id + product_sku` as fallback join |
| `csat_score = 0` (legacy no-response sentinel) | **2 066** | All 2 066 come from `legacy_fd`; 0 from `helpdesk`. Must be converted to NaN (FR-2.3). |
| `csat_score = NaN` (current-system no-response) | 4 477 | Already correct; exclude from averages per policy §8 |
| `refund_amount_inr` null | 9 721 | Expected (most tickets have no refund) |
| `refund_reason_code` null | 9 721 | Matches refund null — consistent |
| `first_response_at` null | 0 | All tickets have a first-response timestamp |
| Voice tickets with null/short customer_message (failed IVR proxy) | ~40 | Sameer confirms ~40 failed IVR transcripts; flag but keep in SLA counts (FR-2.5) |
| Orphan `agent_id` (in tickets but not in agents.csv) | **0** | Clean |
| Orphan `order_id` (in tickets but not in orders.csv) | **0** | Clean |
| Orphan `customer_id` (in tickets but not in customers.csv) | **0** | Clean |

### agents.csv  (46 rows · 8 columns)

| Issue | Count | Notes |
|---|---|---|
| Unique agent_ids | 44 | Matches "44 agents" stated in brief |
| Roster rows | 46 | 2 agents have 2 rows each (shift change in June 2025) |
| `to_date` null (still active) | 41 | Expected; null = current assignment |
| Night-shift rows ending 2025-06-29 | **5** | See roster section D below for per-agent successor status |

### orders.csv  (15 000 rows · 8 columns)
No nulls. `order_value_inr` range consistent with consumer electronics pricing.

### customers.csv  (9 500 rows · 6 columns) · products.csv (14 rows)
No nulls in either file.

---

## B. Contradictions / Traps

**B1 — "Morning team breaches most" — two distinct mechanisms, not one**

There are two separate effects that both inflate the Morning team's breach count; they compound each other and must be reported separately.

*Effect 1 — Resolver attribution (the dominant cause):* Policy §3 credits breaches to the resolving agent, not the agent on duty when the SLA clock started. Overnight tickets created in the 22:00–06:00 IST window accumulate a backlog; they are then picked up and resolved by the Morning shift when it opens at 06:00 IST. 96 % of overnight-created breaches (1 619 of 1 631 on deduplicated data) are attributed to Morning-rostered agents — not because the Morning team is slow, but because they inherit the overnight queue. This is the core unfairness Priya is concerned about. It cannot be fixed by timezone conversion; it requires the report to show *creation-shift* alongside *resolver-shift* for every breach.

*Effect 2 — Timezone mis-attribution (a reporting artefact):* If UTC timestamps are used unconverted for shift logic, 68.4 % of tickets (7 656 of 11 200) are assigned to the wrong shift. Specifically: 2 167 Night-IST tickets (created 22:00–00:29 IST, which maps to 16:30–19:00 UTC) are mis-labelled Day in UTC, and 2 379 Morning-IST tickets (created 06:00–13:30 IST, which maps to 00:30–08:00 UTC) are mis-labelled Night in UTC. The net effect on breach counts without conversion is shown below:

| Shift | Tickets (correct IST) | Breaches | Rate | Tickets (wrong UTC) | Breaches | Rate |
|---|---|---|---|---|---|---|
| Morning | 4 046 | 394 | **9.7 %** | 4 777 | 424 | 8.9 % |
| Day | 4 668 | 415 | **8.9 %** | 3 725 | 1 643 | **44.1 %** |
| Night | 2 486 | 1 631 | **65.6 %** | 2 698 | 373 | 13.8 % |

Without conversion, Day appears to have the problem (44 % breach rate) and Night looks almost clean — the opposite of reality. Morning is less distorted but still carries inherited overnight breaches.

**B2 — Breach attributed to resolver, not creator (disclosure required):** SRS FR-3.3 requires this limitation to be stated on every agent view. See B1 / Effect 1.

**B3 — Night-shift staffing gap post-2025-06-29:** Three agents have no successor row (see Section D). This means chat and email night coverage was reduced after 29 June 2025 with no documented replacement — not simply a cost-neutral "reshuffle" as described in the email thread.

**B4 — Legacy csat=0 vs. blank:** Policy §8: "blank = no response." Legacy_fd used 0 instead. 2 066 zeros are all in `legacy_fd`. Treating them as actual CSAT 0 (dissatisfied) would distort averages — must be nulled before any CSAT analysis.

**B5 — Finance vs. CX credits dispute:** Arjun says credits "roughly tripled since last summer." Priya says they "look flat." Both are consistent with the data: the breach rate jumped from ~9.2 % (pre-June-2025, deduped) to ~25.0 % (post-June-2025) — roughly a 2.7× increase in rate, on a growing volume base. Priya may be comparing recent months, which are all high but stable at ~25 %. The step-change happened in the week of 2025-06-30 (breach rate moved from ~11.7 % to ~29.1 % in a single week). That is the event to explain to Arjun.

**B6 — Voice excluded from night breach analysis (by design):** Voice IVR only accepts callbacks 08:00–22:00 IST (policy §2). No voice tickets exist in the 22:00–08:00 IST window. Night breach concentration is entirely chat + email + social.

**B7 — SRS data-input naming mismatch:** SRS §4 lists `support-policy.pdf` and `email-thread.txt` but actual filenames in `docs/` are `Support-policy.txt` and `Emailthread.txt`. No functional problem; note in README.

---

## C. Stakeholder Wants

| Stakeholder | Role | Explicit asks | Constraints / concerns |
|---|---|---|---|
| **Neha Kulkarni** | Support Ops Manager | Weekly breach report by agent and shift. "Nothing fancy." | Wants numbers before a conversation with agents |
| **Arjun Mehta** | Finance Controller | Explain why SLA credit line tripled since last summer | Headcount frozen to Q4; answer cannot be "hire" |
| **Priya Raman** | Head of CX | Report must not demoralise morning chat team; frame what they *can* control | Believes credits are flat, CSAT moved — wants that narrative explored |
| **Sameer Qureshi** | Helpdesk Admin (IT) | No asks — provided data; flagged UTC, duplicates, csat 0, ~40 IVR fails | Technical informant |

**Internal tension:** Neha and Arjun want facts by agent; Priya wants system/queue framing. SRS FR-9 and FR-5 address this by showing overnight-backlog as the structural driver, not individual agent failure.

---

## D. Roster — Night Agents Ending 2025-06-29

| agent_id | Name | Team | Successor row? |
|---|---|---|---|
| A3001 | Zoya Mehta | Chat Frontline | **No — coverage gap** |
| A3002 | Tarun Mishra | Chat Frontline | Yes — Day shift from 2025-06-30 |
| A3003 | Harpreet Deshpande | Chat Frontline | Yes — Day shift from 2025-06-30 |
| A3016 | Deepak Jadhav | Email Frontline | **No — coverage gap** |
| A3017 | Shreya Bhatt | Email Frontline | **No — coverage gap** |

Three of the five night agents (Zoya Mehta on Chat; Deepak Jadhav and Shreya Bhatt on Email) have no later roster row. The two Chat agents who moved to Day (A3002, A3003) do not cover night chat. This confirms that the overnight coverage reduction after 29 June 2025 was not cost-neutral from a staffing standpoint.

---

## E. Breach Rates — Deduplicated (11 200 tickets)

| Slice | Tickets | Breaches | Rate |
|---|---|---|---|
| **All** | 11 200 | 2 440 | **21.8 %** |
| Pre 2025-06-30 | 2 252 | 207 | 9.2 % |
| Post 2025-06-30 | 8 948 | 2 233 | 24.96 % |
| Night creation (22:00–06:00 IST) | 2 486 | 1 631 | **65.6 %** |
| Day / Morning creation | 8 714 | 809 | 9.3 % |
| Chat channel | 4 959 | 1 368 | 27.6 % |
| Email channel | 3 647 | 745 | 20.4 % |
| Social channel | 1 106 | 243 | 22.0 % |
| Voice channel | 1 488 | 84 | 5.6 % |

---

## F. H7 — Refund + Replacement Check (Extended)

Policy §5: "In no case is a customer to receive both a refund and a replacement for the same order."

| Join method | Cases found | Notes |
|---|---|---|
| Same ticket row (refund > 0 AND replacement = Y) | **6** | Direct violations; no qty caveat needed — each is a single-row breach |
| Same `order_id`, different tickets | **109 rows** (94 unique orders) | Strongest evidence of policy breach; see rupee totals below |
| Fallback join (`customer_id` + `product_sku`, `order_id` null on both) | **44 rows** | Weaker evidence — could be a second contact on a different order; flag for manual review |

**Rupee totals (same order_id cross-ticket cases, 94 orders):**
- Total refund amount: **Rs 2,79,825**
- Total replacement cost (unit cost + Rs 340 logistics): **Rs 1,89,860**
- Combined exposure: **Rs 4,69,685**

**Quantity caveat:** 6 of the 109 cross-order rows have `qty > 1` on the order. These are marked as *candidates*, not confirmed violations — a single order for 2 units could legitimately yield one refund for one unit and one replacement for another. Manual review required.

All remaining 103 cross-order rows have `qty = 1` and are therefore confirmed policy violations pending any dispute from agents.

---

## G. Hypothesis Verdicts

| # | Hypothesis | Verdict | Key numbers (deduplicated) |
|---|---|---|---|
| H1 | Raw timestamps are UTC and must be shifted +5:30 for shift logic | ✅ **CONFIRMED** | DATA_README, Sameer's email, and policy §9 all state UTC API export. Without conversion, 68.4 % of tickets are assigned to the wrong shift and the breach pattern inverts (see B1). |
| H2 | ~616 tickets are duplicated across helpdesk and legacy_fd | ✅ **CONFIRMED** | Exactly **616** ticket_ids appear in both source systems. |
| H3 | Breach rate rose sharply around 30 June 2025 | ✅ **CONFIRMED** | Pre: **9.2 %** (n=2 252). Post: **25.0 %** (n=8 948). Step visible in week of 2025-06-30 (11.7 % → 29.1 %). |
| H4 | Rise concentrated in 22:00–06:00 IST, mostly chat/social; night roster rows end 2025-06-29 | ✅ **CONFIRMED** | Night breach rate: **65.6 %** (2 486 tickets); post-cutoff night: **79.2 %**. Channels in night: chat 80 %, social 73 %, email 42 %, voice 0 %. 5 night roster rows end 2025-06-29; 3 have no successor. |
| H5 | Most breaches are credited to Morning-shift resolvers because overnight tickets are picked up later | ✅ **CONFIRMED** | **1 619 of 1 631** overnight-created breaches (99.3 %) are resolved by Morning-rostered agents. Day: 4. Night: 8. This is structural, not agent failure. |
| H6 | legacy_fd refund_amount_inr uses a different unit from helpdesk (e.g. paise) | ❌ **REJECTED** | Refund / order_value ratio ≤ 1.0 for all rows in both systems (max = 1.0; zero rows with ratio > 5×). Both systems show plausible rupee values. |
| H7 | Some orders get both a refund and a replacement (policy forbids this) | ✅ **CONFIRMED** | 6 same-row violations; 94 unique orders with refund ticket + separate replacement ticket (109 cross-ticket pairs); 44 additional fallback-join candidates. Total exposure Rs 4,69,685. 6 cases with qty > 1 flagged as candidates pending manual review. |
