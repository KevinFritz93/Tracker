#!/usr/bin/env bash
# Browser tests for the sync layer and the service worker.
#
#   ./_test/run.sh
#
# Serves the repo on 127.0.0.1:8765 and drives the real app in headless
# chromium. Nothing here ships with the app; delete this folder if unwanted.
set -u
cd "$(dirname "$0")/.."

PORT=8765
BROWSER="${CHROME:-chromium}"

if ! command -v "$BROWSER" >/dev/null; then
  echo "no chromium found (set CHROME=/path/to/chrome)"; exit 2
fi

LOG=/tmp/tracker-test-httpd.log
python3 _test/server.py "$PORT" . >"$LOG" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT

for _ in $(seq 1 40); do
  kill -0 $SERVER 2>/dev/null || break
  curl -sf -o /dev/null "http://127.0.0.1:$PORT/index.html" && break
  sleep 0.2
done

# A stale server from an interrupted run would answer requests and then vanish
# mid-suite, which looks like a test failure. Refuse to run in that case.
if ! kill -0 $SERVER 2>/dev/null; then
  echo "test server did not start on port $PORT:"; cat "$LOG"; exit 2
fi
if ! curl -sf -o /dev/null "http://127.0.0.1:$PORT/index.html"; then
  echo "test server not reachable on port $PORT"; exit 2
fi

run_page(){ # <page> <profile>
  rm -rf "/tmp/tracker-$2"
  # No --virtual-time-budget: it never lets service worker promises settle.
  timeout 90 "$BROWSER" --headless=new --disable-gpu --no-sandbox \
    --user-data-dir="/tmp/tracker-$2" --dump-dom \
    "http://127.0.0.1:$PORT/_test/$1" 2>"/tmp/tracker-$2.err" | tee "/tmp/tracker-$2.html"
}

report(){ # reads a DOM dump on stdin
  python3 -c "
import html, re, sys
s = sys.stdin.read()
m = re.search(r'<pre id=\"out\">(.*?)</pre>', s, re.S)
if not m or not m.group(1).strip():
    print('  no results (page did not finish)'); sys.exit(2)
body = html.unescape(m.group(1)).strip()
print(body)
sys.exit(1 if 'FAIL' in body else 0)
"
}

FAILED=0

echo "== static checks =="
python3 _test/static_checks.py || FAILED=1

echo
echo "== sync + storage =="
run_page harness.html sync | report || FAILED=1

echo
echo "== service worker =="
run_page sw.html sw | report || FAILED=1

echo
if [ "$FAILED" -eq 0 ]; then echo "all suites passed"; else echo "FAILURES"; fi
exit $FAILED
