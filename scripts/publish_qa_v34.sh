#!/usr/bin/env bash
# Reviewed 13-path source-only publication. Never stage untracked interview briefs.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='c2bfe9d8e9116ff6441bf304e4574946d3dabf82'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected reviewed v0.33 main baseline'; exit 1; }
files=(
 .github/workflows/ci.yml
 web/app/components/engine-studio-v33.tsx
 web/app/layout.tsx
 web/app/api/status/route.ts
 web/app/components/release-status-v34.tsx
 web/app/engine-studio-v34.css
 scripts/run_browser_qa_v34.sh
 tests/browser_qa_v34.py
 tests/test_demo_qa_v34.py
 scripts/install_qa_v34.sh
 scripts/publish_qa_v34.sh
 scripts/patch_qa_v34.py
 research/DEMO_QA_V34.md
)
allowed(){ local item; for item in "${files[@]}"; do [[ "$1" == "$item" ]] && return 0; done; return 1; }
for p in "${files[@]}"; do [[ -f "$p" && ! -L "$p" ]] || { echo "ERROR: Missing/unsafe source $p"; exit 1; }; done
while IFS= read -r p; do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unexpected tracked edit $p"; exit 1; }; done < <(git diff --name-only)
while IFS= read -r p; do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unexpected staged edit $p"; exit 1; }; done < <(git diff --cached --name-only)
printf '=== Full fixture/privacy/source QA regressions ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Immutable private review: READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== TypeScript and production build ===\n'
(cd web && npm run lint && npm run build)
printf '=== Mandatory real-browser Chromium QA against LOCAL Next.js ===\n'
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected 13 exact reviewed source paths'; exit 1; }
for p in "${staged[@]}"; do allowed "$p" || { echo "ERROR: Unexpected staged path $p"; exit 1; }; done
git diff --cached --check
echo '=== Proposed reviewed source-only changes ==='
git diff --cached --stat
git diff --cached --name-only
echo 'Nothing in data/, artifacts/, web/public/data/ or saved models may be staged.'
read -r -p 'Publish v0.34 browser QA, release identity and engineering hardening? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; nothing pushed'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main changed; fresh review needed'; exit 1; }
git commit -m 'test: add browser QA release provenance and engineering safety checks'
git push origin main
echo 'SUCCESS: reviewed v0.34 source-only release pushed. Private research data untouched.'
