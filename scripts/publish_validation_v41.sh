#!/usr/bin/env bash
# Exact reviewed source-only v0.41 publishing gate. No private data or model binaries.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BASE='90a426b131a408cc438c931e03aa43322d81a7e0'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact v0.40 publication baseline required';exit 1; }
files=(
 .github/workflows/ci.yml
 scripts/run_browser_qa_v34.sh
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
 ml/research_validation_v41.py
 research/VALIDATION_AND_PROMOTION_V41.md
 scripts/install_validation_v41.sh
 scripts/patch_validation_v41.py
 scripts/publish_validation_v41.sh
 tests/test_validation_v41.py
 tests/browser_validation_v41.py
 web/app/api/inference/validation/route.ts
 web/app/components/validation-gate-v41.tsx
 web/app/data/validation-readiness-v41.json
 web/app/validation-v41.css
)
allowed(){ local x;for x in "${files[@]}";do [[ "$x" == "$1" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe approved source $f";exit 1; };done
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unexpected tracked edit: $f";exit 1; };done < <(git diff --name-only)
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing staged files are not approved';exit 1; }
bash -n scripts/install_validation_v41.sh
bash -n scripts/publish_validation_v41.sh
PYTHONPATH=. .venv/bin/python -m ml.research_validation_v41 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/validation-v41.css','utf8'));console.log('PASS CSS')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected 15 exact changed paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unexpected staged path $f";exit 1; };done
git diff --cached --check
echo '=== Exact 15 reviewed source-only publication paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'NO private NHANES/HUNT, real model binaries, patient predictions, historical aggregate JSON or unrelated interview briefs staged.'
read -r -p 'Publish v0.41 public clinical promotion gates and invented-only validation metrics? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; no push';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote moved; review again';exit 1; }
git commit -m 'feat: add reproducible fictional holdback validation and clinical model promotion dossier'
git push origin main
echo 'SUCCESS: v0.41 public-only scientific validation dossier published; no patient-level inference.'
