#!/usr/bin/env bash
# v0.40 source-only guarded publication; no model binaries, private participant data or unrelated files.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='bbef3c6aac5565a8e31b395238b60ae4be59805a'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact reviewed v0.39 baseline required';exit 1; }
files=(
 .github/workflows/ci.yml
 scripts/run_browser_qa_v34.sh
 tests/browser_inference_v37.py
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
 research/SYNTHETIC_SERVING_V40.md
 scripts/install_serving_v40.sh
 scripts/patch_serving_v40.py
 scripts/publish_serving_v40.sh
 tests/test_serving_v40.py
 tests/browser_serving_v40.py
 web/app/api/inference/synthetic/route.ts
 web/app/lib/synthetic-serving-v40.ts
 web/app/components/synthetic-server-v40.tsx
 web/app/inference-serving-v40.css
)
allowed(){ local target;for target in "${files[@]}";do [[ "$1" == "$target" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe approved file: $f";exit 1; };done
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unexpected tracked change $f";exit 1; };done < <(git diff --name-only)
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unexpected staged path $f";exit 1; };done < <(git diff --cached --name-only)
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/inference-serving-v40.css','utf8'));console.log('PASS: CSS parsed')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected 15 exact source paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unsafe staged source: $f";exit 1; };done
git diff --cached --check
echo '=== Exact 15 reviewed public/source-only paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'NO private research data, real trained model binaries, participant records, public historical aggregates or unrelated interview brief scripts staged.'
read -r -p 'Publish v0.40 fictional GET-only model serving architecture, with clinical inference still blocked? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; nothing pushed.';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote advanced, review required';exit 1; }
git commit -m 'feat: add GET-only synthetic model serving and exact attribution contract'
git push origin main
echo 'SUCCESS: v0.40 source-only synthetic serving architecture published. No clinical patient inference.'
