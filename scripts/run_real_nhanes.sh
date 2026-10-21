#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
if [[ ! -x .venv/bin/python ]]; then echo "Missing Python .venv. Run Phase 1 bootstrap first." >&2; exit 1; fi
mkdir -p artifacts/realdata_nhanes data/raw/nhanes data/processed
printf '\n=== VERIFIED REAL-DATA WORKSTATION EXPERIMENT ===\n'
printf 'Working directory: %s\n' "$PWD"
.venv/bin/python --version
printf '\n1. Install experiment packages (no GitHub push)\n'
.venv/bin/python -m pip install -r requirements-advanced.txt
printf '\n2. Run real-data ingestion and method tests\n'
.venv/bin/python -m pytest -q tests/test_real_nhanes.py
printf '\n3. Download REAL CDC NHANES public-use components / linked mortality (2011–2014)\n'
.venv/bin/python -m ml.realdata_nhanes \
    --cache data/raw/nhanes \
    --output data/processed/nhanes_5yr_local.csv
printf '\n4. Benchmark models on REAL baseline health + linked mortality\n'
.venv/bin/python -m ml.realdata_train \
    --input data/processed/nhanes_5yr_local.csv \
    --report artifacts/realdata_nhanes/report.json
printf '\n5. Confirm tracked files unchanged and data remain local\n'
git status --short
printf '\nDONE: aggregate report is artifacts/realdata_nhanes/report.json\n'
printf 'DO NOT git-add data, artifacts, individual predictions or model binaries.\n'
