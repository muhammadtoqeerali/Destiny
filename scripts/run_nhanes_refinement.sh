#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT"
[[ "$(git branch --show-current)" == 'main' ]] || { echo 'ERROR: switch to Git main'; exit 1; }
[[ -x .venv/bin/python ]] || { echo 'ERROR: virtual environment missing'; exit 1; }
[[ -f data/processed/nhanes_5yr_local.csv ]] || { echo 'ERROR: REAL NHANES processed data missing. Run scripts/run_real_nhanes.sh'; exit 1; }
[[ -f artifacts/realdata_nhanes/report.json ]] || { echo 'ERROR: baseline REAL NHANES report missing'; exit 1; }
[[ -f web/public/data/nhanes-aggregate.json ]] || { echo 'ERROR: v0.6 real NHANES dashboard missing'; exit 1; }

# Refuse overwriting uncommitted versions of source files.
FILES=(ml/nhanes_refinement.py scripts/export_nhanes_refinement.py scripts/run_nhanes_refinement.sh scripts/publish_refinement_v07.sh tests/test_nhanes_refinement.py web/app/components/clinical-workspace.tsx web/app/components/multi-outcome-admin.tsx web/app/admin/page.tsx web/app/admin/login/page.tsx web/app/layout.tsx web/app/nhanes.css .github/workflows/ci.yml)
for f in "${FILES[@]}"; do
 if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
  if ! git diff --quiet -- "$f" || ! git diff --cached --quiet -- "$f";then
   echo "ERROR: source has uncommitted edits: $f";exit 1
  fi
 fi
done
# Install backend/tests first. Keep currently deployed frontend intact if training fails.
for f in "${FILES[@]}";do
 if [[ "$f" != web/* && "$f" != .github/* ]];then
   mkdir -p "$(dirname "$f")";cp "$RELEASE/$f" "$f"
 fi
done
printf '\n=== Verify exact NHANES data origin ===\n'
.venv/bin/python - <<'PY'
import pandas as pd
from pathlib import Path
p=Path('data/processed/nhanes_5yr_local.csv')
df=pd.read_csv(p,usecols=['SEQN','cycle','data_origin','outcome_5yr'])
assert len(df)>=2000
assert set(df.data_origin)=={'NHANES_PUBLIC_2019_LMF'}
assert set(df.cycle)=={'2011-2012','2013-2014'}
assert df.SEQN.nunique()==len(df)
print(f'PASS: {len(df):,} actual CDC NHANES observations')
PY
printf '\n=== Ensure required analysis packages ===\n'
.venv/bin/python -m pip install -r requirements-advanced.txt
printf '\n=== Run real-data pipeline tests ===\n'
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py
printf '\n=== Optuna 3-fold CV: four model families, training partition only ===\n'
.venv/bin/python -m ml.nhanes_refinement --input data/processed/nhanes_5yr_local.csv \
 --out artifacts/realdata_nhanes/refinement.json --trials "${TRIALS:-10}"
printf '\n=== Export allowlisted, aggregate NHANES diagnostics ===\n'
.venv/bin/python scripts/export_nhanes_refinement.py \
 --report artifacts/realdata_nhanes/refinement.json \
 --output web/public/data/nhanes-refinement.json
printf '\n=== Show key training metrics ===\n'
.venv/bin/python - <<'PY'
import json
r=json.load(open('artifacts/realdata_nhanes/refinement.json'))
print('Data source:',r['data_origin'])
print('Selected model:',r['selected_model'])
print('Threshold:',r['selected_threshold'])
for m in r['model_search']:
 print(m['model'],'CV Brier',m['cv_brier'],'Validation AUC',m['validation']['roc_auc'],'Validation Brier',m['validation']['brier'])
print('Later-cycle metrics:',{k:v for k,v in r['test_metrics'].items() if k!='confusion'})
print('Confusion matrix:',r['test_metrics']['confusion'])
print('SHAP:',r['shap_status'])
PY
# Only replace the local frontend after real-data training and allowlisted export succeed.
for f in "${FILES[@]}";do
 if [[ "$f" == web/* || "$f" == .github/* ]];then
   mkdir -p "$(dirname "$f")";cp "$RELEASE/$f" "$f"
 fi
done
printf '\n=== Validate Next.js build and dependency audit in isolated directory ===\n'
BUILD="$(mktemp -d /tmp/frailtyscope-refinement-build-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data"
cp web/public/data/nhanes-aggregate.json web/public/data/nhanes-refinement.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-audit --no-fund && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)
printf '\nREADY FOR REVIEW. NO GIT PUSH PERFORMED.\n'
printf 'Report: %s/artifacts/realdata_nhanes/refinement.json\n' "$PROJECT"
printf 'Public aggregate: %s/web/public/data/nhanes-refinement.json\n' "$PROJECT"
printf 'After reviewing metrics, use: bash scripts/publish_refinement_v07.sh\n'
