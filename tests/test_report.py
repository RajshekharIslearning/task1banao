import pandas as pd
from io import StringIO
import pytest
import os

def test_html_totals():
    html_path = "out/report.html"
    assert os.path.exists(html_path)
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    
    tables = pd.read_html(StringIO(html))
    
    # Tables are: 0: Hourly, 1: Monthly, 2: Tier 1, 3: Tier 2, 4: Weekly by Shift, 5..83: Weekly agent tables
    
    tier_1 = tables[2]
    tier_2 = tables[3]
    tier_breaches = tier_1['Breaches'].sum() + tier_2['Breaches'].sum()
    assert tier_breaches == 2440, f"Expected 2440, got {tier_breaches}"
    
    weekly_breaches = 0
    weekly_tables_count = 0
    # Search for all agent tables which start from index 5
    for t in tables:
        if 'Agent' in t.columns and 'Breaches' in t.columns:
            weekly_breaches += pd.to_numeric(t['Breaches'], errors='coerce').sum()
            weekly_tables_count += 1
            
    assert weekly_tables_count == 79, f"Expected 79 weekly tables, got {weekly_tables_count}"
    assert weekly_breaches == 2440, f"Expected 2440, got {weekly_breaches}"

def test_csv_totals():
    for f in ["weekly_by_shift.csv", "weekly_by_channel.csv", "weekly_by_agent.csv", "weekly_by_team.csv"]:
        path = f"out/{f}"
        assert os.path.exists(path), f"Missing output CSV: {f}"
        df = pd.read_csv(path)
        if 'breaches' in df.columns:
            total = df['breaches'].sum()
            assert total == 2440, f"{f} breaches sum to {total}, expected 2440"

def test_pipeline_output_exists():
    assert os.path.exists("out/report.html"), "report.html is missing after a run"
    for f in ["weekly_by_shift.csv", "weekly_by_channel.csv", "weekly_by_agent.csv", "weekly_by_team.csv"]:
        assert os.path.exists(f"out/{f}"), f"{f} is missing after a run"
