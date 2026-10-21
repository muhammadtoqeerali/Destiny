#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ -x .venv/bin/python ]] || { echo 'ERROR: Existing project virtual environment required';exit 1; }
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch';exit 1; }
ORIGIN="$(git remote get-url origin)"
[[ "$ORIGIN" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$ORIGIN" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected Git remote';exit 1; }
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Previously staged changes; review before installing';exit 1; }
[[ -f artifacts/cases/nhanes_mortality_v10/metrics.json && -f artifacts/cases/nhanes_mortality_v10/best_model.joblib ]] || { echo 'ERROR: Existing model and report required, no retraining is performed';exit 1; }
[[ -f web/public/data/nhanes-case-audit-v11.json ]] || { echo 'ERROR: Completed v0.11 aggregate audit required';exit 1; }
[[ -f ml/case_model_io_v11.py && -f ml/case_engine_v10.py ]] || { echo 'ERROR: Current fitted-model infrastructure missing';exit 1; }
NEW=( ml/case_decision_quality_v12.py scripts/export_decision_quality_v12.py scripts/patch_ui_ci_v12.py scripts/install_decision_quality_v12.sh scripts/publish_decision_quality_v12.sh tests/test_decision_quality_v12.py research/DECISION_EVALUATION_V12.md web/app/components/decision-quality-v12.tsx web/app/nhanes-v12.css )
EDIT=( web/app/components/multi-outcome-admin.tsx web/app/layout.tsx .github/workflows/ci.yml )
for f in "${NEW[@]}";do
 [[ -f "$SRC/$f" ]] || { echo "ERROR: Missing bundled source $f";exit 1; }
 [[ ! -e "$f" ]] || { echo "ERROR: Source already exists: $f. Do not overwrite; inspect prior installation.";exit 1; }
done
for f in "${EDIT[@]}";do
 git diff --quiet -- "$f" || { echo "ERROR: Unreviewed local edits to $f";exit 1; }
done
echo '=== Confirm latest reviewed GitHub branch ==='
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Local branch differs from origin/main. No changes made';exit 1; }
BACKUP="$(mktemp -d /tmp/frailtyscope-v12-source-XXXXXX)"
for f in "${EDIT[@]}";do
 mkdir -p "$BACKUP/$(dirname "$f")"
 cat "$f" > "$BACKUP/$f"
done
echo "Tracked source backup: $BACKUP"
for f in "${NEW[@]}";do mkdir -p "$(dirname "$f")";cat "$SRC/$f" > "$f";done
PYTHONPATH=. .venv/bin/python scripts/patch_ui_ci_v12.py

echo '=== Unit tests, research and privacy regression checks ==='
PYTHONPATH=. .venv/bin/python -m pytest -q tests

echo '=== Evaluate the existing saved model on the WORKSTATION; no training ==='
PYTHONPATH=. .venv/bin/python -m ml.case_decision_quality_v12 --bootstrap 500

echo '=== Disclosure-screen only reviewed aggregates ==='
PYTHONPATH=. .venv/bin/python scripts/export_decision_quality_v12.py
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('web/public/data')
expected={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json','nhanes-case-audit-v11.json','nhanes-decision-quality-v12.json'}
assert {x.name for x in p.iterdir() if x.is_file()}==expected,'Unexpected public payload files'
d=json.loads((p/'nhanes-decision-quality-v12.json').read_text())
assert d['schema']=='FRAILTYSCOPE_PUBLIC_DECISION_QUALITY_V12'
assert d['counts']=={'validation':292,'evaluation':1257,'events':246}
assert len(d['thresholds'])==14
assert all(x['n']>=100 and min(x['events'],x['n']-x['events'])>=20 for x in d['subgroups'])
assert all(x['n']>=50 and min(x['events'],x['n']-x['events'])>=10 for x in d['calibration_bands'])
print('PASS: Only reproducible screened NHANES aggregates; no individual predictions')
print('Evaluation ROC-AUC',d['evaluation']['roc_auc'],'Brier',d['evaluation']['brier'])
print('Subgroup reliability:',len(d['subgroups']),'risk bands:',len(d['calibration_bands']))
PY

echo '=== Isolated production TypeScript and Next.js build ==='
BUILD="$(mktemp -d /tmp/frailtyscope-v12-build-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data"; cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-fund --no-audit && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)
git diff --check -- "${EDIT[@]}"
printf '\nREADY FOR REVIEW: actual saved-model evaluation and dashboard completed on workstation.\n'
printf 'No model training or fitting; no GitHub push; no individual-level outputs.\n'
printf 'Local report: artifacts/cases/nhanes_mortality_v10/decision_quality_v12_local.json\n'
printf 'After review only: bash scripts/publish_decision_quality_v12.sh\n'
