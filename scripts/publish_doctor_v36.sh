#!/usr/bin/env bash
# Strong reviewed source-only publication gate, no private data staging.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='332cbf33d3102420e3ee1e1e414884fb8ae99323'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: v0.35 main baseline required'; exit 1; }
files=(
 .github/workflows/ci.yml
 research/DOCTOR_JOURNEY_V36.md
 scripts/install_doctor_v36.sh
 scripts/patch_doctor_v36.py
 scripts/publish_doctor_v36.sh
 scripts/run_browser_qa_v34.sh
 tests/browser_doctor_v35.py
 tests/browser_doctor_v36.py
 tests/browser_qa_v34.py
 tests/test_doctor_journey_v36.py
 web/app/components/clinical-workspace.tsx
 web/app/components/doctor-journey-v36.tsx
 web/app/doctor-journey-v36.css
 web/app/layout.tsx
)
allowed(){ local p;for p in "${files[@]}"; do [[ "$p" == "$1" ]] && return 0; done; return 1; }
for p in "${files[@]}";do [[ -f "$p" && ! -L "$p" ]] || { echo "ERROR: Missing/symlink $p"; exit 1; };done
while IFS= read -r p;do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unreviewed tracked change $p"; exit 1; };done < <(git diff --name-only)
while IFS= read -r p;do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unreviewed staged file $p"; exit 1; };done < <(git diff --cached --name-only)
(cd web && node -e "const fs=require('fs');require('postcss').parse(fs.readFileSync('app/doctor-journey-v36.css','utf8'));console.log('PASS: CSS parsed')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected 14 exact source paths'; exit 1; }
for p in "${staged[@]}";do allowed "$p" || { echo "ERROR: Unsafe path $p"; exit 1; };done
git diff --cached --check
echo '=== Proposed source-only publication ==='
git diff --cached --stat
git diff --cached --name-only
echo 'NO research data, private integrity artifacts, public aggregates, trained models, or unrelated interview-brief files staged.'
read -r -p 'Publish v0.36 descriptive Doctor journey and educational explainability animation? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined. No push.'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main moved. Review again.'; exit 1; }
git commit -m 'feat: connect descriptive assessment and visits with animated modeling explanation'
git push origin main
echo 'SUCCESS: v0.36 reviewed Doctor journey source pushed. No patient-level inference.'
