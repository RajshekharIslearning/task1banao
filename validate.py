import pandas as pd
import numpy as np

def get_shift(h):
    if pd.isna(h): return np.nan
    h = int(h)
    if 6 <= h < 14: return 'Morning'
    if 14 <= h < 22: return 'Day'
    return 'Night'

def main():
    # 1. Load data
    clean = pd.read_csv("out/clean.csv")
    raw = pd.read_csv("data/tickets.csv")

    # Sample 30 tickets
    sample = clean.sample(n=30, random_state=42)
    cols = ['ticket_id', 'created_at', 'created_at_ist', 'first_response_at', 'first_response_at_ist', 'frt_minutes', 'sla_target_min', 'breach']
    sample_table = f"| {' | '.join(cols)} |\n| {' | '.join(['---'] * len(cols))} |\n"
    for _, row in sample[cols].iterrows():
        sample_table += f"| {' | '.join(str(row[c]) for c in cols)} |\n"

    # 2. Compute overnight rates
    clean['created_at_dt'] = pd.to_datetime(clean['created_at'])
    clean['shift_utc'] = clean['created_at_dt'].dt.hour.apply(get_shift)
    
    breach_mask = clean['breach'].notna()
    valid = clean[breach_mask]
    
    overnight_ist_rate = valid[valid['created_shift'] == 'Night']['breach'].mean()
    overnight_utc_rate = valid[valid['shift_utc'] == 'Night']['breach'].mean()

    # 3. Effect of cleaning steps
    # Calculate initial breach rate on raw
    raw['created_at_dt'] = pd.to_datetime(raw['created_at'], utc=True, errors="coerce")
    raw['first_response_dt'] = pd.to_datetime(raw['first_response_at'], utc=True, errors="coerce")
    raw['frt_minutes'] = (raw['first_response_dt'] - raw['created_at_dt']).dt.total_seconds() / 60
    SLA_TARGETS = {"chat": 15, "voice": 120, "social": 240, "email": 480}
    raw['sla_target_min'] = raw['channel'].str.lower().map(SLA_TARGETS)
    raw['breach'] = raw['frt_minutes'] > raw['sla_target_min']
    raw.loc[raw['first_response_dt'].isna(), 'breach'] = False
    
    # Step 1: Raw
    raw_rows = len(raw)
    raw_breach_rate = raw['breach'].mean()

    # Step 2: Dedupe
    raw["_sys_order"] = raw["source_system"].map({"helpdesk": 0, "legacy_fd": 1})
    deduped = raw.sort_values(["ticket_id", "_sys_order"]).drop_duplicates(subset="ticket_id", keep="first")
    dedup_rows = len(deduped)
    dedup_breach_rate = deduped['breach'].mean()
    
    # Step 3: CSAT 0 -> Null
    csat0_count = (deduped['csat_score'] == 0).sum()
    deduped.loc[deduped['csat_score'] == 0, 'csat_score'] = np.nan
    
    with open("VALIDATION.md", "w", encoding="utf-8") as f:
        f.write("# Validation Report\n\n")
        f.write("## 1. Random Sample of 30 Tickets (Seed 42)\n\n")
        f.write(sample_table + "\n\n")
        f.write("## 2. Headline Overnight Rate: UTC vs IST\n\n")
        f.write(f"- Using IST (Correct): {overnight_ist_rate:.2%}\n")
        f.write(f"- Using UTC (Incorrect): {overnight_utc_rate:.2%}\n\n")
        f.write("## 3. Effect of Cleaning Steps\n\n")
        f.write(f"- **Raw Data**: {raw_rows:,} rows, Breach Rate: {raw_breach_rate:.2%}\n")
        f.write(f"- **After Dedupe**: {dedup_rows:,} rows (removed {raw_rows - dedup_rows:,}), Breach Rate: {dedup_breach_rate:.2%}\n")
        f.write(f"- **CSAT 0 to Null**: {csat0_count:,} zeros removed. (Breach rate unaffected).\n")

if __name__ == "__main__":
    main()
