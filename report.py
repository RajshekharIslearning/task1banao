import pandas as pd
import numpy as np
import pathlib

def make_css():
    return """
    body { font-family: system-ui, -apple-system, sans-serif; line-height: 1.5; color: #333; background: #fafafa; margin: 0; padding: 20px; }
    .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #222; }
    .summary-box { background: #f0f4f8; border-left: 4px solid #6c757d; padding: 15px; margin-bottom: 20px; border-radius: 0 4px 4px 0; }
    .summary-box ul { margin: 0; padding-left: 20px; }
    .table-container { overflow-x: auto; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #eee; }
    th { background: #f8f9fa; font-weight: 600; color: #555; }
    tr:hover { background: #fcfcfc; }
    .note { font-size: 12px; color: #666; font-style: italic; margin-top: 5px; }
    details { margin-bottom: 10px; border: 1px solid #eee; border-radius: 4px; padding: 5px 10px; background: #fff; }
    summary { font-weight: bold; cursor: pointer; color: #444; }
    .week-scroll { max-height: 320px; overflow-y: auto; overflow-x: auto; border: 1px solid #eee; border-radius: 4px; }
    .week-scroll thead th { position: sticky; top: 0; background: #f8f9fa; z-index: 1; }
    details > summary { cursor: pointer; padding: 8px 0; }
    .heat-low { background: #f8f9fa; }
    .heat-med { background: #dee2e6; }
    .heat-high { background: #ced4da; }
    .heat-vhigh { background: #adb5bd; color: white; }
    @media (max-width: 600px) { body { padding: 10px; } .container { padding: 15px; } th, td { padding: 4px 6px; font-size: 12px; } .week-scroll { max-height: 55vh; } }
    """

def get_heat_class(rate):
    if rate < 0.10: return "heat-low"
    if rate < 0.25: return "heat-med"
    if rate < 0.50: return "heat-high"
    return "heat-vhigh"

def main():
    out_dir = pathlib.Path("out")
    out_dir.mkdir(exist_ok=True)
    
    df = pd.read_csv("out/clean.csv")
    df['created_at_ist'] = pd.to_datetime(df['created_at_ist'])
    df['iso_week'] = df['created_at_ist'].dt.strftime('%G-W%V')
    df['month'] = df['created_at_ist'].dt.strftime('%Y-%m')
    df['hour'] = df['created_at_ist'].dt.hour
    cutoff = pd.to_datetime('2025-06-30').date()
    df['period'] = np.where(df['created_at_ist'].dt.date < cutoff, 'Before', 'After')
    df['is_breach'] = df['breach'].fillna(False).astype(bool)
    
    html = [f"<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>"]
    html.append(f"<style>{make_css()}</style></head><body><div class='container'>")
    html.append("<h1>SLA Breach Report</h1>")
    
    html.append("<div class='summary-box'>")
    html.append("<h3>Key Findings & Goals</h3><ul>")
    html.append("<li><strong>Finding:</strong> Overnight coverage ended on 30 June 2025. Consequently, the overnight breach rate jumped from 10.3% to 79.0%.</li>")
    html.append("<li><strong>Goal:</strong> Cut the overnight breach rate from 79% to 15%, worth about Rs 1.12 lakh a quarter (range Rs 0.94-1.22 lakh at 25%-9%).</li>")
    html.append("<li><strong>CSAT Impact:</strong> Overnight CSAT fell from 3.42 to 2.94, while Day/Morning remained steady at about 3.47.</li>")
    html.append("<li><strong>What the team can control:</strong> In-shift breach rates for Tier 1 agents (tickets created and resolved in their own shift) are at or under 10.8%.</li>")
    html.append("</ul></div>")
    
    html.append("<h2>Hourly Breach Heatmap (IST)</h2>")
    html.append("<div class='table-container'><table><tr><th>Hour</th><th>Before (Tickets)</th><th>Before (Rate)</th><th>After (Tickets)</th><th>After (Rate)</th></tr>")
    hourly = df.groupby(['hour', 'period']).agg(tickets=('ticket_id', 'count'), breaches=('is_breach', 'sum')).reset_index()
    for h in range(24):
        b_data = hourly[(hourly['hour'] == h) & (hourly['period'] == 'Before')]
        a_data = hourly[(hourly['hour'] == h) & (hourly['period'] == 'After')]
        
        b_t = b_data['tickets'].values[0] if not b_data.empty else 0
        a_t = a_data['tickets'].values[0] if not a_data.empty else 0
        b_b = b_data['breaches'].values[0] if not b_data.empty else 0
        a_b = a_data['breaches'].values[0] if not a_data.empty else 0
        
        b_str = f"{b_b/b_t:.1%}" if b_t >= 20 else "n<20"
        a_str = f"{a_b/a_t:.1%}" if a_t >= 20 else "n<20"
        b_class = get_heat_class(b_b/b_t) if b_t >= 20 else ""
        a_class = get_heat_class(a_b/a_t) if a_t >= 20 else ""
        
        html.append(f"<tr><td>{h:02d}:00</td><td>{b_t}</td><td class='{b_class}'>{b_str}</td><td>{a_t}</td><td class='{a_class}'>{a_str}</td></tr>")
    html.append("</table></div>")
    
    html.append("<h2>Monthly SLA Credits Issued</h2>")
    html.append("<div class='table-container'><table><tr><th>Month</th><th>Credits (Rs)</th><th>Trend</th></tr>")
    monthly = df.groupby('month')['is_breach'].sum().reset_index()
    monthly['credits'] = monthly['is_breach'] * 350
    monthly['prev_credits'] = monthly['credits'].shift(1)
    for _, r in monthly.iterrows():
        trend = "N/A"
        if pd.notna(r['prev_credits']):
            diff = r['credits'] - r['prev_credits']
            trend = f"+ Rs {diff:,.0f}" if diff > 0 else f"- Rs {abs(diff):,.0f}" if diff < 0 else "Flat"
        html.append(f"<tr><td>{r['month']}</td><td>Rs {r['credits']:,.0f}</td><td>{trend}</td></tr>")
    html.append("</table></div>")
    
    agent_df = df.groupby(['agent_id', 'rostered_tier', 'created_shift', 'rostered_shift']).agg(
        tickets=('ticket_id', 'count'), breaches=('is_breach', 'sum')
    ).reset_index()
    
    html.append("<h2>Agent Performance (Overall)</h2>")
    html.append("<p>Shows performance based on ticket creation shift vs agent roster shift. Rows with &lt; 20 tickets show n&lt;20 for rate.</p>")
    for tier in [1, 2]:
        html.append(f"<h3>Tier {tier} Agents</h3>")
        html.append("<div class='table-container'><table><tr><th>Agent ID</th><th>Created Shift</th><th>Resolver Shift</th><th>Tickets</th><th>Breaches</th><th>Rate</th></tr>")
        t_data = agent_df[agent_df['rostered_tier'] == tier].sort_values(['agent_id', 'created_shift'])
        for _, r in t_data.iterrows():
            rate_str = f"{r['breaches']/r['tickets']:.1%}" if r['tickets'] >= 20 else "n<20"
            html.append(f"<tr><td>{r['agent_id']}</td><td>{r['created_shift']}</td><td>{r['rostered_shift']}</td><td>{r['tickets']}</td><td>{r['breaches']}</td><td>{rate_str}</td></tr>")
        html.append("</table></div>")
        html.append("<div class='note'>Limitation: agent_id is the resolving agent, not necessarily the first responder.</div>")

    # Weekly Trends (All Weeks) by Shift
    html.append("<h2>Weekly Trends by Shift</h2>")
    html.append("<div class='note'>Week 1 of 2025 and week 27 of 2026 are partial weeks.</div>")
    html.append("<div class='table-container'><table><tr><th>Week</th><th>Shift</th><th>Tickets</th><th>Rate</th></tr>")
    w_shift = df.groupby(['iso_week', 'created_shift']).agg(tickets=('ticket_id', 'count'), breaches=('is_breach', 'sum')).reset_index()
    w_shift = w_shift.sort_values(['iso_week', 'created_shift'])
    for _, r in w_shift.iterrows():
        rate_str = f"{r['breaches']/r['tickets']:.1%}" if r['tickets'] >= 20 else "n<20"
        html.append(f"<tr><td>{r['iso_week']}</td><td>{r['created_shift']}</td><td>{r['tickets']}</td><td>{rate_str}</td></tr>")
    html.append("</table></div>")

    # Weekly breach report (collapsible list per week with agent rows)
    html.append("<h2>Weekly Breach Report (By Agent)</h2>")
    html.append("<div class='note'>Limitation: agent_id is the resolving agent, not necessarily the first responder. Week 1 of 2025 and week 27 of 2026 are partial weeks.</div>")
    
    df['own_shift_breach'] = ((df['created_shift'] == df['rostered_shift']) & df['is_breach']).astype(int)
    df['overnight_breach'] = ((df['created_shift'] == 'Night') & df['is_breach']).astype(int)
    
    w_agent = df.groupby(['iso_week', 'agent_id']).agg(
        tickets=('ticket_id', 'count'),
        breaches=('is_breach', 'sum'),
        own_shift_breaches=('own_shift_breach', 'sum'),
        overnight_breaches=('overnight_breach', 'sum')
    ).reset_index()
    
    weeks = sorted(df['iso_week'].unique())
    for w in weeks:
        html.append(f"<details><summary>{w}</summary><div class='week-scroll'><table>")
        html.append("<thead><tr><th>Agent</th><th>Tickets</th><th>Breaches</th><th>Rate</th><th>Own Shift Breaches</th><th>Overnight Breaches</th></tr></thead><tbody>")
        wa_data = w_agent[w_agent['iso_week'] == w].sort_values('agent_id')
        for _, r in wa_data.iterrows():
            if r['tickets'] > 0:
                rate_str = f"{r['breaches']/r['tickets']:.1%}" if r['tickets'] >= 20 else "n<20"
                html.append(f"<tr><td>{r['agent_id']}</td><td>{r['tickets']}</td><td>{r['breaches']}</td><td>{rate_str}</td><td>{r['own_shift_breaches']}</td><td>{r['overnight_breaches']}</td></tr>")
        html.append("</tbody></table></div></details>")
        
    html.append("</div></body></html>")
    
    with open("out/report.html", "w", encoding='utf-8') as f:
        f.write("".join(html))

    # Write the 4 required CSVs
    def write_weekly_csv(groupby_col, filename):
        g = df.groupby(['iso_week', groupby_col]).agg(
            tickets=('ticket_id', 'count'),
            breaches=('is_breach', 'sum')
        ).reset_index()
        g.to_csv(out_dir / filename, index=False)

    write_weekly_csv('created_shift', 'weekly_by_shift.csv')
    write_weekly_csv('channel', 'weekly_by_channel.csv')
    write_weekly_csv('agent_id', 'weekly_by_agent.csv')
    write_weekly_csv('assigned_team', 'weekly_by_team.csv')

if __name__ == "__main__":
    main()
