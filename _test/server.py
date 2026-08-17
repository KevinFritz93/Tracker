"""Static server for the browser tests.

Adds a /slow endpoint that stalls before responding. A page can reference it as
an image so its `load` event fires late, which gives asynchronous work (service
worker registration in particular) time to finish before chromium's --dump-dom
snapshots the DOM.
"""
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = sys.argv[2] if len(sys.argv) > 2 else '.'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/slow':
            ms = int(parse_qs(parsed.query).get('ms', ['3000'])[0])
            time.sleep(ms / 1000)
            self.send_response(200)
            # Served as a script: a pending image is dropped from the load
            # event by Chromium, a pending script is not.
            self.send_header('Content-Type', 'application/javascript')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
