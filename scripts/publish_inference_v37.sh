#!/usr/bin/env bash
# Strict reviewed source-only publication; never stage private data or unrelated files.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='55b1d48e0a2496144722d7e704310da579e21eaf'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected v0.36 main'; exit 1; }
files=(
 .github/workflows/ci.yml
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
 scripts/run_browser_qa_v34.sh
 research/INFERENCE_READINESS_V37.md
 scripts/patch_inference_v37.py
 scripts/install_inference_v37.sh
 scripts/publish_inference_v37.sh
 tests/test_runtime_gate_v37.py
 tests/browser_inference_v37.py
 web/app/components/inference-readiness-v37.tsx
 web/app/inference-v37.css
)
allowed(){ local item;for item in "${files[@]}";do [[ "$item" == "$1" ]] && return 0;done;return 1; }
for p in "${files[@]}";do [[ -f "$p" && ! -L "$p" ]] || { echo "ERROR: Missing approved source: $p"; exit 1; };done
while IFS= read -r p;do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unexpected tracked change: $p"; exit 1; };done < <(git diff --name-only)
while IFS= read -r p;do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unexpected staged change: $p"; exit 1; };done < <(git diff --cached --name-only)
(cd web && node -e "const fs=require('fs'),pc=require('postcss');pc.parse(fs.readFileSync('app/inference-v37.css','utf8'));console.log('PASS: CSS parses')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected exactly 12 new/modified paths'; exit 1; }
for p in "${staged[@]}";do allowed "$p" || { echo "ERROR: Unexpected staged path $p"; exit 1; };done
git diff --cached --check
printf '=== Exact 12 reviewed source paths ===\n'
git diff --cached --stat
git diff --cached --name-only
printf 'NO models, patient data, real NHANES private data, public aggregate JSON or unrelated interview brief files staged.\n'
printf 'WARNING: Previous hosted GitHub Chromium installation failed. This release does not claim to fix it.\n'
read -r -p 'Publish v0.37 synthetic-only illustrative scoring + explicit blocked clinical inference? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined. Nothing pushed.'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote changed. Fresh review required.'; exit 1; }
git commit -m 'feat: add fail-closed clinical inference gate and synthetic explainability lab'
git push origin main
printf 'SUCCESS: v0.37 source-only research demo published; no clinical prediction and no patient data uploaded.\n'
