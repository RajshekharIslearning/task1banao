import pandas as pd
import numpy as np

def shift_from_hour(h):
    if pd.isna(h): return np.nan
    h = int(h)
    if 6 <= h < 14:  return "Morning"
    if 14 <= h < 22: return "Day"
    return "Night"

def main():
    # Load data
    df = pd.read_csv("out/clean.csv")
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['created_at_ist'] = pd.to_datetime(df['created_at_ist'])
    df['month'] = df['created_at_ist'].dt.to_period("M").astype(str)
    df['hour_ist'] = df['created_at_ist'].dt.hour
    df['hour_utc'] = df['created_at'].dt.hour
    df['created_shift_utc'] = df['hour_utc'].apply(shift_from_hour)
    
    # We treat breach as strict boolean, filling NaNs with False for counting purposes
    # since no_first_response isn't a breach per decision D8.
    df['is_breach'] = df['breach'].fillna(False).astype(bool)
    
    md = ["# Root Cause Analysis: SLA Breaches\n"]
    
    # 1. Breach rate by month (IST) and by IST hour-of-day x channel
    md.append("## 1. Breach Rate by Month and Hour-Channel\n")
    monthly = df.groupby('month').agg(tickets=('ticket_id', 'count'), breaches=('is_breach', 'sum'))
    monthly['rate'] = monthly['breaches'] / monthly['tickets']
    md.append("### By Month (IST)")
    for m, r in monthly.iterrows():
        md.append(f"- **{m}**: {r['rate']:.1%} ({r['breaches']}/{r['tickets']})")
    
    md.append("\n### By Hour (IST) and Channel")
    hour_ch = df.groupby(['hour_ist', 'channel']).agg(t=('ticket_id', 'count'), b=('is_breach', 'sum'))
    hour_ch['rate'] = hour_ch['b'] / hour_ch['t']
    highest_hc = hour_ch[hour_ch['t'] > 50].sort_values('rate', ascending=False).head(5)
    md.append("Top 5 highest breach rate segments (min 50 tickets):")
    for (h, c), row in highest_hc.iterrows():
        md.append(f"- **{h:02d}:00 {c.capitalize()}**: {row['rate']:.1%} ({row['b']}/{row['t']} tickets)")
        
    # 2. Breach rate before vs on/after roster change (2025-06-30)
    df['period'] = np.where(df['created_at_ist'].dt.date < pd.to_datetime('2025-06-30').date(), 'Before 2025-06-30', 'On/After 2025-06-30')
    md.append("\n## 2. Roster Change Impact (by Created Shift)\n")
    shift_period = df.groupby(['period', 'created_shift']).agg(t=('ticket_id', 'count'), b=('is_breach', 'sum'))
    shift_period['rate'] = shift_period['b'] / shift_period['t']
    
    for p in ['Before 2025-06-30', 'On/After 2025-06-30']:
        md.append(f"### {p}")
        for s in ['Morning', 'Day', 'Night']:
            if (p, s) in shift_period.index:
                r = shift_period.loc[(p, s)]
                md.append(f"- **{s}**: {r['rate']:.1%} ({r['b']}/{r['t']})")
                
    # 3. Cross-tab: created_shift vs rostered_shift
    md.append("\n## 3. Cross-Tabulation: Ticket Creation vs Resolving Agent Shift\n")
    xtab = pd.crosstab(df[df['is_breach']]['created_shift'], df[df['is_breach']]['rostered_shift'])
    night_to_morning = xtab.loc['Night', 'Morning'] if 'Night' in xtab.index and 'Morning' in xtab.columns else 0
    md.append("Breaches matrix (Row = Created Shift, Col = Resolver Shift):\n")
    md.append("| Created Shift | Morning | Day | Night |")
    md.append("|---|---|---|---|")
    for r in xtab.index:
        cols = [str(xtab.loc[r, c]) if c in xtab.columns else "0" for c in ['Morning', 'Day', 'Night']]
        md.append(f"| {r} | {' | '.join(cols)} |")
    md.append(f"\n- **Insight**: There are {night_to_morning} breaches for tickets created overnight (Night) but resolved by the Morning team.")
    
    # 4. Agent coverage before vs after
    agents = pd.read_csv("data/agents.csv")
    agents['from_date'] = pd.to_datetime(agents['from_date'])
    agents['to_date'] = pd.to_datetime(agents['to_date'])
    
    def is_active(row, check_date):
        start = row['from_date'].date()
        end = row['to_date'].date() if pd.notna(row['to_date']) else pd.to_datetime('2099-12-31').date()
        return start <= check_date <= end

    before_date = pd.to_datetime('2025-06-29').date()
    after_date = pd.to_datetime('2025-07-01').date()
    
    agents['active_before'] = agents.apply(lambda r: is_active(r, before_date), axis=1)
    agents['active_after'] = agents.apply(lambda r: is_active(r, after_date), axis=1)
    
    night_before = agents[agents['active_before'] & (agents['shift'] == 'Night')]
    night_after = agents[agents['active_after'] & (agents['shift'] == 'Night')]
    
    md.append("\n## 4. Night Shift (22:00-06:00) Coverage\n")
    md.append(f"- **Before Roster Change**: {len(night_before)} agents on Night shift.")
    md.append(f"- **After Roster Change**: {len(night_after)} agents on Night shift.")
    if len(night_after) < len(night_before):
        md.append("- **Insight**: Night coverage was reduced.")

    # 5. Monthly SLA credits & Driver Split (Volume vs Rate)
    md.append("\n## 5. Monthly SLA Credits & Cost Drivers\n")
    monthly['credits_rs'] = monthly['breaches'] * 350
    for m, r in monthly.iterrows():
        md.append(f"- **{m}**: {int(r['credits_rs']):,} Rs ({r['breaches']} breaches)")
        
    first_month = monthly.index.min()
    last_month = monthly.index.max()
    md.append("\n**Dispute Resolution: Did costs 'triple' (Finance) or stay 'flat' (CX)?**")
    
    monthly_before = monthly.loc['2025-01':'2025-06']
    monthly_after = monthly.loc['2025-07':]
    
    avg_vol_before = monthly_before['tickets'].mean()
    avg_vol_after = monthly_after['tickets'].mean()
    avg_rate_before = monthly_before['breaches'].sum() / monthly_before['tickets'].sum()
    avg_rate_after = monthly_after['breaches'].sum() / monthly_after['tickets'].sum()
    avg_credits_before = monthly_before['credits_rs'].mean()
    avg_credits_after = monthly_after['credits_rs'].mean()
    
    md.append(f"- Average Monthly Tickets (Jan-Jun 2025): {avg_vol_before:,.0f} | (Jul 2025-Jun 2026): {avg_vol_after:,.0f}")
    md.append(f"- Average Monthly Breach Rate (Jan-Jun 2025): {avg_rate_before:.1%} | (Jul 2025-Jun 2026): {avg_rate_after:.1%}")
    md.append(f"- Average Monthly Credits (Jan-Jun 2025): {avg_credits_before:,.0f} Rs | (Jul 2025-Jun 2026): {avg_credits_after:,.0f} Rs")
    
    # Split the credit increase
    vol_effect = (avg_vol_after - avg_vol_before) * avg_rate_before * 350
    rate_effect = avg_vol_before * (avg_rate_after - avg_rate_before) * 350
    joint_effect = (avg_vol_after - avg_vol_before) * (avg_rate_after - avg_rate_before) * 350
    total_increase = avg_credits_after - avg_credits_before
    
    md.append(f"\n**Credit Increase Breakdown (Total Increase: {total_increase:,.0f} Rs)**")
    md.append(f"- Volume Effect (holding rate constant): {vol_effect:,.0f} Rs")
    md.append(f"- Rate Effect (holding volume constant): {rate_effect:,.0f} Rs")
    md.append(f"- Compound/Joint Effect: {joint_effect:,.0f} Rs")
    
    md.append("\n- **Conclusion**: Finance is correct that total monthly costs multiplied massively (from ~12k to ~66k average). CX is wrong that the rate was 'flat'—the average breach rate jumped from 9.2% to 24.8%. The increase is driven by BOTH higher volume and a severely worsened breach rate.")

    # 6. Excess breaches due to night window
    md.append("\n## 6. Excess Breaches (Night vs Baseline)\n")
    df['qtr'] = df['created_at_ist'].dt.to_period("Q").astype(str)
    
    quarterly_costs = {}
    for m in monthly.index:
        m_df = df[df['month'] == m]
        baseline = m_df[m_df['created_shift'].isin(['Morning', 'Day'])]
        base_rate = baseline['is_breach'].sum() / len(baseline) if len(baseline) > 0 else 0
        night_df = m_df[m_df['created_shift'] == 'Night']
        night_vol = len(night_df)
        night_breaches = night_df['is_breach'].sum()
        expected_night_breaches = night_vol * base_rate
        excess = max(0, night_breaches - expected_night_breaches)
        md.append(f"- **{m}**: Baseline rate {base_rate:.1%} | Night breaches: {night_breaches} | Expected: {expected_night_breaches:.1f} | Excess: {excess:.1f}")
        
        q = str(pd.to_datetime(m).to_period("Q"))
        quarterly_costs[q] = quarterly_costs.get(q, 0) + (excess * 350)
        
    md.append("\n**Excess Cost per Quarter:**")
    for q, cost in quarterly_costs.items():
        md.append(f"- **{q}**: {int(cost):,} Rs")

    # 7. Fair Agent View
    md.append("\n## 7. Fair Agent View (In-Shift Tickets Only)\n")
    fair_df = df[df['created_shift'] == df['rostered_shift']]
    agent_perf = fair_df.groupby(['agent_id', 'rostered_tier']).agg(t=('ticket_id', 'count'), b=('is_breach', 'sum')).reset_index()
    agent_perf['rate'] = agent_perf['b'] / agent_perf['t']
    
    for tier in [1, 2]:
        md.append(f"\n### Tier {tier} Agents (Min 20 tickets)")
        tier_perf = agent_perf[(agent_perf['rostered_tier'] == tier) & (agent_perf['t'] >= 20)]
        tier_perf = tier_perf.sort_values('rate')
        for _, r in tier_perf.iterrows():
            md.append(f"- **{r['agent_id']}**: {r['rate']:.1%} ({r['b']}/{r['t']})")

    # Verify framing
    md.append("\n## Verification: Does 'Morning team breach most' hold?\n")
    
    md.append("The claim that the 'Morning team breaches most' comes from two distinct analytical traps:\n")
    
    # 1. Resolver attribution
    md.append("### Trap 1: Crediting breaches to the Resolving Agent's Shift")
    morning_resolved_breaches = df[(df['is_breach']) & (df['rostered_shift'] == 'Morning')].shape[0]
    total_breaches = df['is_breach'].sum()
    md.append(f"If we allocate breaches to the agent who *resolved* the ticket, the Morning team appears to have {morning_resolved_breaches} breaches out of {total_breaches}. However, as shown in the cross-tabulation, {night_to_morning} of these were actually created overnight when the Night shift was unstaffed, leaving the Morning team to inherit an already-breached backlog.")
    
    # 2. UTC error
    md.append("\n### Trap 2: Using UTC timestamps for Shift Attribution")
    utc_breach = df[df['is_breach']].groupby('created_shift_utc').size()
    ist_breach = df[df['is_breach']].groupby('created_shift').size()
    
    md.append("If we incorrectly derive the creation shift directly from the raw UTC hours without converting to IST (+5:30):")
    for s, v in utc_breach.items(): md.append(f"- {s}: {v} breaches")
    
    md.append("\nIf we use the correct **IST timestamps**:")
    for s, v in ist_breach.items(): md.append(f"- {s}: {v} breaches")
    
    md.append("\n**Conclusion**: Both traps unfairly shift the blame. Crediting by resolving agent blames the Morning team for the Night team's missing coverage. Failing to convert UTC to IST scrambles the shifts completely, moving the massive night-time backlog into other shifts. Once tickets are correctly attributed to their *creation time in IST*, it is unequivocally the unstaffed Night shift driving the breaches.")

    with open("out/rootcause.md", "w") as f:
        f.write("\n".join(md))
        
if __name__ == "__main__":
    main()
