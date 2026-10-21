#!/usr/bin/env bash
# Set up and evaluate the public SYNTHETIC demo. Never place HUNT data here.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '=== FRAILTYSCOPE PHASE 2: Synthetic-only bootstrap ==='
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m ml.simulate --n 6000 --seed 42
python -m ml.train
python -m pytest -q
cd web
if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
npm run build
printf '\nDONE: Demo generated and production web build passed.\n'
printf 'To run: cd web && npm run dev (then visit http://localhost:3000)\n'
