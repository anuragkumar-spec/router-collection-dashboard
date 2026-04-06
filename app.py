import os
import time
import requests
from flask import Flask, Response

app = Flask(__name__)

GITHUB_RAW = (
    "https://raw.githubusercontent.com/"
    "anuragkumar-spec/router-collection-dashboard/master/docs/index.html"
)

_cache = {"html": None, "ts": 0}
CACHE_TTL = 3600  # 1 hour


@app.route('/')
def index():
    now = time.time()
    if _cache["html"] is None or (now - _cache["ts"]) > CACHE_TTL:
        r = requests.get(GITHUB_RAW, timeout=15)
        r.raise_for_status()
        _cache["html"] = r.content
        _cache["ts"] = now
    return Response(_cache["html"], content_type="text/html; charset=utf-8")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
