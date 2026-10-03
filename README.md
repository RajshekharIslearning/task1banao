# Vireo Audio SLA Tool

## Setup Instructions

1. Ensure you have Python 3.9+ installed.
2. Create and activate a fresh virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Data Requirements

The five input CSVs (`tickets.csv`, `agents.csv`, `orders.csv`, `customers.csv`, `products.csv`) are supplied privately and are NOT included in this repository. Place them in the `data/` directory with those exact names before running the application.

## Running the Application

To run the entire pipeline (clean data and generate reports), use this single command:
```bash
python run.py
```

### Outputs Generated

All output files are placed in the `out/` directory:

- **clean.csv**: The cleaned, transformed, and joined dataset with UTC/IST timestamps, computed SLA targets, breach flags, and roster information.
- **report.html**: The final HTML report, designed to be fully self-contained and mobile-friendly (< 300 KB). Includes the heatmap, agent performance tables, and weekly breakdown with scrolling enabled.
- **weekly_by_shift.csv**: Summary of tickets and breaches aggregated by ISO week and shift.
- **weekly_by_channel.csv**: Summary of tickets and breaches aggregated by ISO week and channel.
- **weekly_by_agent.csv**: Summary of tickets and breaches aggregated by ISO week and agent.
- **weekly_by_team.csv**: Summary of tickets and breaches aggregated by ISO week and team.
- **clean.log**: Processing log detailing every row removal and data transformation.

*(Note: `sample_output/report.html` and `sample_output/rootcause.md` are provided as static copies of the generated reports so reviewers can view them without running anything.)*

### Helper Scripts
- **`scripts/`**: Holds the analysis scripts behind the business-goal figure (e.g., `eval_alternatives.py`) and various helper checks (`check_report.py`, etc.).

## Running Tests

Tests are written in `pytest`. To run them:
```bash
python -m pytest
```
*Troubleshooting:* Any previous `PermissionError` encountered under `pytest` did not reproduce in a separate folder.

## Decisions and Limits

*Extracted from DECISIONS.md*

| # | Decision | Why |
|---|---|---|
| D1 | On duplicate tickets, keep the `helpdesk` row and drop the `legacy_fd` row. | `helpdesk` is the current system of record per SRS FR-2.2 and policy §9. |
| D2 | For shift attribution, use **ticket creation time in IST** (not resolution time). | Policy §7: SLA clock starts at creation. SRS FR-3.2 is explicit. |
| D3 | `csat_score = 0` in `legacy_fd` rows → set to NaN. | DATA_README and policy §8 both say blank (no response) was stored as 0 in legacy. |
| D4 | **No refund normalisation applied.** | Refund/order-value ratio ≤ 1.0 for all rows in both systems; no paise blowup detected. No normalisation applied. |
| D5 | Failed IVR transcripts flagged but kept in SLA counts. | SRS FR-2.5 explicitly says "exclude from text analysis only, not from SLA counts." |
| D6 | Minimum volume threshold for per-agent ranking: tickets >= 20. | Prevents noisy one-ticket weeks. |
| D7 | Tier 2 agents reported in a separate section, not ranked against Tier 1. | Policy §6 and SRS FR-3.3. |
| D8 | Strict boolean logic for FRT Breach. Tickets with a null `first_response_at` receive `breach = False` but are flagged in `no_first_response = True`. | Satisfies the requirement that a breach is strictly when response time exceeds the target. Matches requirement to report open/pending tickets separately. |
