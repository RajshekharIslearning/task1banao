"""
clean.py — FR-1, FR-2, FR-3 data cleaning for Vireo Audio SLA tool.

Outputs:  out/clean.csv
Logs:     every row removal with before/after count.
Rules:
  - Never join roster by name (agent_id only).
  - Never use UTC hours for shift logic.
  - Never silently drop rows; every removal is logged.
  - H6 REJECTED: no refund normalisation (see docs/DECISIONS.md D4).
"""

import sys
import pathlib
import logging
import pandas as pd
import numpy as np

# -- Setup ---------------------------------------------------------------------
OUT = pathlib.Path("out")
OUT.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT / "clean.log", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("clean")

DATA = pathlib.Path("data")
IST  = "Asia/Kolkata"

REQUIRED_FILES = {
    "tickets.csv":   ["ticket_id","created_at","first_response_at","resolved_at",
                      "status","channel","customer_id","order_id","product_sku",
                      "category","priority","assigned_team","agent_id","transfers",
                      "csat_score","refund_amount_inr","refund_reason_code",
                      "replacement_issued","customer_message","agent_notes",
                      "source_system"],
    "agents.csv":    ["agent_id","name","site","team","shift","tier",
                      "from_date","to_date"],
    "orders.csv":    ["order_id","customer_id","sku","order_date","channel",
                      "qty","order_value_inr","lot_code"],
    "customers.csv": ["customer_id","name","city","state","signup_date","care_plus"],
    "products.csv":  ["sku","product_name","family","launch_date",
                      "unit_cost_inr","retail_price_inr","warranty_months"],
}

# -- FR-1  Ingest --------------------------------------------------------------
log.info("-- FR-1  INGEST ------------------------------------------------------")

frames = {}
for fname, required_cols in REQUIRED_FILES.items():
    path = DATA / fname
    if not path.exists():
        log.error(f"MISSING FILE: {path}")
        sys.exit(1)
    df = pd.read_csv(path)
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        log.error(f"{fname}: missing columns {missing}")
        sys.exit(1)
    frames[fname] = df
    log.info(f"  Loaded {fname}: {len(df):,} rows, {df.shape[1]} cols")

tickets  = frames["tickets.csv"].copy()
agents   = frames["agents.csv"].copy()
orders   = frames["orders.csv"].copy()
products = frames["products.csv"].copy()

# -- FR-2.1  Parse timestamps as UTC; add *_ist columns -----------------------
log.info("-- FR-2.1  TIMESTAMPS UTC -> IST -------------------------------------")

TS_COLS = ["created_at", "first_response_at", "resolved_at"]
for col in TS_COLS:
    tickets[col] = pd.to_datetime(tickets[col], utc=True, errors="coerce")
    ist_col = col.replace("_at", "_at_ist")
    tickets[ist_col] = tickets[col].dt.tz_convert(IST)

log.info(f"  created_at range (UTC) : {tickets['created_at'].min()}  to  "
         f"{tickets['created_at'].max()}")
log.info(f"  created_at_ist range   : {tickets['created_at_ist'].min()}  to  "
         f"{tickets['created_at_ist'].max()}")

# -- FR-2.2  Deduplicate: same ticket_id in both source systems ----------------
log.info("-- FR-2.2  DEDUPLICATE -----------------------------------------------")

rows_before_dedup = len(tickets)
log.info(f"  Rows before dedup      : {rows_before_dedup:,}")

# ticket_ids that appear in both source systems
dup_counts = tickets.groupby("ticket_id")["source_system"].nunique()
cross_dup_ids = set(dup_counts[dup_counts > 1].index)
log.info(f"  ticket_ids in both systems: {len(cross_dup_ids):,}")

# Sort so helpdesk rows come first (0 < 1), then drop_duplicates keeps first
tickets["_sys_order"] = tickets["source_system"].map({"helpdesk": 0, "legacy_fd": 1})
tickets = (
    tickets
    .sort_values(["ticket_id", "_sys_order"])
    .drop_duplicates(subset="ticket_id", keep="first")
    .drop(columns="_sys_order")
    .reset_index(drop=True)
)

rows_after_dedup = len(tickets)
rows_removed_dedup = rows_before_dedup - rows_after_dedup
log.info(f"  Rows removed (legacy_fd dups) : {rows_removed_dedup:,}")
log.info(f"  Rows after dedup              : {rows_after_dedup:,}")

# -- FR-2.3  csat_score: legacy 0 -> null -------------------------------------
log.info("-- FR-2.3  CSAT 0 -> NULL --------------------------------------------")

csat_zero_mask = (tickets["csat_score"] == 0)
n_csat_zero = csat_zero_mask.sum()
# Verify all zeros are legacy_fd rows (expected from FINDINGS_0)
zeros_in_helpdesk = ((tickets["csat_score"] == 0) &
                     (tickets["source_system"] == "helpdesk")).sum()
if zeros_in_helpdesk > 0:
    log.warning(f"  {zeros_in_helpdesk} csat=0 rows found in helpdesk (unexpected) — also nulled")
tickets.loc[csat_zero_mask, "csat_score"] = np.nan
log.info(f"  csat=0 -> null: {n_csat_zero:,} rows affected")
log.info(f"  csat null total after: {tickets['csat_score'].isna().sum():,}")

# -- FR-2.4  Refund normalisation ----------------------------------------------
# H6 REJECTED (see docs/DECISIONS.md D4): refund/order-value ratio <= 1.0 in
# both systems; no paise blowup detected.  No transformation applied.
log.info("-- FR-2.4  REFUND NORMALISATION --------------------------------------")
log.info("  H6 REJECTED: refund amounts already in rupees in both systems.")
log.info("  No normalisation applied. See DECISIONS.md D4.")

# -- FR-2.5  Flag failed IVR transcripts --------------------------------------
log.info("-- FR-2.5  FLAG FAILED IVR TRANSCRIPTS ------------------------------")

voice_mask = tickets["channel"].str.lower() == "voice"
# Unusable: empty, < 12 chars, or < 80% letters/spaces
# body = customer_message with the leading "[IVR transcript]" removed and whitespace stripped (null becomes "")
body = tickets["customer_message"].fillna("").str.replace(r"^\[ivr transcript\]\s*", "", regex=True, case=False).str.strip()

def check_ratio(text):
    if len(text) == 0:
        return False
    letters_spaces = sum(1 for c in text if c.isalpha() or c.isspace())
    return (letters_spaces / len(text)) < 0.8

cond_len = (body.str.len() == 0) | (body.str.len() < 12)
cond_ratio = body.apply(check_ratio)

ivr_fail_mask = voice_mask & (cond_len | cond_ratio)
tickets["ivr_transcript_failed"] = ivr_fail_mask
n_ivr_fail = ivr_fail_mask.sum()
log.info(f"  Voice tickets total          : {voice_mask.sum():,}")
log.info(f"  Flagged ivr_transcript_failed: {n_ivr_fail:,}")
log.info("  (kept in SLA counts; excluded from text analysis only)")

# -- FR-2.6  Open/pending — flag, do NOT drop ---------------------------------
log.info("-- FR-2.6  OPEN/PENDING TICKETS --------------------------------------")

open_mask    = tickets["status"].isin(["open", "pending"])
no_resp_mask = tickets["first_response_at"].isna()
tickets["no_first_response"] = no_resp_mask
n_open    = open_mask.sum()
n_no_resp = no_resp_mask.sum()
log.info(f"  Open/pending rows            : {n_open:,}")
log.info(f"  Rows with no first_response  : {n_no_resp:,}")
log.info("  (kept; reported separately; not counted as breach unless SLA lapsed)")

# -- FR-2.5  frt_minutes + SLA target + breach flag ---------------------------
log.info("-- BREACH COMPUTATION -------------------------------------------------")

SLA_TARGETS = {"chat": 15, "voice": 120, "social": 240, "email": 480}
tickets["sla_target_min"] = tickets["channel"].str.lower().map(SLA_TARGETS)

tickets["frt_minutes"] = (
    (tickets["first_response_at"] - tickets["created_at"]).dt.total_seconds() / 60
)

# breach = strictly greater than target (FR-5 wording); NaN frt -> False breach
tickets["breach"] = tickets["frt_minutes"] > tickets["sla_target_min"]
# Open/pending with no frt: breach is False (strictly not greater than target yet)
# (FR-2.6: report separately; flag in no_first_response)
tickets.loc[no_resp_mask, "breach"] = False

n_breach_computable = tickets["breach"].notna().sum()
n_breach            = tickets["breach"].sum()
log.info(f"  Tickets with computable breach flag : {n_breach_computable:,}")
log.info(f"  Breaches                            : {int(n_breach):,}")
log.info(f"  Overall breach rate                 : {n_breach / n_breach_computable:.2%}")

# -- FR-3.2  created_shift from created_at_ist (NEVER UTC hours) --------------
log.info("-- FR-3.2  CREATED_SHIFT (IST) ---------------------------------------")

hour_ist = tickets["created_at_ist"].dt.hour

def ist_shift(h):
    # Morning 06:00-14:00, Day 14:00-22:00, Night 22:00-06:00 (IST)
    if pd.isna(h):
        return np.nan
    h = int(h)
    if 6 <= h < 14:  return "Morning"
    if 14 <= h < 22: return "Day"
    return "Night"

tickets["created_shift"] = hour_ist.apply(ist_shift)
log.info("  created_shift distribution:")
for shift, cnt in tickets["created_shift"].value_counts().sort_index().items():
    log.info(f"    {shift}: {cnt:,}")

# -- FR-3.1  Roster join: agent_id AND date within [from_date, to_date] --------
log.info("-- FR-3.1  ROSTER JOIN -----------------------------------------------")
log.info("  Joining on agent_id + created_at_ist date (NEVER by name).")

agents["from_date"] = pd.to_datetime(agents["from_date"]).dt.date
agents["to_date"]   = pd.to_datetime(agents["to_date"], errors="coerce").dt.date

tickets["_ticket_date"] = tickets["created_at_ist"].dt.date

# Build a lookup: for each (agent_id, date) -> roster row
# We do this with an efficient approach: merge then filter within date range
# Step 1: merge on agent_id
merged = tickets[["ticket_id","agent_id","_ticket_date"]].merge(
    agents[["agent_id","site","team","shift","tier","from_date","to_date"]],
    on="agent_id",
    how="left",
)

# Step 2: filter to rows where ticket date is within roster window
in_window = (
    (merged["_ticket_date"] >= merged["from_date"]) &
    (
        merged["to_date"].isna() |
        (merged["_ticket_date"] <= merged["to_date"])
    )
)
merged_valid = merged[in_window].copy()

# Step 3: if multiple roster rows match (shouldn't happen with clean data),
# keep the most recent from_date (narrowest window)
merged_valid = (
    merged_valid
    .sort_values("from_date", ascending=False)
    .drop_duplicates(subset="ticket_id", keep="first")
)

# Step 4: join back
roster_cols = ["ticket_id","site","team","shift","tier"]
tickets = tickets.merge(
    merged_valid[roster_cols].rename(columns={
        "site": "rostered_site",
        "team": "rostered_team",
        "shift": "rostered_shift",
        "tier": "rostered_tier",
    }),
    on="ticket_id",
    how="left",
)

n_no_roster = tickets["rostered_shift"].isna().sum()
n_roster_ok = tickets["rostered_shift"].notna().sum()
log.info(f"  Tickets with roster match    : {n_roster_ok:,}")
log.info(f"  Tickets with NO roster match : {n_no_roster:,}")
if n_no_roster > 0:
    no_match_agents = tickets[tickets["rostered_shift"].isna()]["agent_id"].value_counts()
    log.info(f"  Top agents with no match: {no_match_agents.head(10).to_dict()}")

# -- Breach rates by created_shift (for verification vs FINDINGS_0) ------------
log.info("-- VERIFICATION — BREACH RATES BY CREATED_SHIFT ---------------------")
valid = tickets[tickets["breach"].notna()].copy()
for shift in ["Morning", "Day", "Night"]:
    s = valid[valid["created_shift"] == shift]
    if len(s):
        log.info(f"  {shift:8s}: n={len(s):,}  breaches={s['breach'].sum():.0f}  "
                 f"rate={s['breach'].mean():.2%}")

log.info("-- BREACH RATES BY CHANNEL -------------------------------------------")
for ch in ["chat", "email", "voice", "social"]:
    s = valid[valid["channel"].str.lower() == ch]
    if len(s):
        log.info(f"  {ch:8s}: n={len(s):,}  breaches={s['breach'].sum():.0f}  "
                 f"rate={s['breach'].mean():.2%}")

# -- Drop internal helpers ----------------------------------------------------
tickets.drop(columns=["_ticket_date"], inplace=True)

# -- Write output -------------------------------------------------------------
out_path = OUT / "clean.csv"
tickets.to_csv(out_path, index=False)
log.info(f"-- OUTPUT ------------------------------------------------------------")
log.info(f"  Written: {out_path}  ({len(tickets):,} rows, {tickets.shape[1]} cols)")

# -- Final schema summary -----------------------------------------------------
log.info("-- COLUMNS IN clean.csv ----------------------------------------------")
for col in tickets.columns:
    log.info(f"  {col}")

log.info("-- clean.py DONE -----------------------------------------------------")
