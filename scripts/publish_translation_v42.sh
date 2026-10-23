#!/usr/bin/env bash
# Guarded v0.42 public-only promotion protocol publication; NEVER changes clinical approvals.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='990748baa5de15c09a6153de62d7846003d21168'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected exact published v0.41 baseline';exit 1; }
files=(
 .github/workflows/ci.yml
 scripts/run_browser_qa_v34.sh
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
 ml/model_translation_v42.py
 research/TRANSLATION_AND_PROMOTION_V42.md
 scripts/install_translation_v42.sh
 scripts/patch_translation_v42.py
 scripts/publish_translation_v42.sh
 tests/test_translation_v42.py
 tests/browser_translation_v42.py
 web/app/api/inference/translation/route.ts
 web/app/components/model-translation-v42.tsx
 web/app/data/model-translation-v42.json
 web/app/translation-v42.css
)
allowed(){ local x;for x in "${files[@]}"; do [[ "$x" == "$1" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe allowlisted path: $f";exit 1; };done
while IFS= read -r f; do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unexpected tracked change $f"; exit 1; }; done < <(git diff --name-only)
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing staged files detected';exit 1; }
bash -n scripts/install_translation_v42.sh
bash -n scripts/publish_translation_v42.sh
grep -Fq 'tests/test_serving_v40.py tests/test_validation_v41.py' .github/workflows/ci.yml
grep -Fq 'run: python -m pytest -q tests/test_translation_v42.py' .github/workflows/ci.yml
PYTHONPATH=. .venv/bin/python -m ml.model_translation_v42 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/translation-v42.css','utf8'));console.log('PASS: CSS parsed')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected exactly 15 source paths'; exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unexpected staged source $f";exit 1; };done
git diff --cached --check
echo '=== Review exactly 15 source-only paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'NO private NHANES/HUNT data, participant records, model binaries, personal predictions, historical aggregate JSON or unrelated interview briefs staged.'
read -r -p 'Publish v0.42 public candidate source-to-form crosswalk and DENIED clinical promotion gates? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; nothing pushed.';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main advanced; re-review required';exit 1; }
git commit -m 'feat: audit public predictor source-to-form translation and denied clinical promotion gates'
git push origin main
echo 'SUCCESS: v0.42 public crosswalk published; individual clinical inference remains blocked.'
