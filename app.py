import os
from flask import Flask, send_from_directory

app = Flask(__name__)

DOCS_DIR = os.path.join(os.path.dirname(__file__), 'docs')


@app.route('/')
def index():
    return send_from_directory(DOCS_DIR, 'index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
