"""
tests/test_core.py
Unit tests for core.py using hand-built DataFrames only.
No real files are read.

Run: pytest tests/test_core.py -v
"""

import math
import numpy as np
import pandas as pd
import pytest

# The module under test
import sys
from core import (
    parse_utc_timestamps,
    shift_from_ist_hour,
    dedup_tickets,
    fix_csat,
    compute_breach,
    add_sla_columns,
    roster_join,
)

IST = "Asia/Kolkata"

# =============================================================================
# 1.  UTC -> IST conversion + shift boundary cases
# =============================================================================

class TestUTCtoIST:
    UTC_CASES = [
        ("2025-03-01 00:29",  "2025-03-01 05:59",   "Night"),
        ("2025-03-01 00:30",  "2025-03-01 06:00",   "Morning"),
        ("2025-03-01 08:30",  "2025-03-01 14:00",   "Day"),
        ("2025-03-01 16:30",  "2025-03-01 22:00",   "Night"),
    ]

    @pytest.mark.parametrize("utc_str,expected_ist,expected_shift", UTC_CASES)
    def test_utc_to_ist_value(self, utc_str, expected_ist, expected_shift):
        df = pd.DataFrame({"created_at": [utc_str], "ticket_id": ["T1"]})
        result = parse_utc_timestamps(df, ["created_at"])
        ist_ts = result["created_at_ist"].iloc[0]
        actual_ist = ist_ts.strftime("%Y-%m-%d %H:%M")
        assert actual_ist == expected_ist

    @pytest.mark.parametrize("utc_str,expected_ist,expected_shift", UTC_CASES)
    def test_shift_from_ist_boundary(self, utc_str, expected_ist, expected_shift):
        df = pd.DataFrame({"created_at": [utc_str], "ticket_id": ["T1"]})
        result = parse_utc_timestamps(df, ["created_at"])
        hour = result["created_at_ist"].iloc[0].hour
        shift = shift_from_ist_hour(hour)
        assert shift == expected_shift

    def test_shift_null_input(self):
        assert math.isnan(shift_from_ist_hour(np.nan))

    def test_original_utc_column_preserved(self):
        df = pd.DataFrame({"created_at": ["2025-03-01 00:30"]})
        result = parse_utc_timestamps(df, ["created_at"])
        assert "created_at" in result.columns
        assert "created_at_ist" in result.columns

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"created_at": ["2025-03-01 00:30"]})
        original_cols = list(df.columns)
        _ = parse_utc_timestamps(df, ["created_at"])
        assert list(df.columns) == original_cols


# =============================================================================
# 2.  Breach flag & no_first_response
# =============================================================================

class TestBreachFlag:
    def _make_ticket(self, frt_min: float, channel: str = "chat") -> pd.DataFrame:
        created = pd.Timestamp("2025-03-01 10:00:00", tz="UTC")
        responded = created + pd.Timedelta(minutes=frt_min)
        return pd.DataFrame({
            "ticket_id":         ["T1"],
            "created_at":        [created],
            "first_response_at": [responded],
            "channel":           [channel],
        })

    def test_exactly_at_target_is_not_breach(self):
        df = add_sla_columns(self._make_ticket(15.0, "chat"))
        assert bool(df["breach"].iloc[0]) is False

    def test_one_minute_over_target_is_breach(self):
        df = add_sla_columns(self._make_ticket(16.0, "chat"))
        assert bool(df["breach"].iloc[0]) is True

    def test_under_target_is_not_breach(self):
        df = add_sla_columns(self._make_ticket(14.0, "chat"))
        assert bool(df["breach"].iloc[0]) is False

    def test_voice_target_120_min(self):
        df_ok   = add_sla_columns(self._make_ticket(120.0, "voice"))
        df_fail = add_sla_columns(self._make_ticket(121.0, "voice"))
        assert bool(df_ok["breach"].iloc[0]) is False
        assert bool(df_fail["breach"].iloc[0]) is True

    def test_social_target_240_min(self):
        df_ok   = add_sla_columns(self._make_ticket(240.0, "social"))
        df_fail = add_sla_columns(self._make_ticket(241.0, "social"))
        assert bool(df_ok["breach"].iloc[0]) is False
        assert bool(df_fail["breach"].iloc[0]) is True

    def test_email_target_480_min(self):
        df_ok   = add_sla_columns(self._make_ticket(480.0, "email"))
        df_fail = add_sla_columns(self._make_ticket(481.0, "email"))
        assert bool(df_ok["breach"].iloc[0]) is False
        assert bool(df_fail["breach"].iloc[0]) is True

    def test_missing_frt_gives_false_breach_and_true_no_response(self):
        df = pd.DataFrame({
            "ticket_id":         ["T1"],
            "created_at":        [pd.Timestamp("2025-03-01 10:00", tz="UTC")],
            "first_response_at": pd.Series([pd.NaT], dtype="datetime64[ns, UTC]"),
            "channel":           ["chat"],
        })
        df = add_sla_columns(df)
        assert bool(df["breach"].iloc[0]) is False
        assert bool(df["no_first_response"].iloc[0]) is True


# =============================================================================
# 3.  Deduplication
# =============================================================================

class TestDedup:
    def _make_pair(self, extra_helpdesk: bool = False) -> pd.DataFrame:
        rows = [
            {"ticket_id": "TK-001", "source_system": "helpdesk",  "agent_id": "A1", "value": "HD"},
            {"ticket_id": "TK-001", "source_system": "legacy_fd", "agent_id": "A1", "value": "LFD"},
        ]
        if extra_helpdesk:
            rows.append({"ticket_id": "TK-002", "source_system": "helpdesk", "agent_id": "A2", "value": "HD2"})
        return pd.DataFrame(rows)

    def test_dedup_removes_legacy_row(self):
        df, n_removed = dedup_tickets(self._make_pair())
        assert n_removed == 1
        assert len(df) == 1

    def test_dedup_keeps_helpdesk_row(self):
        df, _ = dedup_tickets(self._make_pair())
        assert df.iloc[0]["source_system"] == "helpdesk"
        assert df.iloc[0]["value"] == "HD"

    def test_dedup_unique_ids_not_removed(self):
        df, n = dedup_tickets(self._make_pair(extra_helpdesk=True))
        assert n == 1
        assert len(df) == 2

    def test_dedup_does_not_mutate_input(self):
        raw = self._make_pair()
        original_len = len(raw)
        _, _ = dedup_tickets(raw)
        assert len(raw) == original_len

    def test_dedup_returns_correct_count_when_no_dups(self):
        df = pd.DataFrame([
            {"ticket_id": "TK-001", "source_system": "helpdesk",  "value": "a"},
            {"ticket_id": "TK-002", "source_system": "helpdesk",  "value": "b"},
        ])
        _, n = dedup_tickets(df)
        assert n == 0


# =============================================================================
# 4.  Roster join
# =============================================================================

class TestRosterJoin:
    @pytest.fixture()
    def agents(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "agent_id":  "A3002",
                "name":      "Tarun Mishra",
                "site":      "Indore",
                "team":      "Chat Frontline",
                "shift":     "Night",
                "tier":      1,
                "from_date": "2023-02-12",
                "to_date":   "2025-06-29",
            },
            {
                "agent_id":  "A3002",
                "name":      "Tarun Mishra",
                "site":      "Indore",
                "team":      "Chat Frontline",
                "shift":     "Day",
                "tier":      1,
                "from_date": "2025-06-30",
                "to_date":   None,
            },
        ])

    def _make_ticket(self, ticket_id: str, date_str: str) -> pd.DataFrame:
        ts = pd.Timestamp(date_str + " 10:00", tz="UTC")
        ts_ist = ts.tz_convert("Asia/Kolkata")
        return pd.DataFrame({
            "ticket_id":     [ticket_id],
            "agent_id":      ["A3002"],
            "created_at":    [ts],
            "created_at_ist":[ts_ist],
            "_ticket_date":  [ts_ist.date()],
        })

    def test_before_move_gets_night(self, agents):
        tickets = self._make_ticket("T-OLD", "2025-06-28")
        result  = roster_join(tickets, agents)
        assert result["rostered_shift"].iloc[0] == "Night"

    def test_after_move_gets_day(self, agents):
        tickets = self._make_ticket("T-NEW", "2025-07-01")
        result  = roster_join(tickets, agents)
        assert result["rostered_shift"].iloc[0] == "Day"

    def test_on_move_date_gets_day(self, agents):
        tickets = self._make_ticket("T-MOVE", "2025-06-30")
        result  = roster_join(tickets, agents)
        assert result["rostered_shift"].iloc[0] == "Day"

    def test_on_last_night_date_gets_night(self, agents):
        tickets = self._make_ticket("T-LAST", "2025-06-29")
        result  = roster_join(tickets, agents)
        assert result["rostered_shift"].iloc[0] == "Night"

    def test_no_roster_match_gives_nan(self, agents):
        ts = pd.Timestamp("2025-06-28 10:00", tz="UTC")
        ts_ist = ts.tz_convert("Asia/Kolkata")
        tickets = pd.DataFrame({
            "ticket_id":     ["T-UNKNOWN"],
            "agent_id":      ["ZZZZ"],
            "created_at":    [ts],
            "created_at_ist":[ts_ist],
            "_ticket_date":  [ts_ist.date()],
        })
        result = roster_join(tickets, agents)
        assert pd.isna(result["rostered_shift"].iloc[0])

    def test_join_does_not_use_name_column(self, agents):
        agents_bad_name = agents.copy()
        agents_bad_name["name"] = "CORRUPTED"
        tickets = self._make_ticket("T-NAME", "2025-07-01")
        result  = roster_join(tickets, agents_bad_name)
        assert result["rostered_shift"].iloc[0] == "Day"


# =============================================================================
# 5.  CSAT
# =============================================================================

class TestCSAT:
    def _make_csat_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "ticket_id":  ["T1", "T2", "T3", "T4", "T5"],
            "csat_score": [0.0,   3.0,  5.0,  np.nan, 0.0],
        })

    def test_zeros_become_nan(self):
        df, n = fix_csat(self._make_csat_df())
        assert n == 2
        assert pd.isna(df.loc[df["ticket_id"] == "T1", "csat_score"].iloc[0])
        assert pd.isna(df.loc[df["ticket_id"] == "T5", "csat_score"].iloc[0])

    def test_valid_scores_unchanged(self):
        df, _ = fix_csat(self._make_csat_df())
        assert df.loc[df["ticket_id"] == "T2", "csat_score"].iloc[0] == 3.0
        assert df.loc[df["ticket_id"] == "T3", "csat_score"].iloc[0] == 5.0

    def test_blank_stays_nan(self):
        df, _ = fix_csat(self._make_csat_df())
        assert pd.isna(df.loc[df["ticket_id"] == "T4", "csat_score"].iloc[0])

    def test_average_excludes_null(self):
        df, _ = fix_csat(self._make_csat_df())
        mean = df["csat_score"].mean()
        assert mean == pytest.approx(4.0)

    def test_does_not_mutate_input(self):
        raw = self._make_csat_df()
        _ = fix_csat(raw)
        assert raw["csat_score"].iloc[0] == 0.0

    def test_no_zeros_returns_zero_count(self):
        df = pd.DataFrame({"ticket_id": ["T1"], "csat_score": [4.0]})
        _, n = fix_csat(df)
        assert n == 0
