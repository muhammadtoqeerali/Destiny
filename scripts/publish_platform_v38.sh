#!/usr/bin/env bash
# Explicit authorized source-only publication; blocked against remote drift and extra tracked files.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='79698cf9874814a2f8d9154b26bc68d51bf3bae8'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.37 base required.';exit 1; }
files=(
 .github/workflows/ci.yml
 research/CONSOLIDATED_PLATFORM_V38.md
 scripts/build_fictional_models_v38.py
 scripts/install_platform_v38.sh
 scripts/patch_platform_v38.py
 scripts/publish_platform_v38.sh
 scripts/run_browser_qa_v34.sh
 tests/browser_doctor_v35.py
 tests/browser_doctor_v36.py
 tests/browser_inference_v37.py
 tests/browser_platform_v38.py
 tests/test_demo_qa_v34.py
 tests/test_doctor_v35.py
 tests/test_platform_v38.py
 web/app/api/inference/route.ts
 web/app/components/clinical-workspace.tsx
 web/app/components/multioutcome-lab-v38.tsx
 web/app/data/fictional-model-registry-v38.json
 web/app/inference-v38.css
 web/app/layout.tsx
)
allowed(){ local f; for f in "${files[@]}"; do [[ "$1" == "$f" ]] && return 0; done; return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/symlink approved file: $f";exit 1; };done
while IFS= read -r p;do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unapproved tracked change: $p";exit 1; };done < <(git diff --name-only)
while IFS= read -r p;do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unapproved staged path: $p";exit 1; };done < <(git diff --cached --name-only)
.venv/bin/python scripts/build_fictional_models_v38.py --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/inference-v38.css','utf8'));console.log('PASS CSS')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected 20 exact source paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unapproved staged: $f";exit 1; };done
git diff --cached --check
echo '=== Proposed exact source-only changes ==='
git diff --cached --stat
git diff --cached --name-only
echo 'Never stage private NHANES/HUNT, historical aggregate files, clinical model artifacts, or unrelated interview briefs.'
read -r -p 'Publish v0.38 synthetic multi-outcome studio, fail-closed API and CI Chrome fix? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; no push'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Origin/main moved; fresh review required';exit 1; }
git commit -m 'feat: consolidate synthetic multi-outcome inference contracts and CI browser reliability'
git push origin main
echo 'SUCCESS: v0.38 source-only demo published. Patient-level clinical inference remains disabled.'
