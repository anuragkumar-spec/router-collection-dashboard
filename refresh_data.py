"""
Run this locally whenever you want to refresh the dashboard data.
  python refresh_data.py
Reads METABASE_API_KEY from C:\\credentials\\.env, fetches all panels,
writes static/data.json — no credentials leave your machine.
"""
import os, json, requests
from datetime import datetime, timezone
from dotenv import load_dotenv

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


def run_card(card_id):
    r = requests.post(f'{MB_URL}/api/card/{card_id}/query',
                      headers=HEADERS, json={}, timeout=30)
    r.raise_for_status()
    d = r.json()['data']
    cols = [c['name'] for c in d['cols']]
    return [dict(zip(cols, row)) for row in d['rows']]


print('Fetching data from Metabase...')
data = {}
for key, cid in CARD_IDS.items():
    print(f'  {key} (card {cid})')
    rows = run_card(cid)
    # convert any non-serialisable types (dates) to strings
    for row in rows:
        for k, v in row.items():
            if v is not None and not isinstance(v, (str, int, float, bool)):
                row[k] = str(v)
    data[key] = rows

data['refreshed_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

os.makedirs('static', exist_ok=True)
out = 'static/data.json'
with open(out, 'w') as f:
    json.dump(data, f)

print(f'\nWrote {out}  ({os.path.getsize(out):,} bytes)')
print(f"Refreshed at: {data['refreshed_at']}")
print('\nNext steps:')
print('  git add static/data.json && git commit -m "refresh data" && railway up')
