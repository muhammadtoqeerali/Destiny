#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '=== FrailtyScope Phase 2: reproducible synthetic experiment ==='
if [[ ! -f .venv/bin/activate ]]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m ml.simulate --n 6000 --seed 42
python -m ml.train --seed 42
python -m pytest -q
cd web
if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
npm run lint
npm run build
printf '\nSUCCESS: Synthetic experiment, tests, and Next.js build finished.\n'
printf 'Start separately: cd web && npm run dev -- -p 3001\n'
