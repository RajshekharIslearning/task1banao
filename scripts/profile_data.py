"""
profile_data.py  --  Step 1 orientation for Vireo Audio SLA tool.
Reads every doc and CSV; produces counts for FINDINGS_0.md and H1-H7 checks.
Run: python profile_data.py > profile_out.txt 2>&1
"""
import sys, pathlib, textwrap
import pandas as pd
import numpy as np

# Force UTF-8 output so any Unicode in data doesn't crash the terminal
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = pathlib.Path("data")
DOCS = pathlib.Path("docs")

SEP = "=" * 70

# ── helpers ──────────────────────────────────────────────────────────────────
def sec(title):
    print(f"\n{SEP}\n{title}\n{SEP}")

def read_doc(path):
    """Try utf-8 then latin-1."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="latin-1")
        except Exception as e:
            return f"[COULD NOT READ: {e}]"

# ============================================================
# 0. READ ALL DOCS
# ============================================================
sec("READING DOCS")
for fname in sorted(DOCS.iterdir()):
    content = read_doc(fname)
    print(f"\n{'─'*60}")
    print(f"FILE: {fname.name}  ({len(content)} chars)")
    print('─'*60)
    # Print first 3000 chars so we catch all policy numbers
    print(content[:4000])
    if len(content) > 4000:
        print(f"... [truncated, total {len(content)} chars]")

# ============================================================
# 1. LOAD ALL CSVs
# ============================================================
sec("LOADING CSVs")

tickets   = pd.read_csv(DATA / "tickets.csv")
agents    = pd.read_csv(DATA / "agents.csv")
orders    = pd.read_csv(DATA / "orders.csv")
customers = pd.read_csv(DATA / "customers.csv")
products  = pd.read_csv(DATA / "products.csv")

for name, df in [("tickets", tickets), ("agents", agents),
                 ("orders", orders), ("customers", customers),
                 ("products", products)]:
    print(f"\n--- {name}.csv  shape={df.shape} ---")
    print(df.dtypes.to_string())
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        print("  Nulls:")
        print(nulls.to_string())
    else:
        print("  Nulls: none")

# ============================================================
# 2. TICKETS DEEP DIVE
# ============================================================
sec("TICKETS DEEP DIVE")

ts_cols = ["created_at", "first_response_at", "resolved_at"]
for c in ts_cols:
    tickets[c] = pd.to_datetime(tickets[c], utc=True, errors="coerce")

print(f"\nTotal rows            : {len(tickets)}")
print(f"Unique ticket_ids     : {tickets['ticket_id'].nunique()}")
print(f"Duplicate ticket_ids  : {tickets.duplicated(subset='ticket_id').sum()}")

# cross-system dups (same ID in both source systems)
dup_sys = tickets.groupby("ticket_id")["source_system"].nunique()
cross_dup_count = (dup_sys > 1).sum()
print(f"IDs in BOTH systems   : {cross_dup_count}")

print("\nsource_system value counts:")
print(tickets["source_system"].value_counts().to_string())

raw_min = tickets["created_at"].min()
raw_max = tickets["created_at"].max()
print(f"\ncreated_at range (UTC): {raw_min}  to  {raw_max}")
print(f"first_response_at NaT : {tickets['first_response_at'].isna().sum()}")
print(f"resolved_at NaT       : {tickets['resolved_at'].isna().sum()}")

print("\nstatus value counts:")
print(tickets["status"].value_counts().to_string())

print("\nchannel value counts:")
print(tickets["channel"].value_counts().to_string())

print("\npriority value counts:")
print(tickets["priority"].value_counts().to_string())

print("\ncategory value counts (top 20):")
print(tickets["category"].value_counts().head(20).to_string())

# ---- CSAT ----
print("\ncsat_score value counts (incl NaN):")
print(tickets["csat_score"].value_counts(dropna=False).sort_index().to_string())
csat_zero = (tickets["csat_score"] == 0).sum()
csat_null = tickets["csat_score"].isna().sum()
print(f"\n  csat=0   : {csat_zero}")
print(f"  csat=NaN : {csat_null}")
print("  csat=0 by source_system:")
print(tickets[tickets["csat_score"] == 0]["source_system"].value_counts().to_string())

# ---- REFUND ----
print("\nrefund_amount_inr stats by source_system:")
print(tickets.groupby("source_system")["refund_amount_inr"].describe().to_string())
print("\nMax refund by source_system:")
print(tickets.groupby("source_system")["refund_amount_inr"].max().to_string())
print("Median non-zero refund by source_system:")
nonzero_refund = tickets[tickets["refund_amount_inr"] > 0]
print(nonzero_refund.groupby("source_system")["refund_amount_inr"].median().to_string())

# ---- REPLACEMENT + REFUND ----
print("\nreplacement_issued value counts:")
print(tickets["replacement_issued"].value_counts(dropna=False).to_string())

both_on_ticket = tickets[
    (tickets["refund_amount_inr"] > 0) &
    (tickets["replacement_issued"].str.strip().str.lower() == "yes")
]
print(f"\nTickets with BOTH refund>0 AND replacement=yes: {len(both_on_ticket)}")
print("  By source_system:")
print(both_on_ticket["source_system"].value_counts().to_string())

# ---- FAILED IVR ----
voice = tickets[tickets["channel"] == "voice"]
print(f"\nVoice tickets total: {len(voice)}")
null_vm  = voice["customer_message"].isna().sum()
short_vm = (voice["customer_message"].fillna("").str.strip().str.len() < 10).sum()
kw_vm    = voice["customer_message"].fillna("").str.lower().str.contains(
               r"ivr|transcript|failed|inaudible|\[noise\]", regex=True).sum()
print(f"  customer_message null          : {null_vm}")
print(f"  customer_message len<10        : {short_vm}")
print(f"  customer_message IVR-keywords  : {kw_vm}")
print(f"  Likely failed IVR (null+short) : {short_vm}")

# ---- ORPHAN KEYS ----
ticket_agent_ids  = set(tickets["agent_id"].dropna().unique())
roster_agent_ids  = set(agents["agent_id"].unique())
orphan_agents     = ticket_agent_ids - roster_agent_ids
print(f"\nAgent IDs in tickets not in agents.csv : {len(orphan_agents)}")
if orphan_agents:
    print(f"  : {sorted(orphan_agents)[:10]}")

ticket_order_ids  = set(tickets["order_id"].dropna().unique())
order_ids         = set(orders["order_id"].unique())
orphan_orders     = ticket_order_ids - order_ids
print(f"Order IDs in tickets not in orders.csv : {len(orphan_orders)}")
if orphan_orders:
    print(f"  sample: {sorted(orphan_orders)[:5]}")

ticket_cust_ids   = set(tickets["customer_id"].dropna().unique())
cust_ids          = set(customers["customer_id"].unique())
orphan_custs      = ticket_cust_ids - cust_ids
print(f"Customer IDs in tickets not in customers.csv: {len(orphan_custs)}")

missing_order = tickets["order_id"].isna().sum()
print(f"Tickets with missing order_id  : {missing_order}  ({missing_order/len(tickets)*100:.1f}%)")

print("\nrefund_reason_code value counts (incl NaN):")
print(tickets["refund_reason_code"].value_counts(dropna=False).to_string())

print("\ntransfers stats:")
print(tickets["transfers"].describe().to_string())
print("transfers value counts:")
print(tickets["transfers"].value_counts().to_string())

# ============================================================
# 3. TIMEZONE + SHIFT + BREACH ANALYSIS  (H1, H3, H4, H5)
# ============================================================
sec("TIMEZONE / SHIFT / BREACH ANALYSIS")

IST = "Asia/Kolkata"
tickets["created_ist"]        = tickets["created_at"].dt.tz_convert(IST)
tickets["first_response_ist"] = tickets["first_response_at"].dt.tz_convert(IST)
tickets["hour_ist"]           = tickets["created_ist"].dt.hour

print("\nH1 check -- raw created_at sample (first 5 rows):")
raw_check = pd.read_csv(DATA / "tickets.csv", usecols=["created_at", "first_response_at"], nrows=5)
print(raw_check.to_string())
print("\nIf timestamps end in 'Z' or '+00:00' or have no offset they are UTC.")

print("\nHour-of-day distribution in IST (all tickets):")
print(tickets["hour_ist"].value_counts().sort_index().to_string())

# ---- compute breach ----
SLA_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}
tickets["sla_target_min"] = tickets["channel"].str.lower().map(SLA_MIN)
tickets["frt_min"]        = (
    (tickets["first_response_at"] - tickets["created_at"]).dt.total_seconds() / 60
)
tickets["breach"] = tickets["frt_min"] > tickets["sla_target_min"]

valid = tickets.dropna(subset=["frt_min", "sla_target_min"]).copy()
print(f"\nTickets with computable FRT  : {len(valid)}")
print(f"Breaches (raw, no dedup)     : {valid['breach'].sum()}")
print(f"Overall breach rate          : {valid['breach'].mean():.2%}")

# ---- weekly breach rate ----
valid["week"] = valid["created_ist"].dt.to_period("W")
weekly = valid.groupby("week").agg(
    n=("breach","count"), breaches=("breach","sum")
).assign(rate=lambda d: d["breaches"]/d["n"])

print("\nWeekly breach rate (IST, all channels):")
print(weekly.to_string())

# ---- H3: pre vs post 2025-06-30 ----
cutoff = pd.Timestamp("2025-06-30", tz=IST)
pre  = valid[valid["created_ist"] <  cutoff]
post = valid[valid["created_ist"] >= cutoff]
print(f"\nH3 -- Pre-cutoff  (<2025-06-30) : n={len(pre):,}  breach_rate={pre['breach'].mean():.2%}")
print(f"H3 -- Post-cutoff (>=2025-06-30): n={len(post):,}  breach_rate={post['breach'].mean():.2%}")

# ---- H4: night-hour slice ----
night_mask = (valid["hour_ist"] >= 22) | (valid["hour_ist"] < 6)
night  = valid[night_mask]
dayhrs = valid[~night_mask]
print(f"\nH4 -- Night (22-06 IST) tickets : {len(night):,}  breach_rate={night['breach'].mean():.2%}")
print(f"H4 -- Other-hour tickets        : {len(dayhrs):,}  breach_rate={dayhrs['breach'].mean():.2%}")

print("\nH4 -- Night breach rate by channel:")
print(night.groupby("channel").agg(
    n=("breach","count"), br=("breach","sum")
).assign(rate=lambda d: d["br"]/d["n"]).to_string())

# night, post-cutoff
post_night = valid[(valid["created_ist"] >= cutoff) & night_mask]
print(f"\nH4 -- Post-cutoff night tickets : {len(post_night):,}  breach_rate={post_night['breach'].mean():.2%}")

# agents whose night shift ended 2025-06-29
agents["from_date"] = pd.to_datetime(agents["from_date"])
agents["to_date"]   = pd.to_datetime(agents["to_date"], errors="coerce")
night_ended = agents[
    (agents["shift"] == "Night") &
    (agents["to_date"] == pd.Timestamp("2025-06-29"))
]
print(f"\nH4 -- Night-roster rows ending 2025-06-29: {len(night_ended)}")
print(night_ended[["agent_id","name","shift","from_date","to_date"]].to_string())

# ---- H5: shift of creation time vs who resolves ----
def creation_shift(h):
    if 6 <= h < 14:  return "Morning"
    if 14 <= h < 22: return "Day"
    return "Night"

valid["creation_shift"] = valid["hour_ist"].apply(creation_shift)
print("\nH5 -- Breach count/rate by creation-shift:")
print(valid.groupby("creation_shift").agg(
    n=("breach","count"), breaches=("breach","sum")
).assign(rate=lambda d: d["breaches"]/d["n"]).to_string())

# ---- H5: who actually resolves overnight-created breached tickets? ----
overnight_breaches = valid[valid["creation_shift"] == "Night"][valid["breach"] == True].copy()
print(f"\nH5 -- Overnight-created breaches : {len(overnight_breaches)}")
# Check agent shift assignment via roster at ticket date
# (simple: join agent's shift at ticket date)
def get_agent_shift(agent_id, ticket_date):
    rows = agents[(agents["agent_id"] == agent_id) &
                  (agents["from_date"] <= ticket_date) &
                  ((agents["to_date"].isna()) | (agents["to_date"] >= ticket_date))]
    if len(rows):
        return rows.iloc[0]["shift"]
    return "Unknown"

overnight_breaches["created_date"] = overnight_breaches["created_ist"].dt.normalize()
# Sample first 200 for speed
sample_ob = overnight_breaches.head(200).copy()
sample_ob["resolver_shift"] = sample_ob.apply(
    lambda r: get_agent_shift(r["agent_id"], r["created_date"]), axis=1
)
print("H5 -- Resolver shift for overnight-created breaches (sample 200):")
print(sample_ob["resolver_shift"].value_counts().to_string())

# ============================================================
# 4. REFUND ANALYSIS  (H6, H7)
# ============================================================
sec("REFUND ANALYSIS (H6, H7)")

print(f"\norders.csv shape: {orders.shape}")
print(orders.dtypes.to_string())
print("\norder_value_inr stats:")
print(orders["order_value_inr"].describe().to_string())

# join tickets to orders to compare refund vs order value
merged = tickets.merge(
    orders[["order_id","order_value_inr"]], on="order_id", how="left"
)
has_refund = merged[merged["refund_amount_inr"] > 0].copy()
has_refund["refund_ratio"] = has_refund["refund_amount_inr"] / has_refund["order_value_inr"]

print(f"\nTickets with refund>0 and matched order: {has_refund['order_value_inr'].notna().sum()}")
print("\nrefund_ratio stats by source_system:")
print(has_refund.groupby("source_system")["refund_ratio"].describe().to_string())

print("\nrefund_ratio > 5 (likely paise vs rupees mismatch):")
paise = has_refund[has_refund["refund_ratio"] > 5]
print(f"  Count: {len(paise)}")
print("  By source_system:")
print(paise["source_system"].value_counts().to_string())

print("\nSample rows with very high refund_ratio (potential paise issue):")
print(has_refund.nlargest(10, "refund_ratio")[
    ["ticket_id","source_system","refund_amount_inr","order_value_inr","refund_ratio"]
].to_string())

# H7: same ORDER gets both refund ticket AND replacement ticket
order_has_refund      = set(tickets[tickets["refund_amount_inr"] > 0]["order_id"].dropna())
order_has_replacement = set(tickets[tickets["replacement_issued"].str.strip().str.lower() == "yes"]["order_id"].dropna())
both_orders = order_has_refund & order_has_replacement
print(f"\nH7 -- Orders with a refund ticket AND a replacement ticket : {len(both_orders)}")
print(f"H7 -- Tickets with BOTH on same row                       : {len(both_on_ticket)}")

# ============================================================
# 5. AGENTS ROSTER QUALITY
# ============================================================
sec("AGENTS ROSTER QUALITY")

print(f"Roster rows    : {len(agents)}")
print(f"Unique agent_ids: {agents['agent_id'].nunique()}")
print("\nShift value counts:")
print(agents["shift"].value_counts().to_string())

print("\nAgents with multiple roster rows (shift changes):")
multi = agents[agents.duplicated(subset="agent_id", keep=False)].sort_values("agent_id")
print(multi.to_string())

print("\nto_date nulls (still active):", agents["to_date"].isna().sum())
print("\nFull agents roster:")
print(agents.to_string())

# ============================================================
# 6. CUSTOMERS & PRODUCTS
# ============================================================
sec("CUSTOMERS & PRODUCTS")

print(f"\ncustomers.csv shape: {customers.shape}")
print(customers.dtypes.to_string())
print("\ncustomers sample (5 rows):")
print(customers.head().to_string())

print(f"\nproducts.csv shape: {products.shape}")
print(products.to_string())

print("\n\nDONE -- all checks complete.")
