#!/usr/bin/env bash
# Isolated local-production-server browser QA. Never targets real private data.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
PY="${FRAILTYSCOPE_QA_PYTHON:-.venv/bin/python}"
"$PY" -c 'import playwright.sync_api' || { echo 'ERROR: Install Playwright in the QA Python environment: python -m pip install playwright==1.56.0'; exit 1; }
[[ -f web/.next/BUILD_ID ]] || { echo 'ERROR: Run (cd web && npm run build) before browser QA'; exit 1; }
PORT="$("$PY" - <<'PY'
import socket
s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1]); s.close()
PY
)"
LOG="$(mktemp /tmp/frailtyscope-v34-next-XXXXXXXX.log)"
(cd web && exec ./node_modules/.bin/next start -p "$PORT" -H 127.0.0.1) >"$LOG" 2>&1 &
SERVER_PID=$!
cleanup(){ kill "$SERVER_PID" 2>/dev/null || :; wait "$SERVER_PID" 2>/dev/null || :; }
trap cleanup EXIT INT TERM
READY=0
for i in $(seq 1 70); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then echo 'ERROR: Next.js exited unexpectedly'; tail -n 25 "$LOG"; exit 1; fi
  if curl -fsS --connect-timeout 2 --max-time 3 "http://127.0.0.1:$PORT/api/status" >/dev/null 2>&1; then READY=1; break; fi
  sleep 1
done
[[ "$READY" -eq 1 ]] || { echo 'ERROR: Next.js server did not start'; tail -n 25 "$LOG"; exit 1; }
printf '=== Browser QA against isolated production build on loopback ===\n'
FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_qa_v34.py
FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_doctor_v35.py
