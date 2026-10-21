#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected origin';exit 1; }

FILES=(
  ml/case_engine_v10.py
  tests/test_case_engine_v10.py
  research/cases/nhanes_mortality_v10.json
  research/cases/CASE_ASSIGNMENT_TEMPLATE.json
  research/CASE_READY_ARCHITECTURE.md
  scripts/patch_admin_benchmark_v10.py
  scripts/environment_check_v10.py
  scripts/install_case_ready_v10.sh
  scripts/publish_case_ready_v10.sh
  .github/workflows/ci.yml
  web/app/components/multi-outcome-admin.tsx
)

mapfile -d '' -t PRESTAGED < <(git diff --cached --name-only -z)
for file in "${PRESTAGED[@]}"; do
  allowed=0
  for item in "${FILES[@]}"; do
    if [[ "$file" == "$item" ]]; then allowed=1;break;fi
  done
  (( allowed )) || { echo "ERROR: Unexpected staged file: $file";exit 1; }
done

.venv/bin/python - <<'PY'
import json
from pathlib import Path
r=json.loads(Path('artifacts/cases/nhanes_mortality_v10/metrics.json').read_text())
assert r['schema']=='FRAILTYSCOPE_CASE_V10' and r['report_type']=='LOCAL_AGGREGATE_RESEARCH_ONLY'
assert r['selected_model']!='dummy' and r['split']['counts']['evaluation']==1257
assert len(r['candidate_models'])>=3
assert Path('artifacts/cases/nhanes_mortality_v10/best_model.joblib').is_file()
assert {x.name for x in Path('web/public/data').iterdir() if x.is_file()}=={
  'nhanes-aggregate.json','nhanes-cohort-profile.json','nhanes-refinement.json'}
print('PASS: Local case benchmark and aggregate-only boundary')
PY

git diff --quiet -- web/public/data || { echo 'ERROR: Modified public data files are outside this release';exit 1; }

echo '=== Regression tests before publication ==='
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py \
  tests/test_v08.py tests/test_phq_xport_zero.py tests/test_survival_v09.py tests/test_nhats_v09.py \
  tests/test_case_engine_v10.py

echo '=== Exact proposed Next.js build and dependency security audit ==='
BUILD="$(mktemp -d /tmp/frailtyscope-v10-release-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data";cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-audit --no-fund && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)

echo '=== Stage exact source-only allowlist ==='
git add -- "${FILES[@]}"
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for file in "${STAGED[@]}";do
  allowed=0
  for item in "${FILES[@]}";do
    if [[ "$file" == "$item" ]];then allowed=1;break;fi
  done
  (( allowed )) || { echo "ERROR: Unapproved staged file: $file";exit 1; }
done
[[ ${#STAGED[@]} -gt 0 ]] || { echo 'No source changes to publish';exit 0; }
git diff --cached --check
git diff --cached --stat
printf '\nSOURCE-ONLY RELEASE. No data/, artifacts/, patient data or model binaries staged.\n'
read -r -p 'Push source and Admin Benchmark tab to GitHub main? Type YES: ' CONFIRM
[[ "$CONFIRM" == YES ]] || { echo 'No push performed';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main moved; no push';exit 1; }
git commit -m 'feat: add case-ready experiment architecture and real benchmark review'
git push origin main
printf 'SUCCESS: Case-ready architecture and current real-data benchmark portal published.\n'
