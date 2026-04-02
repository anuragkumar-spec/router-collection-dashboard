import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

MB_URL = os.environ.get('METABASE_URL', 'https://metabase.wiom.in')
MB_KEY  = os.environ['METABASE_API_KEY']
HEADERS = {'x-api-key': MB_KEY, 'Content-Type': 'application/json'}

CARD_IDS = {
    'all_calls':      10829,
    'latest_call':    10830,
    'first_call':     10831,
    'first_call_day': 10832,
    'unique_leads':   10833,
    'first_day_conn': 10834,
    'agent':          10835,
}

PANEL_LABELS = [
    ('all_calls',      'ALL CALLS',              'Every attempt'),
    ('latest_call',    'LATEST CALL',             'Last attempt per lead'),
    ('first_call',     'FIRST CALL',              '1st attempt per lead'),
    ('first_call_day', '1ST CALL OF DAY',         '1st attempt per lead per day'),
    ('unique_leads',   'UNIQUE LEADS',            '1st attempt · ever connected'),
    ('first_day_conn', '1ST CALL OF DAY',         'Ever connected same day'),
]


def run_card(card_id, params=None):
    body = {}
    if params:
        body['parameters'] = params
    r = requests.post(f'{MB_URL}/api/card/{card_id}/query',
                      headers=HEADERS, json=body, timeout=30)
    r.raise_for_status()
    data = r.json().get('data', {})
    cols = [c['name'] for c in data.get('cols', [])]
    rows = data.get('rows', [])
    return [dict(zip(cols, row)) for row in rows]


def build_params(call_date=None, agent=None):
    params = []
    if call_date:
        params.append({
            'type':   'date/single',
            'target': ['variable', ['template-tag', 'call_date']],
            'value':  call_date,
        })
    if agent:
        params.append({
            'type':   'string/=',
            'target': ['variable', ['template-tag', 'agent_name']],
            'value':  agent,
        })
    return params or None


@app.route('/')
def index():
    call_date = request.args.get('date', '')
    agent     = request.args.get('agent', '')
    params    = build_params(call_date or None, agent or None)

    panels = []
    for key, title, subtitle in PANEL_LABELS:
        rows = run_card(CARD_IDS[key], params)
        total = sum(r['Total'] for r in rows)
        conn_key = next((k for k in (rows[0].keys() if rows else [])
                         if k not in ('Date', 'Total', 'Connect Rate %')), 'Connected')
        conn  = sum(r.get(conn_key, 0) or 0 for r in rows)
        rate  = round(conn * 100 / total, 1) if total else 0
        panels.append({
            'key':      key,
            'title':    title,
            'subtitle': subtitle,
            'total':    total,
            'conn':     conn,
            'conn_key': conn_key,
            'rate':     rate,
            'rows':     rows,
        })

    agent_rows = run_card(CARD_IDS['agent'], params)

    return render_template('dashboard.html',
                           panels=panels,
                           agent_rows=agent_rows,
                           call_date=call_date,
                           agent=agent)


@app.route('/api/panel/<key>')
def api_panel(key):
    call_date = request.args.get('date', '')
    agent     = request.args.get('agent', '')
    params    = build_params(call_date or None, agent or None)
    if key not in CARD_IDS:
        return jsonify({'error': 'unknown panel'}), 404
    rows = run_card(CARD_IDS[key], params)
    return jsonify(rows)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
