"""
recheck.py -- corrections for FINDINGS_0.md
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pandas as pd
import numpy as np

tickets  = pd.read_csv("data/tickets.csv")
agents   = pd.read_csv("data/agents.csv")
orders   = pd.read_csv("data/orders.csv")
products = pd.read_csv("data/products.csv")

# ── timestamps ────────────────────────────────────────────────────────────────
for c in ["created_at", "first_response_at", "resolved_at"]:
    tickets[c] = pd.to_datetime(tickets[c], utc=True, errors="coerce")

IST = "Asia/Kolkata"
tickets["created_ist"] = tickets["created_at"].dt.tz_convert(IST)
tickets["hour_ist"]    = tickets["created_ist"].dt.hour
tickets["hour_utc"]    = tickets["created_at"].dt.hour          # raw UTC hour

SLA_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}
tickets["sla_target_min"] = tickets["channel"].str.lower().map(SLA_MIN)
tickets["frt_min"]        = (
    (tickets["first_response_at"] - tickets["created_at"]).dt.total_seconds() / 60
)
tickets["breach"] = tickets["frt_min"] > tickets["sla_target_min"]

# ── DEDUP (keep helpdesk row, drop legacy_fd duplicate) ───────────────────────
dup_ids = tickets.groupby("ticket_id")["source_system"].nunique()
cross_dup_ids = set(dup_ids[dup_ids > 1].index)
# For cross-dup IDs keep the helpdesk row
dedup = (
    tickets
    .sort_values("source_system",          # "helpdesk" < "legacy_fd" alphabetically
                 key=lambda s: s.map({"helpdesk": 0, "legacy_fd": 1}))
    .drop_duplicates(subset="ticket_id", keep="first")
    .copy()
)
print(f"Raw rows          : {len(tickets)}")
print(f"After dedup       : {len(dedup)}")
print(f"Rows dropped      : {len(tickets) - len(dedup)}")

# ─────────────────────────────────────────────────────────────────────────────
# 1.  BREACH RATES ON DEDUPLICATED DATA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("BREACH RATES — DEDUPLICATED (n=11 200)")
print("="*60)

valid = dedup.dropna(subset=["frt_min", "sla_target_min"]).copy()
print(f"Tickets with computable FRT: {len(valid)}")
print(f"Breaches                   : {valid['breach'].sum()}")
print(f"Overall breach rate        : {valid['breach'].mean():.2%}")

def creation_shift_ist(h):
    if 6 <= h < 14:  return "Morning"
    if 14 <= h < 22: return "Day"
    return "Night"

def creation_shift_utc(h):
    # raw UTC hour treated as if it were IST (the bug)
    if 6 <= h < 14:  return "Morning"
    if 14 <= h < 22: return "Day"
    return "Night"

valid["shift_ist"] = valid["hour_ist"].apply(creation_shift_ist)
valid["shift_utc"] = valid["hour_utc"].apply(creation_shift_utc)

cutoff = pd.Timestamp("2025-06-30", tz=IST)
pre    = valid[valid["created_ist"] <  cutoff]
post   = valid[valid["created_ist"] >= cutoff]
print(f"\nPre  2025-06-30 : n={len(pre):,}  breach_rate={pre['breach'].mean():.2%}")
print(f"Post 2025-06-30 : n={len(post):,}  breach_rate={post['breach'].mean():.2%}")

night_mask = (valid["hour_ist"] >= 22) | (valid["hour_ist"] < 6)
night  = valid[night_mask]
other  = valid[~night_mask]
print(f"\nNight (22-06 IST): n={len(night):,}  breach_rate={night['breach'].mean():.2%}")
print(f"Other hours      : n={len(other):,}  breach_rate={other['breach'].mean():.2%}")

print("\nBreaches by creation-shift (IST, deduped):")
print(valid.groupby("shift_ist").agg(
    n=("breach","count"), breaches=("breach","sum")
).assign(rate=lambda d: d["breaches"]/d["n"]).to_string())

print("\nBreaches by channel (deduped):")
print(valid.groupby("channel").agg(
    n=("breach","count"), breaches=("breach","sum")
).assign(rate=lambda d: d["breaches"]/d["n"]).to_string())

# ─────────────────────────────────────────────────────────────────────────────
# 2.  UTC-vs-IST SHIFT ATTRIBUTION COMPARISON
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SHIFT ATTRIBUTION: IST CORRECT vs UTC RAW (deduped)")
print("="*60)

print("\nWith CORRECT IST conversion:")
ist_tbl = valid.groupby("shift_ist").agg(
    tickets=("breach","count"), breaches=("breach","sum")
).assign(rate=lambda d: d["breaches"]/d["tickets"])
print(ist_tbl.to_string())

print("\nWith WRONG UTC hours (no conversion):")
utc_tbl = valid.groupby("shift_utc").agg(
    tickets=("breach","count"), breaches=("breach","sum")
).assign(rate=lambda d: d["breaches"]/d["tickets"])
print(utc_tbl.to_string())

# Misclassified tickets (IST shift != UTC shift)
mismatch = valid[valid["shift_ist"] != valid["shift_utc"]]
print(f"\nTickets mis-classified by timezone: {len(mismatch)} ({len(mismatch)/len(valid):.1%})")
print("Cross-tab (IST shift → UTC mis-label):")
print(pd.crosstab(mismatch["shift_ist"], mismatch["shift_utc"]).to_string())

# How many Night-IST tickets are wrongly labelled Day/Morning in UTC?
night_ist = valid[valid["shift_ist"] == "Night"]
print(f"\nNight-IST tickets mislabelled in UTC:")
print(night_ist["shift_utc"].value_counts().to_string())

# ─────────────────────────────────────────────────────────────────────────────
# 3.  H7 EXTENDED — refund + replacement on same order_id or fallback join
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("H7 EXTENDED — REFUND + REPLACEMENT CHECK")
print("="*60)

# Normalise replacement_issued
dedup["repl_flag"] = dedup["replacement_issued"].str.strip().str.upper() == "Y"
dedup["has_refund"] = dedup["refund_amount_inr"] > 0

# -- same row --
same_row = dedup[dedup["has_refund"] & dedup["repl_flag"]]
print(f"\nSame-row (refund>0 AND replacement=Y): {len(same_row)}")

# -- same order_id --
# only where order_id is not null
ref_orders  = dedup[dedup["has_refund"] & dedup["order_id"].notna()][["ticket_id","order_id","refund_amount_inr","channel"]].copy()
repl_orders = dedup[dedup["repl_flag"]  & dedup["order_id"].notna()][["ticket_id","order_id","product_sku","channel"]].copy()

ref_orders.rename(columns={"ticket_id":"ref_ticket","channel":"ref_channel"}, inplace=True)
repl_orders.rename(columns={"ticket_id":"repl_ticket","channel":"repl_channel"}, inplace=True)

cross_order = ref_orders.merge(repl_orders, on="order_id", how="inner")
# exclude cases where it's the same ticket (same_row already counted)
cross_order = cross_order[cross_order["ref_ticket"] != cross_order["repl_ticket"]]
print(f"Same order_id, different tickets       : {len(cross_order)}")
print("  (unique order_ids affected)           :", cross_order["order_id"].nunique())

# -- fallback join on customer_id + product_sku (where order_id is null on either) --
ref_fallback  = dedup[dedup["has_refund"]  & dedup["order_id"].isna()][
    ["ticket_id","customer_id","product_sku","refund_amount_inr"]].copy()
repl_fallback = dedup[dedup["repl_flag"]   & dedup["order_id"].isna()][
    ["ticket_id","customer_id","product_sku"]].copy()

if len(ref_fallback) and len(repl_fallback):
    ref_fallback.rename(columns={"ticket_id":"ref_ticket"}, inplace=True)
    repl_fallback.rename(columns={"ticket_id":"repl_ticket"}, inplace=True)
    fb = ref_fallback.merge(repl_fallback, on=["customer_id","product_sku"], how="inner")
    fb = fb[fb["ref_ticket"] != fb["repl_ticket"]]
    print(f"Fallback join (cust+sku, no order_id)  : {len(fb)}")
else:
    fb = pd.DataFrame()
    print(f"Fallback join (cust+sku, no order_id)  : 0")

# -- rupee totals for cross-order cases --
if len(cross_order):
    # join product unit cost
    prod_cost = products[["sku","unit_cost_inr"]].rename(columns={"sku":"product_sku"})
    cross_with_cost = cross_order.merge(prod_cost, on="product_sku", how="left")
    cross_with_cost["replacement_cost"] = cross_with_cost["unit_cost_inr"] + 340

    # also join orders to get qty for candidate flagging
    cross_with_qty = cross_with_cost.merge(
        orders[["order_id","qty"]], on="order_id", how="left"
    )
    total_refund   = cross_with_qty["refund_amount_inr"].sum()
    total_repl_cost = cross_with_qty["replacement_cost"].sum()
    multi_qty = cross_with_qty[cross_with_qty["qty"] > 1]

    print(f"\n  Total refund amount (cross-order)   : Rs {total_refund:,.0f}")
    print(f"  Total replacement cost (cross-order): Rs {total_repl_cost:,.0f}")
    print(f"  Rows where qty > 1 (candidate only) : {len(multi_qty)}")
    print("\n  Cross-order violations detail:")
    print(cross_with_qty[[
        "order_id","ref_ticket","repl_ticket","refund_amount_inr",
        "replacement_cost","qty"
    ]].to_string(index=False))
else:
    print("\n  No cross-order cases to report.")

# ─────────────────────────────────────────────────────────────────────────────
# 4.  ROSTER — night agents ending 2025-06-29 and successor rows
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ROSTER — NIGHT AGENTS ENDING 2025-06-29")
print("="*60)

agents["from_date"] = pd.to_datetime(agents["from_date"])
agents["to_date"]   = pd.to_datetime(agents["to_date"], errors="coerce")

night_ended = agents[
    (agents["shift"] == "Night") &
    (agents["to_date"] == pd.Timestamp("2025-06-29"))
].copy()

for _, row in night_ended.iterrows():
    aid = row["agent_id"]
    later = agents[
        (agents["agent_id"] == aid) &
        (agents["from_date"] > pd.Timestamp("2025-06-29"))
    ]
    has_later = len(later) > 0
    later_detail = ""
    if has_later:
        lr = later.iloc[0]
        later_detail = f"  --> {lr['shift']} shift from {lr['from_date'].date()}"
    else:
        later_detail = "  --> NO successor row (coverage gap)"
    print(f"  {aid}  {row['name']:<25}  Team: {row['team']:<20}  {later_detail}")

print("\nDONE.")
