"""
Run locally to refresh the dashboard:
  python refresh_data.py

Reads METABASE_API_KEY from C:\\credentials\\.env, fetches all panels,
generates docs/index.html — commit + push to publish via GitHub Pages.
"""
import os, json, requests
from datetime import datetime, timezone
from dotenv import load_dotenv

if not os.environ.get('METABASE_API_KEY'):
    load_dotenv('C:\\credentials\\.env')

MB_URL  = 'https://metabase.wiom.in'
HEADERS = {'x-api-key': os.environ['METABASE_API_KEY'], 'Content-Type': 'application/json'}

CARD_IDS = {
    'all_calls':      10829,
    'latest_call':    10830,
    'first_call':     10831,
    'first_call_day': 10832,
    'unique_leads':   10833,
    'first_day_conn': 10834,
    'agent':          10835,
}

PANEL_META = [
    ('all_calls',      'ALL CALLS',         'Every attempt',                'Connected'),
    ('latest_call',    'LATEST CALL',        'Last attempt per lead',        'Connected'),
    ('first_call',     'FIRST CALL',         '1st attempt per lead',         'Connected'),
    ('first_call_day', '1ST CALL OF DAY',    '1st attempt per lead per day', 'Connected'),
    ('unique_leads',   'UNIQUE LEADS',       '1st attempt · ever connected', 'Ever Connected'),
    ('first_day_conn', '1ST CALL OF DAY',    'Ever connected same day',      'Connected Same Day'),
]


DISP_CLASSES = [
    'All',
    'Call Back Requested',
    'Customer Not Connected',
    'Failed Pickup Attempt Calling',
    'Incomplete Call',
    'Router-Collection',
    'campaign.system.disposition',
    'user.forced.logged.off',
]


def run_card(card_id, disposition_class=None, agent_name=None):
    params = []
    if disposition_class:
        params.append({
            'type':   'string/=',
            'target': ['variable', ['template-tag', 'disposition_class']],
            'value':  disposition_class,
        })
    if agent_name:
        params.append({
            'type':   'string/=',
            'target': ['variable', ['template-tag', 'agent_name']],
            'value':  agent_name,
        })
    r = requests.post(f'{MB_URL}/api/card/{card_id}/query',
                      headers=HEADERS, json={'parameters': params}, timeout=30)
    r.raise_for_status()
    d = r.json()['data']
    cols = [c['name'] for c in d['cols']]
    rows = [dict(zip(cols, row)) for row in d['rows']]
    for row in rows:
        for k, v in row.items():
            if v is not None and not isinstance(v, (str, int, float, bool)):
                row[k] = str(v)
    return rows


def rate_class(r):
    if r is None: return ''
    if r >= 40:   return 'rate-high'
    if r >= 25:   return 'rate-mid'
    return 'rate-low'


print('Fetching data from Metabase...')

# Fetch data for All + each disposition class
all_data = {}   # all_data[disp_class][card_key] = rows
for dc in DISP_CLASSES:
    dc_filter = None if dc == 'All' else dc
    print(f'  [{dc}]')
    dc_data = {}
    for key, cid in CARD_IDS.items():
        print(f'    {key}')
        dc_data[key] = run_card(cid, dc_filter)
    all_data[dc] = dc_data

refreshed_at = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')


def build_panels(data):
    panels = []
    for key, title, subtitle, conn_key in PANEL_META:
        rows = data[key]
        total = sum(r.get('Total', 0) or 0 for r in rows)
        conn  = sum(r.get(conn_key, 0) or 0 for r in rows)
        rate  = round(conn * 100 / total, 1) if total else 0
        panels.append({
            'key': key, 'title': title, 'subtitle': subtitle,
            'conn_key': conn_key, 'total': total, 'conn': conn, 'rate': rate,
            'rows': rows,
        })
    return panels


# Build panels and trend data per disposition class for JS
js_datasets = {}
for dc, data in all_data.items():
    panels_dc = build_panels(data)
    for p in panels_dc:
        p['trend_dates']  = [str(r['Date'])[:10] for r in p['rows']]
        p['trend_rates']  = [r.get('Connect Rate %', 0) for r in p['rows']]
        p['trend_totals'] = [r.get('Total', 0) for r in p['rows']]
    js_datasets[dc] = {
        'panels': [
            {k: p[k] for k in ('key','total','conn','rate','conn_key','trend_dates','trend_rates','trend_totals')}
            for p in panels_dc
        ],
        'agent': data['agent'],
    }

# Default (All) for initial render
all_default = all_data['All']
panels    = build_panels(all_default)
for p in panels:
    p['trend_dates']  = [str(r['Date'])[:10] for r in p['rows']]
    p['trend_rates']  = [r.get('Connect Rate %', 0) for r in p['rows']]
    p['trend_totals'] = [r.get('Total', 0) for r in p['rows']]
agent_rows = all_default['agent']

# Fetch per-agent data
agents_list = ['All'] + sorted(set(r['Agent'] for r in agent_rows if r.get('Agent')))
agent_data = {}
for agent in agents_list:
    if agent == 'All':
        continue
    print(f'  [Agent: {agent}]')
    ag_dc = {}
    for key, cid in CARD_IDS.items():
        print(f'    {key}')
        ag_dc[key] = run_card(cid, agent_name=agent)
    agent_data[agent] = ag_dc

# Build agent_datasets for JS
agent_datasets = {}
for agent, ag_dc in agent_data.items():
    panels_ag = build_panels(ag_dc)
    for p in panels_ag:
        p['trend_dates']  = [str(r['Date'])[:10] for r in p['rows']]
        p['trend_rates']  = [r.get('Connect Rate %', 0) for r in p['rows']]
        p['trend_totals'] = [r.get('Total', 0) for r in p['rows']]
    agent_datasets[agent] = {
        'panels': [
            {k: p[k] for k in ('key','total','conn','rate','conn_key','trend_dates','trend_rates','trend_totals')}
            for p in panels_ag
        ],
        'agent': ag_dc['agent'],
    }

# ── Build trend data per panel ───────────────────────────────────────────────
for p in panels:
    rows = p['rows']
    p['trend_dates']  = [str(r['Date'])[:10] for r in rows]
    p['trend_rates']  = [r.get('Connect Rate %', 0) for r in rows]
    p['trend_totals'] = [r.get('Total', 0) for r in rows]
    p['trend_conn']   = [r.get(p['conn_key'], 0) for r in rows]

# ── Generate HTML ─────────────────────────────────────────────────────────────

panel_cards_html = ''
for p in panels:
    rc = rate_class(p['rate'])
    panel_cards_html += f'''
    <div class="panel" id="panel_{p["key"]}">
      <div class="panel-title">{p["title"]}</div>
      <div class="panel-subtitle">{p["subtitle"]}</div>
      <div class="panel-rate {rc}">{p["rate"]}%</div>
      <div class="panel-meta">
        <span><strong class="panel-total">{p["total"]:,}</strong> Total</span>
        <span><strong class="panel-conn">{p["conn"]:,}</strong> {p["conn_key"]}</span>
      </div>
    </div>'''

summary_rows_html = ''
for p in panels:
    rc = rate_class(p['rate'])
    summary_rows_html += f'''
      <tr>
        <td>{p["title"]}<br><span class="sub">{p["subtitle"]}</span></td>
        <td>{p["total"]:,}</td>
        <td>{p["conn"]:,}</td>
        <td class="{rc}">{p["rate"]}%</td>
      </tr>'''

agent_rows_html = ''
for row in agent_rows:
    r = row.get('Connect Rate %', 0) or 0
    rc = rate_class(r)
    agent_rows_html += f'''
      <tr>
        <td>{row["Agent"]}</td>
        <td>{row["Total"]:,}</td>
        <td>{row["Connected"]:,}</td>
        <td class="{rc}">{r}%</td>
      </tr>'''

# Daily breakdown table rows (from all_calls)
daily_rows_html = ''
for row in all_default['all_calls']:
    r = row.get('Connect Rate %', 0) or 0
    rc = rate_class(r)
    daily_rows_html += f'''
      <tr>
        <td>{str(row["Date"])[:10]}</td>
        <td>{row["Total"]:,}</td>
        <td>{row["Connected"]:,}</td>
        <td class="{rc}">{r}%</td>
      </tr>'''

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Connect Rate Dashboard — Router-Collection</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; background: #f0f2f5; color: #222; }}

  .header {{
    background: #1a1a2e; color: #fff;
    padding: 18px 28px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  }}
  .header h1 {{ font-size: 18px; font-weight: 700; flex: 1; }}
  .badge {{ background: #e94560; color: #fff; font-size: 11px; padding: 3px 10px; border-radius: 12px; font-weight: 600; }}
  .filter-wrap {{ display: flex; align-items: center; gap: 8px; }}
  .filter-wrap label {{ font-size: 11px; opacity: .7; white-space: nowrap; }}
  .filter-wrap select {{ background: #2a2a4a; color: #fff; border: 1px solid #444; border-radius: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; }}
  .refreshed {{ font-size: 11px; opacity: .6; margin-left: auto; }}

  .main {{ padding: 20px 28px; max-width: 1600px; margin: 0 auto; }}

  .panels {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px; margin-bottom: 20px;
  }}
  @media(max-width:1100px){{ .panels{{ grid-template-columns: repeat(3,1fr); }} }}
  @media(max-width:650px){{ .panels{{ grid-template-columns: repeat(2,1fr); }} }}

  .panel {{
    background: #fff; border-radius: 10px; padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
  }}
  .panel-title  {{ font-size: 10px; font-weight: 700; letter-spacing: .8px; color: #888; text-transform: uppercase; }}
  .panel-subtitle {{ font-size: 10px; color: #bbb; margin-top: 2px; margin-bottom: 8px; }}
  .panel-rate   {{ font-size: 30px; font-weight: 700; line-height: 1; margin-bottom: 6px; }}
  .panel-meta   {{ display: flex; gap: 14px; font-size: 12px; color: #666; }}
  .panel-meta strong {{ color: #222; }}

  .rate-high {{ color: #1e8a44; }}
  .rate-mid  {{ color: #f57c00; }}
  .rate-low  {{ color: #c62828; }}

  .card {{
    background: #fff; border-radius: 10px; padding: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 20px;
  }}
  .card h2 {{ font-size: 14px; font-weight: 700; margin-bottom: 16px; color: #333; }}
  .chart-sub {{ font-size: 11px; font-weight: 400; color: #aaa; }}
  .chart-wrap {{ position: relative; height: 220px; }}
  .charts-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 16px; margin-bottom: 20px;
  }}
  @media(max-width:900px){{ .charts-grid{{ grid-template-columns: repeat(2,1fr); }} }}
  @media(max-width:600px){{ .charts-grid{{ grid-template-columns: 1fr; }} }}

  .bottom {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
  @media(max-width:900px){{ .bottom{{ grid-template-columns:1fr; }} }}

  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{
    text-align: left; padding: 8px 12px;
    background: #f7f8fa; color: #555; font-weight: 600;
    border-bottom: 2px solid #e8eaed; font-size: 11px; text-transform: uppercase;
  }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #f0f0f0; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #fafbfc; }}
  .sub {{ font-size: 10px; color: #aaa; }}
</style>
</head>
<body>

<div class="header">
  <h1>Connect Rate Dashboard</h1>
  <span class="badge">Router-Collection</span>
  <div class="filter-wrap">
    <label for="dcFilter">Disposition Class</label>
    <select id="dcFilter" onchange="applyFilter()">
      {''.join(f'<option value="{dc}">{dc}</option>' for dc in DISP_CLASSES)}
    </select>
  </div>
  <div class="filter-wrap">
    <label for="agentFilter">Agent</label>
    <select id="agentFilter" onchange="applyFilter()">
      {''.join(f'<option value="{a}">{a}</option>' for a in agents_list)}
    </select>
  </div>
  <div class="filter-wrap">
    <label>Date Range</label>
    <input type="date" id="dateFrom" onchange="applyFilter()" style="background:#2a2a4a;color:#fff;border:1px solid #444;border-radius:6px;padding:5px 8px;font-size:12px;">
    <span style="opacity:.5;font-size:11px;">to</span>
    <input type="date" id="dateTo" onchange="applyFilter()" style="background:#2a2a4a;color:#fff;border:1px solid #444;border-radius:6px;padding:5px 8px;font-size:12px;">
  </div>
  <span class="refreshed">Refreshed: {refreshed_at}</span>
</div>

<div class="main">

  <div class="panels">
    {panel_cards_html}
  </div>

  <div class="charts-grid">
    {''.join(f'''
    <div class="card">
      <h2>{p["title"]} <span class="chart-sub">— {p["subtitle"]}</span></h2>
      <div class="chart-wrap"><canvas id="chart_{p['key']}"></canvas></div>
    </div>''' for p in panels)}
  </div>

  <div class="bottom">

    <div class="card">
      <h2>Summary by View</h2>
      <table>
        <thead><tr><th>Lens</th><th>Total</th><th>Connected</th><th>Rate %</th></tr></thead>
        <tbody>{summary_rows_html}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>Daily Breakdown</h2>
      <table>
        <thead><tr><th>Date</th><th>Total</th><th>Connected</th><th>Rate %</th></tr></thead>
        <tbody>{daily_rows_html}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>Agent Breakdown</h2>
      <table>
        <thead><tr><th>Agent</th><th>Total</th><th>Connected</th><th>Rate %</th></tr></thead>
        <tbody id="agentTbody">{agent_rows_html}</tbody>
      </table>
    </div>

  </div>
</div>

<script>
const charts = {{}};

function makeChart(id, labels, rates, totals) {{
  return new Chart(document.getElementById(id), {{
    type: 'line',
    data: {{
      labels,
      datasets: [
        {{
          label: 'Connect Rate %',
          data: rates,
          borderColor: '#1a73e8',
          backgroundColor: 'rgba(26,115,232,.08)',
          tension: .3, pointRadius: 3, fill: true, yAxisID: 'rate',
        }},
        {{
          label: 'Total',
          data: totals,
          borderColor: '#ccc',
          borderDash: [4,3],
          tension: .3, pointRadius: 2, fill: false, yAxisID: 'vol',
        }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{ legend: {{ position: 'top', labels: {{ boxWidth: 12, font: {{ size: 11 }} }} }} }},
    scales: {{
      rate: {{ type: 'linear', position: 'left',
               title: {{ display: true, text: 'Connect Rate %' }},
               ticks: {{ callback: v => v + '%' }}, suggestedMin: 0 }},
      vol:  {{ type: 'linear', position: 'right',
               title: {{ display: false }},
               grid: {{ drawOnChartArea: false }} }},
    }}
  }}
  }});
}}

CHART_CALLS_PLACEHOLDER

const ALL_DATA = JS_DATASETS_PLACEHOLDER;
const ALL_AGENT_DATA = AGENT_DATASETS_PLACEHOLDER;

function applyFilter() {{
  const dc = document.getElementById('dcFilter').value;
  const agent = document.getElementById('agentFilter').value;
  const dateFrom = document.getElementById('dateFrom').value;
  const dateTo   = document.getElementById('dateTo').value;
  const d = (agent !== 'All') ? ALL_AGENT_DATA[agent] : ALL_DATA[dc];

  d.panels.forEach(p => {{
    // Filter by date range
    let dates = p.trend_dates, rates = p.trend_rates, totals = p.trend_totals;
    if (dateFrom || dateTo) {{
      const idx = dates.map((dt, i) => (!dateFrom || dt >= dateFrom) && (!dateTo || dt <= dateTo) ? i : -1).filter(i => i >= 0);
      dates  = idx.map(i => dates[i]);
      rates  = idx.map(i => rates[i]);
      totals = idx.map(i => totals[i]);
    }}

    // Recalculate aggregate from filtered daily data
    const filtTotal = totals.reduce((a, b) => a + b, 0);
    const filtConn  = totals.reduce((s, t, i) => s + Math.round(rates[i] * t / 100), 0);
    const filtRate  = filtTotal ? Math.round(filtConn * 1000 / filtTotal) / 10 : 0;

    // Update panel
    const el = document.getElementById('panel_' + p.key);
    if (el) {{
      const rc = filtRate >= 40 ? 'rate-high' : filtRate >= 25 ? 'rate-mid' : 'rate-low';
      el.querySelector('.panel-rate').className = 'panel-rate ' + rc;
      el.querySelector('.panel-rate').textContent = filtRate + '%';
      el.querySelector('.panel-total').textContent = filtTotal.toLocaleString();
      el.querySelector('.panel-conn').textContent = filtConn.toLocaleString();
    }}

    // Update chart
    const c = charts[p.key];
    if (c) {{
      c.data.labels = dates;
      c.data.datasets[0].data = rates;
      c.data.datasets[1].data = totals;
      c.update();
    }}
  }});

  // Update agent table
  const tbody = document.getElementById('agentTbody');
  tbody.innerHTML = d.agent.map(row => {{
    const r = row['Connect Rate %'] || 0;
    const rc = r >= 40 ? 'rate-high' : r >= 25 ? 'rate-mid' : 'rate-low';
    return '<tr><td>' + row.Agent + '</td><td>' + (row.Total||0).toLocaleString() +
           '</td><td>' + (row.Connected||0).toLocaleString() +
           '</td><td class="' + rc + '">' + r + '%</td></tr>';
  }}).join('');
}}
</script>
</body>
</html>'''

chart_calls_parts = []
for p in panels:
    chart_calls_parts.append(
        "charts['{}'] = makeChart('chart_{}', {}, {}, {});".format(
            p['key'], p['key'],
            json.dumps(p['trend_dates']),
            json.dumps(p['trend_rates']),
            json.dumps(p['trend_totals'])
        )
    )
chart_calls = '\n'.join(chart_calls_parts)
html = html.replace('CHART_CALLS_PLACEHOLDER', chart_calls)
html = html.replace('JS_DATASETS_PLACEHOLDER', json.dumps(js_datasets))
html = html.replace('AGENT_DATASETS_PLACEHOLDER', json.dumps(agent_datasets))

os.makedirs('docs', exist_ok=True)
with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\nWrote docs/index.html  ({os.path.getsize("docs/index.html"):,} bytes)')
print(f'Refreshed at: {refreshed_at}')
print('\nNext: git add docs/index.html && git commit -m "refresh" && git push')
