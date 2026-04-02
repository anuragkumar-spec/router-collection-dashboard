import os, json
from flask import Flask, render_template, request

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'static', 'data.json')

PANEL_META = [
    ('all_calls',      'ALL CALLS',         'Every attempt',                'Connected'),
    ('latest_call',    'LATEST CALL',        'Last attempt per lead',        'Connected'),
    ('first_call',     'FIRST CALL',         '1st attempt per lead',         'Connected'),
    ('first_call_day', '1ST CALL OF DAY',    '1st attempt per lead per day', 'Connected'),
    ('unique_leads',   'UNIQUE LEADS',       '1st attempt · ever connected', 'Ever Connected'),
    ('first_day_conn', '1ST CALL OF DAY',    'Ever connected same day',      'Connected Same Day'),
]


def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def filter_rows(rows, call_date, agent):
    if call_date:
        rows = [r for r in rows if str(r.get('Date', '')).startswith(call_date)]
    if agent:
        rows = [r for r in rows if r.get('Agent') == agent or r.get('User Name') == agent]
    return rows


def summarise(rows, conn_key):
    total = sum(r.get('Total', 0) or 0 for r in rows)
    conn  = sum(r.get(conn_key, 0) or 0 for r in rows)
    rate  = round(conn * 100 / total, 1) if total else 0
    return total, conn, rate


@app.route('/')
def index():
    call_date = request.args.get('date', '')
    agent     = request.args.get('agent', '')

    data = load_data()

    panels = []
    for key, title, subtitle, conn_key in PANEL_META:
        all_rows      = data.get(key, [])
        filtered_rows = filter_rows(all_rows, call_date, '')   # date only; agent handled separately
        # For agent filter on panel cards (Date-grouped rows), filter by agent on the raw agent card
        if call_date:
            rows = filtered_rows
        else:
            rows = all_rows
        total, conn, rate = summarise(rows, conn_key)
        panels.append({
            'key':      key,
            'title':    title,
            'subtitle': subtitle,
            'conn_key': conn_key,
            'total':    total,
            'conn':     conn,
            'rate':     rate,
            'rows':     rows,
        })

    agent_rows = data.get('agent', [])
    if call_date:
        # re-fetch isn't possible without API; show all agents with note
        pass

    refreshed_at = data.get('refreshed_at', '')

    return render_template('dashboard.html',
                           panels=panels,
                           agent_rows=agent_rows,
                           call_date=call_date,
                           agent=agent,
                           refreshed_at=refreshed_at)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
