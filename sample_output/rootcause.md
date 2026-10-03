# Root Cause Analysis: SLA Breaches

## 1. Breach Rate by Month and Hour-Channel

### By Month (IST)
- **2025-01**: 8.2% (21.0/256.0)
- **2025-02**: 11.3% (41.0/362.0)
- **2025-03**: 9.1% (37.0/406.0)
- **2025-04**: 9.1% (38.0/418.0)
- **2025-05**: 9.5% (40.0/419.0)
- **2025-06**: 8.4% (34.0/405.0)
- **2025-07**: 22.9% (109.0/475.0)
- **2025-08**: 27.5% (188.0/684.0)
- **2025-09**: 26.7% (182.0/682.0)
- **2025-10**: 24.0% (207.0/863.0)
- **2025-11**: 24.3% (212.0/873.0)
- **2025-12**: 23.3% (195.0/836.0)
- **2026-01**: 25.9% (213.0/821.0)
- **2026-02**: 22.8% (157.0/688.0)
- **2026-03**: 26.0% (203.0/782.0)
- **2026-04**: 26.8% (194.0/725.0)
- **2026-05**: 25.2% (188.0/747.0)
- **2026-06**: 23.9% (181.0/758.0)

### By Hour (IST) and Channel
Top 5 highest breach rate segments (min 50 tickets):
- **01:00 Chat**: 91.1% (102.0/112.0 tickets)
- **04:00 Chat**: 85.0% (51.0/60.0 tickets)
- **23:00 Chat**: 84.4% (248.0/294.0 tickets)
- **03:00 Chat**: 84.3% (43.0/51.0 tickets)
- **22:00 Social**: 82.8% (72.0/87.0 tickets)

## 2. Roster Change Impact (by Created Shift)

### Before 2025-06-30
- **Morning**: 9.2% (77.0/841.0)
- **Day**: 8.6% (80.0/925.0)
- **Night**: 10.3% (50.0/486.0)
### On/After 2025-06-30
- **Morning**: 9.9% (317.0/3205.0)
- **Day**: 9.0% (335.0/3743.0)
- **Night**: 79.0% (1581.0/2000.0)

## 3. Cross-Tabulation: Ticket Creation vs Resolving Agent Shift

Breaches matrix (Row = Created Shift, Col = Resolver Shift):

| Created Shift | Morning | Day | Night |
|---|---|---|---|
| Day | 204 | 197 | 14 |
| Morning | 248 | 139 | 7 |
| Night | 1566 | 57 | 8 |

- **Insight**: There are 1566 breaches for tickets created overnight (Night) but resolved by the Morning team.

## 4. Night Shift (22:00-06:00) Coverage

- **Before Roster Change**: 5 agents on Night shift.
- **After Roster Change**: 0 agents on Night shift.
- **Insight**: Night coverage was reduced.

## 5. Monthly SLA Credits & Cost Drivers

- **2025-01**: 7,350 Rs (21.0 breaches)
- **2025-02**: 14,350 Rs (41.0 breaches)
- **2025-03**: 12,950 Rs (37.0 breaches)
- **2025-04**: 13,300 Rs (38.0 breaches)
- **2025-05**: 14,000 Rs (40.0 breaches)
- **2025-06**: 11,900 Rs (34.0 breaches)
- **2025-07**: 38,150 Rs (109.0 breaches)
- **2025-08**: 65,800 Rs (188.0 breaches)
- **2025-09**: 63,700 Rs (182.0 breaches)
- **2025-10**: 72,450 Rs (207.0 breaches)
- **2025-11**: 74,200 Rs (212.0 breaches)
- **2025-12**: 68,250 Rs (195.0 breaches)
- **2026-01**: 74,550 Rs (213.0 breaches)
- **2026-02**: 54,950 Rs (157.0 breaches)
- **2026-03**: 71,050 Rs (203.0 breaches)
- **2026-04**: 67,900 Rs (194.0 breaches)
- **2026-05**: 65,800 Rs (188.0 breaches)
- **2026-06**: 63,350 Rs (181.0 breaches)

**Dispute Resolution: Did costs 'triple' (Finance) or stay 'flat' (CX)?**
- Average Monthly Tickets (Jan-Jun 2025): 378 | (Jul 2025-Jun 2026): 744
- Average Monthly Breach Rate (Jan-Jun 2025): 9.3% | (Jul 2025-Jun 2026): 24.9%
- Average Monthly Credits (Jan-Jun 2025): 12,308 Rs | (Jul 2025-Jun 2026): 65,012 Rs

**Credit Increase Breakdown (Total Increase: 52,704 Rs)**
- Volume Effect (holding rate constant): 11,955 Rs
- Rate Effect (holding volume constant): 20,671 Rs
- Compound/Joint Effect: 20,078 Rs

- **Conclusion**: Finance is correct that total monthly costs multiplied massively (from ~12k to ~66k average). CX is wrong that the rate was 'flat'—the average breach rate jumped from 9.2% to 24.8%. The increase is driven by BOTH higher volume and a severely worsened breach rate.

## 6. Excess Breaches (Night vs Baseline)

- **2025-01**: Baseline rate 8.4% | Night breaches: 4 | Expected: 4.4 | Excess: 0.0
- **2025-02**: Baseline rate 12.1% | Night breaches: 5 | Expected: 7.9 | Excess: 0.0
- **2025-03**: Baseline rate 7.3% | Night breaches: 14 | Expected: 6.6 | Excess: 7.4
- **2025-04**: Baseline rate 8.6% | Night breaches: 10 | Expected: 8.0 | Excess: 2.0
- **2025-05**: Baseline rate 9.5% | Night breaches: 9 | Expected: 8.7 | Excess: 0.3
- **2025-06**: Baseline rate 7.8% | Night breaches: 10 | Expected: 7.5 | Excess: 2.5
- **2025-07**: Baseline rate 7.9% | Night breaches: 79 | Expected: 7.7 | Excess: 71.3
- **2025-08**: Baseline rate 10.6% | Night breaches: 132 | Expected: 16.7 | Excess: 115.3
- **2025-09**: Baseline rate 11.0% | Night breaches: 124 | Expected: 16.9 | Excess: 107.1
- **2025-10**: Baseline rate 10.3% | Night breaches: 137 | Expected: 18.6 | Excess: 118.4
- **2025-11**: Baseline rate 8.5% | Night breaches: 154 | Expected: 16.6 | Excess: 137.4
- **2025-12**: Baseline rate 8.7% | Night breaches: 138 | Expected: 16.0 | Excess: 122.0
- **2026-01**: Baseline rate 10.2% | Night breaches: 149 | Expected: 19.4 | Excess: 129.6
- **2026-02**: Baseline rate 8.1% | Night breaches: 114 | Expected: 12.7 | Excess: 101.3
- **2026-03**: Baseline rate 9.3% | Night breaches: 147 | Expected: 16.6 | Excess: 130.4
- **2026-04**: Baseline rate 9.8% | Night breaches: 139 | Expected: 16.2 | Excess: 122.8
- **2026-05**: Baseline rate 9.0% | Night breaches: 136 | Expected: 15.6 | Excess: 120.4
- **2026-06**: Baseline rate 8.6% | Night breaches: 130 | Expected: 14.4 | Excess: 115.6

**Excess Cost per Quarter:**
- **2025Q1**: 2,607 Rs
- **2025Q2**: 1,683 Rs
- **2025Q3**: 102,795 Rs
- **2025Q4**: 132,256 Rs
- **2026Q1**: 126,440 Rs
- **2026Q2**: 125,590 Rs

## 7. Fair Agent View (In-Shift Tickets Only)


### Tier 1 Agents (Min 20 tickets)
- **A3025**: 0.0% (0/119)
- **A3022**: 1.4% (2/146)
- **A3021**: 2.2% (3/139)
- **A3023**: 2.8% (5/179)
- **A3020**: 3.1% (4/130)
- **A3024**: 3.2% (4/126)
- **A3030**: 3.4% (7/208)
- **A3026**: 3.5% (7/199)
- **A3002**: 4.2% (8/191)
- **A3034**: 5.3% (28/533)
- **A3016**: 5.3% (2/38)
- **A3029**: 5.3% (12/226)
- **A3009**: 5.5% (6/109)
- **A3006**: 5.6% (13/233)
- **A3038**: 5.7% (11/192)
- **A3014**: 5.9% (7/118)
- **A3017**: 6.2% (2/32)
- **A3004**: 6.3% (13/207)
- **A3007**: 6.3% (9/142)
- **A3036**: 6.5% (11/169)
- **A3027**: 6.6% (16/244)
- **A3012**: 7.0% (16/228)
- **A3035**: 7.1% (12/168)
- **A3008**: 7.3% (9/124)
- **A3005**: 7.5% (10/134)
- **A3011**: 7.5% (9/120)
- **A3033**: 7.6% (12/157)
- **A3028**: 8.1% (23/285)
- **A3001**: 8.1% (3/37)
- **A3037**: 8.2% (25/304)
- **A3032**: 8.7% (15/172)
- **A3015**: 8.9% (16/180)
- **A3031**: 8.9% (25/280)
- **A3003**: 8.9% (16/179)
- **A3013**: 9.9% (14/142)
- **A3018**: 10.4% (18/173)
- **A3019**: 10.5% (21/200)
- **A3010**: 10.8% (14/130)

### Tier 2 Agents (Min 20 tickets)
- **A3040**: 2.3% (1/44)
- **A3041**: 2.6% (1/38)
- **A3042**: 4.3% (2/46)
- **A3043**: 6.6% (6/91)
- **A3044**: 8.0% (6/75)
- **A3039**: 13.6% (9/66)

## Verification: Does 'Morning team breach most' hold?

The claim that the 'Morning team breaches most' comes from two distinct analytical traps:

### Trap 1: Crediting breaches to the Resolving Agent's Shift
If we allocate breaches to the agent who *resolved* the ticket, the Morning team appears to have 2018 breaches out of 2440. However, as shown in the cross-tabulation, 1566 of these were actually created overnight when the Night shift was unstaffed, leaving the Morning team to inherit an already-breached backlog.

### Trap 2: Using UTC timestamps for Shift Attribution
If we incorrectly derive the creation shift directly from the raw UTC hours without converting to IST (+5:30):
- Day: 1643 breaches
- Morning: 424 breaches
- Night: 373 breaches

If we use the correct **IST timestamps**:
- Day: 415 breaches
- Morning: 394 breaches
- Night: 1631 breaches

**Conclusion**: Both traps unfairly shift the blame. Crediting by resolving agent blames the Morning team for the Night team's missing coverage. Failing to convert UTC to IST scrambles the shifts completely, moving the massive night-time backlog into other shifts. Once tickets are correctly attributed to their *creation time in IST*, it is unequivocally the unstaffed Night shift driving the breaches.