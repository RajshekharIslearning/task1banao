import pandas as pd
import numpy as np
import pathlib

def main():
    df = pd.read_csv("out/clean.csv")
    df['created_at_ist'] = pd.to_datetime(df['created_at_ist'])
    df['resolved_at_ist'] = pd.to_datetime(df['resolved_at_ist'])
    prod = pd.read_csv("data/products.csv")

    print("--- 1. CSAT Analysis ---")
    csat = df.dropna(subset=['csat_score']).copy()
    csat['period'] = np.where(csat['created_at_ist'].dt.date < pd.to_datetime('2025-06-30').date(), 'Before 30 June 2025', 'After 30 June 2025')
    csat['is_overnight'] = np.where(csat['created_shift'] == 'Night', 'Overnight', 'Day/Morning')
    
    res = csat.groupby(['period', 'is_overnight']).agg(
        avg_csat=('csat_score', 'mean'),
        n=('csat_score', 'count')
    ).reset_index()
    for _, r in res.iterrows():
        print(f"{r['period']} | {r['is_overnight']}: {r['avg_csat']:.2f} (n={r['n']})")

    print("\n--- 2. H7: Refund + Replacement on Same Order ---")
    same_row = df[(df['refund_amount_inr'] > 0) & (df['replacement_issued'] == 'Y')]
    sr_cost = 0
    if not same_row.empty:
        sr = pd.merge(same_row, prod, how='left', left_on='product_sku', right_on='sku')
        sr_cost = sr['refund_amount_inr'].sum() + (sr['unit_cost_inr'] + 340).sum()
    print(f"Same-row cases: {len(same_row)}, cost: {sr_cost:,.2f} Rs")
    
    # We ignore the join cases for now, just the same-row cases are usually H7.

    print("\n--- 3. Repeat Contacts within 30 days ---")
    df_rep = df.dropna(subset=['customer_id', 'resolved_at_ist']).sort_values(['customer_id', 'created_at_ist'])
    df_rep['prev_resolved'] = df_rep.groupby('customer_id')['resolved_at_ist'].shift(1)
    df_rep['days_since_prev'] = (df_rep['created_at_ist'] - df_rep['prev_resolved']).dt.total_seconds() / (24*3600)
    
    repeats = df_rep[(df_rep['days_since_prev'] >= 0) & (df_rep['days_since_prev'] <= 30)]
    channel_costs = {'chat': 210, 'email': 260, 'voice': 520, 'social': 240}
    repeats_cost = repeats['channel'].str.lower().map(channel_costs).sum()
    print(f"Repeat contacts within 30 days: {len(repeats)}, cost: {repeats_cost:,.2f} Rs")

    print("\n--- 4. Avoidable Transfers ---")
    transfers = df['transfers'].sum()
    transfer_cost = transfers * 305
    print(f"Total transfers: {transfers}, cost: {transfer_cost:,.2f} Rs")
    
    print("\n--- 5. GW-OTHER Misuse ---")
    gw = df[df['refund_reason_code'] == 'GW-OTHER']
    gw_over_500 = gw[gw['refund_amount_inr'] > 500]
    excess_gw = (gw_over_500['refund_amount_inr'] - 500).sum()
    print(f"GW-OTHER cases > 500: {len(gw_over_500)}, excess amount: {excess_gw:,.2f} Rs")
    
    print("\n--- 6. Base rate stats (per Quarter) ---")
    after_june = df[df['created_at_ist'].dt.date >= pd.to_datetime('2025-06-30').date()]
    night_tickets = len(after_june[after_june['created_shift'] == 'Night'])
    print(f"Night tickets after June 30: {night_tickets} (over 4 quarters = {night_tickets/4} per quarter)")
    
    # Calculate contact cost per breached night ticket vs non-breached? 
    # Repeat contacts caused by breached tickets?
    breached_after = after_june[after_june['breach'] == True]
    print(f"Breached Night tickets after June 30: {len(after_june[(after_june['created_shift'] == 'Night') & (after_june['breach'] == True)])}")
    
    # Do breached tickets have a higher repeat rate?
    rep_mask = df_rep['days_since_prev'].notna() & (df_rep['days_since_prev'] <= 30)
    df_rep['is_repeat'] = rep_mask
    
    # We want to know if a ticket *caused* a repeat. 
    # The 'repeats' dataframe holds the *second* ticket. We want to know if the *first* ticket was breached.
    df_rep['is_prev_breached'] = df_rep.groupby('customer_id')['breach'].shift(1)
    
    repeats_from_breach = df_rep[(df_rep['is_repeat']) & (df_rep['is_prev_breached'] == True)]
    repeats_from_ok = df_rep[(df_rep['is_repeat']) & (df_rep['is_prev_breached'] == False)]
    
    total_breached = df['breach'].sum()
    total_ok = len(df) - total_breached
    
    print(f"Repeats from breached tickets: {len(repeats_from_breach)} (Rate: {len(repeats_from_breach)/total_breached:.2%})")
    print(f"Repeats from OK tickets: {len(repeats_from_ok)} (Rate: {len(repeats_from_ok)/total_ok:.2%})")

if __name__ == "__main__":
    main()
