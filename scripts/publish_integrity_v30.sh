#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
files=(
 .github/workflows/ci.yml
 ml/case_integrity_v30.py
 research/WORKFLOW_INTEGRITY_V30.md
 research/cases/WORKFLOW_INTEGRITY_TEMPLATE_V30.json
 research/cases/nhanes_integrity_v30.json
 scripts/install_integrity_v30.sh
 scripts/publish_integrity_v30.sh
 tests/test_case_integrity_v30.py
 web/app/components/decision-quality-v12.tsx
 web/app/components/threshold-sensitivity-chart.tsx
)
allowed_path() { for item in "${files[@]}"; do [[ "$1" == "$item" ]] && return 0; done; return 1; }
while IFS= read -r modified; do
 [[ -z "$modified" ]] && continue
 allowed_path "$modified" || { echo "ERROR: Unapproved modified path: $modified"; exit 1; }
done < <(git diff --name-only)
while IFS= read -r staged; do
 [[ -z "$staged" ]] && continue
 allowed_path "$staged" || { echo "ERROR: Unapproved pre-staged path: $staged"; exit 1; }
done < <(git diff --cached --name-only)
for file in "${files[@]}"; do [[ -f "$file" ]] || { echo "ERROR: Missing source: $file"; exit 1; }; done
bash -n scripts/publish_integrity_v30.sh
bash -n scripts/install_integrity_v30.sh
printf '=== Synthetic/privacy regression tests ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-only plan, internally generated synthetic test, and READ-ONLY private audit verification ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --plan
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --smoke
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== TypeScript and production build ===\n'
[[ -x web/node_modules/.bin/tsc ]] || { echo 'ERROR: npm dependencies missing. Run npm ci in web/ first'; exit 1; }
(cd web && npm run lint && npm run build)
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected exactly ten source paths staged'; exit 1; }
for path in "${staged[@]}"; do allowed_path "$path" || { echo "ERROR: Disallowed staged path $path"; exit 1; }; done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. Historical public aggregate JSON UNCHANGED. No participant data, predictions, models, private audit or research results staged.\n'
read -r -p 'Publish v0.30 synthetic workflow integrity and historical-chart rendering fix? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; no commit or push'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
 echo 'ERROR: Remote main changed. Inspect before pushing'; exit 1; }
git commit -m 'feat: synthetic workflow integrity checks and robust threshold chart'
git push origin main
printf 'SUCCESS: v0.30 source-only integrity and visualization fix published; private research data remain local.\n'
