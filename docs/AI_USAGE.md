# AI_USAGE.md — Vireo Audio SLA Tool

## Step 1 — Orientation (2026-10-02)

### What was AI-generated
- `profile_data.py` — full data profiling script (generated, iteratively fixed for UTF-8 encoding and tz-naive comparison errors)
- `check_h567.py` — targeted script for H5/H6/H7 with tz-aware roster join (generated after main script error)
- `docs/FINDINGS_0.md` — orientation findings document (AI-drafted from verified Python output)
- `docs/DECISIONS.md` — decisions log (AI-drafted, decisions grounded in policy + SRS text)
- `docs/AI_USAGE.md` — this file

### What was attempted and failed
- Browser-based PDF reading (blocked by browser tool restrictions; abandoned immediately)
- Inline Python one-liner for H5/H6/H7 (quoting/syntax failure in PowerShell; switched to script file)
- Arrow character (`→`) in print string caused `UnicodeEncodeError` on Windows cp1252 terminal; fixed with `sys.stdout.reconfigure(encoding='utf-8')`
- PowerShell `>` redirect produced UTF-16LE file unreadable by view_file tool; switched to log-file approach

### What was discarded
- Paise-detection logic (H6): coded and ran, returned zero rows with ratio > 5x — hypothesis REJECTED by data. Logic kept in script for auditability but not needed in Step 2.

### What was verified against raw data (not assumed)
- All H1–H7 verdicts derived from Python output, not from reading hypothesis text.
- Cross-dup count (616): confirmed by `groupby("ticket_id")["source_system"].nunique()`.
- Breach rate step-change: read directly from weekly table, not inferred.
- Resolver-shift breakdown: computed via date-aware roster join on 1 686 overnight breaches.
