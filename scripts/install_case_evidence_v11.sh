#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ -x .venv/bin/python ]] || { echo 'ERROR: Project .venv required';exit 1; }
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected repository';exit 1; }
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Review previously staged files first';exit 1; }
[[ -f data/processed/nhanes_5yr_local.csv && -f artifacts/cases/nhanes_mortality_v10/metrics.json && -f artifacts/cases/nhanes_mortality_v10/best_model.joblib ]] || { echo 'ERROR: Existing corrected data and v0.10 trained model required';exit 1; }
[[ -f web/app/components/multi-outcome-admin.tsx && -f web/app/layout.tsx ]] || { echo 'ERROR: Existing frontend missing';exit 1; }
FILES_NEW=(
 ml/case_forensics_v11.py ml/case_enhancement_v11.py ml/case_model_io_v11.py
 scripts/export_case_audit_v11.py scripts/local_transformation_inspector_v11.py scripts/patch_admin_v11.py scripts/patch_layout_v11.py scripts/patch_ci_v11.py
 scripts/install_case_evidence_v11.sh scripts/publish_case_evidence_v11.sh
 tests/test_case_forensics_v11.py tests/test_case_model_io_v11.py research/CASE_EVIDENCE_V11.md
 web/app/components/evidence-workbench-v11.tsx web/app/nhanes-v11.css
)
FILES_EDIT=( web/app/components/multi-outcome-admin.tsx web/app/layout.tsx .github/workflows/ci.yml ml/case_engine_v10.py )
for file in "${FILES_NEW[@]}";do
  [[ -f "$SOURCE/$file" ]] || { echo "ERROR: Package missing: $file";exit 1; }
  if [[ -e "$file" ]] || git ls-files --error-unmatch "$file" >/dev/null 2>&1;then
    echo "ERROR: v0.11 already installed or unexpected existing file: $file";exit 1
  fi
done
for file in "${FILES_EDIT[@]}";do
  git diff --quiet -- "$file" || { echo "ERROR: Existing local edits require review: $file";exit 1; }
done

echo '=== Verify branch and prepare protected source backup ==='
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Local branch is not current; no files changed';exit 1; }
BACKUP="$(mktemp -d /tmp/frailtyscope-v11-backup-XXXXXX)"
for file in "${FILES_EDIT[@]}";do
 mkdir -p "$BACKUP/$(dirname "$file")";cat "$file" > "$BACKUP/$file"
done
printf 'Current tracked code backed up: %s\n' "$BACKUP"

echo '=== Install dedicated research and frontend source ==='
for file in "${FILES_NEW[@]}";do
 mkdir -p "$(dirname "$file")";cat "$SOURCE/$file" > "$file"
done
.venv/bin/python scripts/patch_admin_v11.py web/app/components/multi-outcome-admin.tsx
.venv/bin/python scripts/patch_layout_v11.py web/app/layout.tsx
.venv/bin/python scripts/patch_ci_v11.py .github/workflows/ci.yml
.venv/bin/python - <<'PY_COMPAT'
from pathlib import Path
p=Path('ml/case_engine_v10.py')
s=p.read_text()
old="if __name__=='__main__':main()"
new="""if __name__=='__main__':
    from ml.case_engine_v10 import main as canonical_main
    canonical_main()"""
if s.count(old)!=1:raise ValueError('Unexpected v0.10 entry point; review before continuing')
p.write_text(s.replace(old,new))
PY_COMPAT

echo '=== Run full local safety / forensic regression suite ==='
PYTHONPATH=. .venv/bin/python -m pytest -q tests

echo '=== Canonicalize and verify the legacy local model (no retraining) ==='
PYTHONPATH=. .venv/bin/python -m ml.case_model_io_v11

echo '=== Inspect actual fitted preprocessing, data shift and model behavior ==='
PYTHONPATH=. .venv/bin/python -m ml.case_forensics_v11

echo '=== Assess a predeclared calibration enhancement without test-set tuning ==='
PYTHONPATH=. .venv/bin/python -m ml.case_enhancement_v11

echo '=== Export strictly selected, disclosure-screened aggregate findings ==='
PYTHONPATH=. .venv/bin/python scripts/export_case_audit_v11.py

PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('web/public/data')
expected={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json','nhanes-case-audit-v11.json'}
actual={x.name for x in p.iterdir() if x.is_file()}
assert actual==expected,(actual,expected)
d=json.loads((p/'nhanes-case-audit-v11.json').read_text())
assert d['schema']=='FRAILTYSCOPE_PUBLIC_CASE_AUDIT_V11'
assert d['counts']['all']==2422 and d['counts']['evaluation']==1257
assert d['provenance']=='REAL_NHANES_AGGREGATE_ONLY'
assert len(d['features'])==14 and len(d['selection']['candidates'])>=6
assert not ({'local_examples','patient_ids','individual_predictions','raw_predictions','dataset_sha256'}&set(d))
assert all(x['n']>=50 for x in d['evaluation']['calibration'])
assert all(x['n']>=100 for x in d['evaluation']['subgroups'])
print('PASS: 14 real data features, fitted transformations, six candidate models, and protected public aggregate')
print('Selected model:',d['selection']['model'])
print('Enhancement accepted (development-only):',d['enhancement']['rule']['accepted'])
print('Evaluation:',d['evaluation']['metrics'])
PY

echo '=== Validate exact proposed production frontend in isolated /tmp ==='
BUILD="$(mktemp -d /tmp/frailtyscope-v11-build-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data";cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-fund --no-audit && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)

git diff --check -- "${FILES_EDIT[@]}"
echo ''
echo 'READY FOR REVIEW. v0.11 source and real-data deep analyses prepared.'
echo 'The model weights, respondent examples, and local audits remain in ignored artifacts/.'
echo 'No GitHub push performed. After reviewing, run: bash scripts/publish_case_evidence_v11.sh'
