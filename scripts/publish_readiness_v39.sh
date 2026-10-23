#!/usr/bin/env bash
# Source-only guarded publication. No private cohort, model binaries, or interview-brief files staged.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='5b77d2ebab4f742926981a55ca2473f422f1fbc9'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact v0.38 baseline required';exit 1; }
files=(
 .github/workflows/ci.yml
 ml/inference_readiness_v39.py
 research/MODEL_READINESS_V39.md
 scripts/install_readiness_v39.sh
 scripts/patch_readiness_v39.py
 scripts/publish_readiness_v39.sh
 scripts/run_browser_qa_v34.sh
 tests/browser_readiness_v39.py
 tests/test_inference_readiness_v39.py
 web/app/api/inference/readiness/route.ts
 web/app/components/clinical-workspace.tsx
 web/app/components/inference-evidence-v39.tsx
 web/app/data/inference-readiness-v39.json
 web/app/inference-v39.css
 web/app/layout.tsx
)
allowed(){ local path;for path in "${files[@]}";do [[ "$1" == "$path" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/symlink approved file: $f";exit 1; };done
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unexpected tracked change: $f";exit 1; };done < <(git diff --name-only)
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unexpected staged change: $f";exit 1; };done < <(git diff --cached --name-only)
PYTHONPATH=. .venv/bin/python -m ml.inference_readiness_v39 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/inference-v39.css','utf8'));console.log('PASS: CSS parsed')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected exactly 15 approved source paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unsafe staged path: $f";exit 1; };done
git diff --cached --check
echo '=== Review 15 exact source paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'No NHANES/HUNT participant rows, model binaries, private reviews, previous public aggregate JSON or unrelated interview-brief files staged.'
read -r -p 'Publish v0.39 documentary readiness and portable browser CI fix? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined. Nothing pushed.';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: origin/main changed; fresh review required';exit 1; }
git commit -m 'feat: add documentary model readiness evidence and portable browser QA'
git push origin main
echo 'SUCCESS: v0.39 source-only readiness published; patient inference still disabled.'
