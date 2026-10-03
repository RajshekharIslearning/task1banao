import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pandas as pd, numpy as np

tickets = pd.read_csv("data/tickets.csv")
agents  = pd.read_csv("data/agents.csv")
orders  = pd.read_csv("data/orders.csv")

for c in ["created_at","first_response_at","resolved_at"]:
    tickets[c] = pd.to_datetime(tickets[c], utc=True, errors="coerce")

IST = "Asia/Kolkata"
tickets["created_ist"] = tickets["created_at"].dt.tz_convert(IST)
tickets["hour_ist"]    = tickets["created_ist"].dt.hour

SLA_MIN = {"chat":15,"voice":120,"social":240,"email":480}
tickets["sla_target_min"] = tickets["channel"].str.lower().map(SLA_MIN)
tickets["frt_min"] = (tickets["first_response_at"]-tickets["created_at"]).dt.total_seconds()/60
tickets["breach"]  = tickets["frt_min"] > tickets["sla_target_min"]

def creation_shift(h):
    if 6 <= h < 14: return "Morning"
    if 14 <= h < 22: return "Day"
    return "Night"
tickets["creation_shift"] = tickets["hour_ist"].apply(creation_shift)
valid = tickets.dropna(subset=["frt_min","sla_target_min"]).copy()

# H5 -- resolver shift for overnight-created breaches
agents["from_dt"] = pd.to_datetime(agents["from_date"]).dt.tz_localize(None)
agents["to_dt"]   = pd.to_datetime(agents["to_date"], errors="coerce").dt.tz_localize(None)

overnight_breaches = valid[(valid["creation_shift"]=="Night") & (valid["breach"]==True)].copy()
print(f"H5 -- overnight-created breaches: {len(overnight_breaches)}")

def get_agent_shift(agent_id, ticket_ts):
    ts = ticket_ts.replace(tzinfo=None)  # strip tz for naive comparison
    rows = agents[
        (agents["agent_id"] == agent_id) &
        (agents["from_dt"] <= ts) &
        ((agents["to_dt"].isna()) | (agents["to_dt"] >= ts))
    ]
    if len(rows): return rows.iloc[0]["shift"]
    return "Unknown"

sample = overnight_breaches.head(300).copy()
sample["resolver_shift"] = sample.apply(
    lambda r: get_agent_shift(r["agent_id"], r["created_ist"]), axis=1
)
print("H5 -- resolver shift for overnight-created breaches (sample 300):")
print(sample["resolver_shift"].value_counts().to_string())
print()

# Full set
overnight_breaches["resolver_shift"] = overnight_breaches.apply(
    lambda r: get_agent_shift(r["agent_id"], r["created_ist"]), axis=1
)
print("H5 -- resolver shift FULL overnight-created breaches:")
print(overnight_breaches["resolver_shift"].value_counts().to_string())
print()

# H6: refund unit mismatch
merged = tickets.merge(orders[["order_id","order_value_inr"]], on="order_id", how="left")
has_refund = merged[merged["refund_amount_inr"] > 0].copy()
has_refund["refund_ratio"] = has_refund["refund_amount_inr"] / has_refund["order_value_inr"]
print("H6 -- refund_ratio stats by source_system:")
print(has_refund.groupby("source_system")["refund_ratio"].describe().to_string())
paise = has_refund[has_refund["refund_ratio"] > 5]
print(f"H6 -- rows where refund > 5x order value: {len(paise)}")
print(paise["source_system"].value_counts().to_string())
print("\nH6 -- top 10 by refund_ratio:")
print(has_refund.nlargest(10,"refund_ratio")[
    ["ticket_id","source_system","refund_amount_inr","order_value_inr","refund_ratio"]
].to_string())

# H7
order_refund = set(tickets[tickets["refund_amount_inr"]>0]["order_id"].dropna())
order_replac = set(tickets[tickets["replacement_issued"].str.strip().str.lower()=="yes"]["order_id"].dropna())
both = order_refund & order_replac
print(f"\nH7 -- orders with refund ticket AND replacement ticket: {len(both)}")
mask_both_row = (tickets["refund_amount_inr"]>0) & (tickets["replacement_issued"].str.strip().str.lower()=="yes")
print(f"H7 -- tickets with both on same row                 : {mask_both_row.sum()}")
