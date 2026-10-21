#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ -x .venv/bin/python ]] || { echo 'ERROR: Existing project virtualenv required';exit 1; }
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Require project main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected remote origin';exit 1; }
[[ -f data/processed/nhanes_5yr_local.csv && -f artifacts/realdata_nhanes/quality_v08.json ]] || { echo 'ERROR: Corrected NHANES reference data is required';exit 1; }
[[ -f artifacts/realdata_nhanes/cox_v09_local.json ]] || { echo 'ERROR: Expected v0.9 local survival benchmark';exit 1; }
[[ -f web/app/components/multi-outcome-admin.tsx ]] || { echo 'ERROR: Admin Portal source is missing';exit 1; }
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing staged changes must be reviewed first';exit 1; }

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
)
for file in "${FILES[@]}";do
  [[ -f "$SOURCE/$file" ]] || { echo "ERROR: Release missing: $file";exit 1; }
  if git ls-files --error-unmatch "$file" >/dev/null 2>&1;then
    git diff --quiet -- "$file" || { echo "ERROR: Modified tracked file: $file";exit 1; }
  elif [[ -e "$file" ]];then
    echo "ERROR: Untracked existing file: $file";exit 1
  fi
done

git diff --quiet -- web/app/components/multi-outcome-admin.tsx || { echo 'ERROR: Save pending Admin edits first';exit 1; }
git diff --quiet -- web/public/data || { echo 'ERROR: Uncommitted public aggregate edits; review before installing';exit 1; }

echo '=== Verify corrected NHANES provenance and fixed local follow-up ==='
.venv/bin/python - <<'PY'
import json,pandas as pd
from pathlib import Path
q=json.loads(Path('artifacts/realdata_nhanes/quality_v08.json').read_text())
assert q['phq9_flag']=='COVERAGE_OK' and q['phq9_complete_percent']>85
x=pd.read_csv('data/processed/nhanes_5yr_local.csv',usecols=['SEQN','cycle','data_origin','phq9_score','outcome_5yr'])
assert len(x)==2422 and x.SEQN.is_unique and set(x.data_origin)=={'NHANES_PUBLIC_2019_LMF'}
assert int(x.outcome_5yr.sum())==484 and round(100*x.phq9_score.notna().mean(),2)==q['phq9_complete_percent']
print('PASS:',len(x),'real participants;',q['phq9_complete_percent'],'percent valid PHQ-9;',int(x.outcome_5yr.sum()),'events')
PY

echo '=== Verify tracked version before installing release ==='
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Local branch differs from GitHub main; nothing installed';exit 1; }

BACKUP="$(mktemp -d /tmp/frailtyscope-v10-source-backup-XXXXXX)"
mkdir -p "$BACKUP/web/app/components"
cat web/app/components/multi-outcome-admin.tsx > "$BACKUP/web/app/components/multi-outcome-admin.tsx"
for file in "${FILES[@]}";do
  mkdir -p "$(dirname "$file")" "$BACKUP/$(dirname "$file")"
  if [[ -f "$file" ]];then cat "$file" > "$BACKUP/$file";fi
  cat "$SOURCE/$file" > "$file"
done
printf 'Code backup under /tmp: %s\n' "$BACKUP"

.venv/bin/python scripts/patch_admin_benchmark_v10.py web/app/components/multi-outcome-admin.tsx

PYTHONPATH=. .venv/bin/python scripts/environment_check_v10.py

echo '=== Full regression and research safety suite ==='
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py \
  tests/test_v08.py tests/test_phq_xport_zero.py tests/test_survival_v09.py tests/test_nhats_v09.py \
  tests/test_case_engine_v10.py

echo '=== Verify case manifest and partitions before training ==='
PYTHONPATH=. .venv/bin/python -m ml.case_engine_v10 \
  --config research/cases/nhanes_mortality_v10.json --dry-run

echo '=== Train general-purpose case engine on existing corrected REAL NHANES ==='
PYTHONPATH=. .venv/bin/python -m ml.case_engine_v10 \
  --config research/cases/nhanes_mortality_v10.json

echo '=== Validate experiment metadata and public-release boundary ==='
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
r=json.loads(Path('artifacts/cases/nhanes_mortality_v10/metrics.json').read_text())
assert r['report_type']=='LOCAL_AGGREGATE_RESEARCH_ONLY'
assert r['schema']=='FRAILTYSCOPE_CASE_V10'
assert r['split']['counts']['evaluation']==1257
assert r['split']['counts']['train']+r['split']['counts']['validation']==1165
assert 0<=r['evaluation']['roc_auc']<=1 and 0<=r['evaluation']['brier']<=1
assert r['selected_model'] != 'dummy'
assert r['cv_objective']=='minimize brier'
assert len(r['candidate_models'])>=3
assert not (set(r)&{'patients','SEQN','participant_rows','individual_predictions','individual_scores'})
assert Path('artifacts/cases/nhanes_mortality_v10/best_model.joblib').is_file()
public=Path('web/public/data')
assert {x.name for x in public.iterdir() if x.is_file()}=={
 'nhanes-aggregate.json','nhanes-cohort-profile.json','nhanes-refinement.json'}
print('VALIDATED local case experiment:',r['selected_model'],r['evaluation'])
print('PASS: Public assets limited to three reviewed aggregates; no new rows published')
PY

echo '=== Isolated frontend lint, build and dependency security audit ==='
BUILD="$(mktemp -d /tmp/frailtyscope-v10-next-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data"
cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-audit --no-fund && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)

echo '=== Final source and privacy review ==='
git diff --check -- .github/workflows/ci.yml web/app/components/multi-outcome-admin.tsx
printf '\nREADY FOR REVIEW. General-purpose case pipeline trained on real NHANES.\n'
printf 'Local run: artifacts/cases/nhanes_mortality_v10/metrics.json\n'
printf 'No GitHub push, no individual data export.\n'
printf 'If satisfactory: bash scripts/publish_case_ready_v10.sh\n'
