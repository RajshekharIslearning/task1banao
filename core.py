"""
core.py -- Pure, importable functions for the Vireo Audio SLA pipeline.

All business logic lives here so it can be unit-tested without touching files.
clean.py calls these functions; tests import them directly.
"""

import numpy as np
import pandas as pd

IST = "Asia/Kolkata"

# SLA first-response targets (minutes)
SLA_TARGETS: dict[str, int] = {
    "chat": 15,
    "voice": 120,
    "social": 240,
    "email": 480,
}

# ── Timestamp helpers ─────────────────────────────────────────────────────────

def parse_utc_timestamps(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Parse string/naive columns as UTC and add corresponding *_ist columns.
    Returns a copy; does not modify the original.
    """
    df = df.copy()
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
        ist_col = col.replace("_at", "_at_ist") if "_at" in col else col + "_ist"
        df[ist_col] = df[col].dt.tz_convert(IST)
    return df


def shift_from_ist_hour(hour: int | float) -> str | float:
    """
    Return the shift name for a given IST hour (0-23).
    Morning 06:00-14:00, Day 14:00-22:00, Night 22:00-06:00.
    Returns NaN for missing/null inputs.
    """
    if pd.isna(hour):
        return np.nan
    h = int(hour)
    if 6 <= h < 14:
        return "Morning"
    if 14 <= h < 22:
        return "Day"
    return "Night"


# ── Cleaning steps ────────────────────────────────────────────────────────────

def dedup_tickets(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Drop duplicate ticket_ids that appear in both source systems.
    Keeps the 'helpdesk' row; removes the 'legacy_fd' row.
    Returns (deduplicated_df, n_rows_removed).
    """
    df = df.copy()
    df["_sys_order"] = df["source_system"].map({"helpdesk": 0, "legacy_fd": 1})
    before = len(df)
    df = (
        df.sort_values(["ticket_id", "_sys_order"])
        .drop_duplicates(subset="ticket_id", keep="first")
        .drop(columns="_sys_order")
        .reset_index(drop=True)
    )
    return df, before - len(df)


def fix_csat(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Convert csat_score == 0 to NaN (legacy sentinel for 'no response').
    Blank (NaN) is left as-is.
    Returns (df_copy, n_rows_changed).
    """
    df = df.copy()
    mask = df["csat_score"] == 0
    n = int(mask.sum())
    df.loc[mask, "csat_score"] = np.nan
    return df, n


def compute_breach(
    df: pd.DataFrame,
    frt_col: str = "frt_minutes",
    target_col: str = "sla_target_min",
) -> pd.Series:
    """
    Return a boolean Series: True if frt > target (strictly greater).
    NaN where frt or target is missing.
    """
    frt    = pd.to_numeric(df[frt_col],    errors="coerce")
    target = pd.to_numeric(df[target_col], errors="coerce")
    return frt > target


def add_sla_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add frt_minutes, sla_target_min, breach, and no_first_response to a tickets DataFrame.
    Requires created_at and first_response_at as UTC-aware datetimes.
    """
    df = df.copy()
    df["sla_target_min"] = df["channel"].str.lower().map(SLA_TARGETS)
    df["frt_minutes"] = (
        (df["first_response_at"] - df["created_at"]).dt.total_seconds() / 60
    )
    df["breach"] = compute_breach(df)
    df["no_first_response"] = df["first_response_at"].isna()
    return df


def roster_join(
    tickets: pd.DataFrame,
    agents: pd.DataFrame,
    ticket_date_col: str = "_ticket_date",
) -> pd.DataFrame:
    """
    Join agent roster attributes to tickets using agent_id AND ticket creation
    date within [from_date, to_date] (null to_date means still active).

    agents must have columns: agent_id, site, team, shift, tier, from_date, to_date
    Dates in agents must already be Python date objects (or NaT for to_date).

    Returns tickets with added columns:
        rostered_site, rostered_team, rostered_shift, rostered_tier
    """
    tickets = tickets.copy()
    agents  = agents.copy()

    # Ensure date types
    agents["from_date"] = pd.to_datetime(agents["from_date"]).dt.date
    agents["to_date"]   = pd.to_datetime(agents["to_date"], errors="coerce").dt.date

    merged = tickets[[ticket_date_col, "ticket_id", "agent_id"]].merge(
        agents[["agent_id", "site", "team", "shift", "tier",
                "from_date", "to_date"]],
        on="agent_id",
        how="left",
    )

    in_window = (merged["_ticket_date"] >= merged["from_date"]) & (
        merged["to_date"].isna() | (merged["_ticket_date"] <= merged["to_date"])
    )
    matched = (
        merged[in_window]
        .sort_values("from_date", ascending=False)
        .drop_duplicates(subset="ticket_id", keep="first")
    )

    tickets = tickets.merge(
        matched[["ticket_id", "site", "team", "shift", "tier"]].rename(
            columns={
                "site": "rostered_site",
                "team": "rostered_team",
                "shift": "rostered_shift",
                "tier": "rostered_tier",
            }
        ),
        on="ticket_id",
        how="left",
    )
    return tickets


def flag_ivr_failures(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add ivr_transcript_failed column. True for voice rows with null, very short
    (<10 chars), or IVR-failure-keyword customer_message.
    """
    df = df.copy()
    voice = df["channel"].str.lower() == "voice"
    msg   = df["customer_message"].fillna("")
    df["ivr_transcript_failed"] = (
        voice & (
            df["customer_message"].isna()
            | (msg.str.strip().str.len() < 10)
            | msg.str.lower().str.contains(
                r"ivr|transcript.*fail|inaudible|\[noise\]",
                na=False, regex=True
            )
        )
    )
    return df
