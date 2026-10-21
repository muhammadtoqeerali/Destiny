#!/usr/bin/env bash
# Correct v0.11's false-canonical model check and finish evidence generation.
# No repeat of six-family tuning or selected-model retraining. Learning-curve
# refits and calibration (if needed) happen ONLY on the workstation.
set -euo pipefail
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"

[[ -x .venv/bin/python ]] || { echo 'ERROR: Local .venv is missing'; exit 1; }
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected git origin'; exit 1; }
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Review staged changes before repair'; exit 1; }
[[ -f data/processed/nhanes_5yr_local.csv && -f artifacts/cases/nhanes_mortality_v10/metrics.json && -f artifacts/cases/nhanes_mortality_v10/best_model.joblib ]] || { echo 'ERROR: Trusted local case data/model/metrics required'; exit 1; }
[[ -f ml/case_model_io_v11.py && -f ml/case_forensics_v11.py && -f ml/case_enhancement_v11.py ]] || { echo 'ERROR: v0.11 and previous serialization hotfix must already be installed'; exit 1; }
[[ -f scripts/publish_case_evidence_v11.sh && -f .github/workflows/ci.yml ]] || { echo 'ERROR: v0.11 publication files missing'; exit 1; }

# Check package against recorded source hashes; never replace unrelated changes.
.venv/bin/python - "$SOURCE" <<'PY'
from pathlib import Path
import hashlib,sys
source=Path(sys.argv[1]);root=Path('.')
originals={
 'ml/case_model_io_v11.py': '848772ece1f730fc25bb084b7e9697f14146086663106901253e7c90a79674a5',
 'ml/case_forensics_v11.py': '7b21dd488699fd26cb8c141453d0f3d8bf85fd2eb358d8f6f43d02542615a092',
 'ml/case_enhancement_v11.py': '483960880e5fa05939597ddcdc075c3d4e0751e95b25a386268b8cdca44390a2',
}
new_files=['tests/test_clean_model_reload_v112.py','research/MODEL_ARTIFACT_PROTOCOL_V112.md','scripts/repair_model_reload_v112.sh']
if not all((source/x).is_file() for x in [*originals,*new_files]):
    raise SystemExit('ERROR: Incomplete patch archive')
existing=[x for x in new_files if (root/x).exists()]
# Allow a resumed run only when ALL patched source files and new assets match exactly.
if existing:
    if len(existing)!=len(new_files):raise SystemExit('ERROR: Partial patch state; please inspect files, no changes made')
    if any((root/x).read_bytes()!=(source/x).read_bytes() for x in [*originals,*new_files]):
        raise SystemExit('ERROR: Existing patch differs; review changes before rerun')
    print('PASS: Previously installed source matches v0.11.2; resuming')
else:
    for x,sha in originals.items():
        actual=hashlib.sha256((root/x).read_bytes()).hexdigest()
        if actual!=sha:
            raise SystemExit('ERROR: Unexpected local changes to '+x+'; no changes made')
    print('PASS: Exact earlier v0.11 sources identified; patch is safe to apply')
ci=(root/'.github/workflows/ci.yml').read_text()
publish=(root/'scripts/publish_case_evidence_v11.sh').read_text()
for p in [ci,publish]:
    if p.count('tests/test_case_model_io_v11.py')!=1:
        raise SystemExit('ERROR: Release test anchor missing or ambiguous')
if existing and (ci.count('tests/test_clean_model_reload_v112.py')!=1 or
                 publish.count('tests/test_clean_model_reload_v112.py')!=1):
    raise SystemExit('ERROR: Resumed release wiring is inconsistent')
if not existing and ('tests/test_clean_model_reload_v112.py' in ci or
                     'tests/test_clean_model_reload_v112.py' in publish):
    raise SystemExit('ERROR: Unexpected existing CI/publish patch; review manually')
PY

if [[ ! -f tests/test_clean_model_reload_v112.py ]]; then
  BACKUP="$(mktemp -d /tmp/frailtyscope-v112-source-backup-XXXXXX)"
  for file in ml/case_model_io_v11.py ml/case_forensics_v11.py ml/case_enhancement_v11.py .github/workflows/ci.yml scripts/publish_case_evidence_v11.sh; do
    mkdir -p "$BACKUP/$(dirname "$file")"
    cat "$file" > "$BACKUP/$file"
  done
  echo "SOURCE BACKUP: $BACKUP"
  for file in ml/case_model_io_v11.py ml/case_forensics_v11.py ml/case_enhancement_v11.py tests/test_clean_model_reload_v112.py research/MODEL_ARTIFACT_PROTOCOL_V112.md scripts/repair_model_reload_v112.sh; do
    mkdir -p "$(dirname "$file")"
    cat "$SOURCE/$file" > "$file"
  done
  .venv/bin/python - <<'PY'
from pathlib import Path
ci=Path('.github/workflows/ci.yml')
s=ci.read_text()
anchor='tests/test_case_model_io_v11.py'
assert s.count(anchor)==1
ci.write_text(s.replace(anchor,anchor+' tests/test_clean_model_reload_v112.py'))
p=Path('scripts/publish_case_evidence_v11.sh')
s=p.read_text()
assert s.count(anchor)==1
s=s.replace(anchor, anchor+' tests/test_clean_model_reload_v112.py research/MODEL_ARTIFACT_PROTOCOL_V112.md scripts/repair_model_reload_v112.sh')
p.write_text(s)
print('PASS: Shared loader, CI and publishing allowlist updated')
PY
fi

bash -n scripts/repair_model_reload_v112.sh scripts/publish_case_evidence_v11.sh
.venv/bin/python -m py_compile ml/case_model_io_v11.py ml/case_forensics_v11.py ml/case_enhancement_v11.py

echo '=== Prove legacy detection with UNFITTED serialization-only fixtures ==='
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_clean_model_reload_v112.py

echo '=== Independently reload and verify workstation model; NO retraining ==='
PYTHONPATH=. .venv/bin/python -m ml.case_model_io_v11

echo '=== Run previously installed research and model compatibility tests ==='
PYTHONPATH=. .venv/bin/python -m pytest -q tests

echo '=== Compute REAL fitted-model evidence locally (no model search) ==='
PYTHONPATH=. .venv/bin/python -m ml.case_forensics_v11
PYTHONPATH=. .venv/bin/python -m ml.case_enhancement_v11
PYTHONPATH=. .venv/bin/python scripts/export_case_audit_v11.py

echo '=== Enforce approved public aggregates ==='
PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
import json
folder=Path('web/public/data')
expected={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json','nhanes-case-audit-v11.json'}
actual={p.name for p in folder.iterdir() if p.is_file()}
assert actual==expected, (actual,expected)
a=json.loads((folder/'nhanes-case-audit-v11.json').read_text())
assert a['schema']=='FRAILTYSCOPE_PUBLIC_CASE_AUDIT_V11'
assert a['provenance']=='REAL_NHANES_AGGREGATE_ONLY'
assert a['counts']['all']==2422 and a['counts']['evaluation']==1257
assert len(a['features'])==14 and len(a['selection']['candidates'])>=6
assert not ({'local_examples','patient_ids','individual_predictions','raw_predictions','dataset_sha256'} & set(a))
assert all(x['n']>=50 for x in a['evaluation']['calibration'])
assert all(x['n']>=100 for x in a['evaluation']['subgroups'])
print('PASS: Only real NHANES aggregate forensic evidence is public')
print('Model:', a['selection']['model'])
print('Calibration rule accepted:',a['enhancement']['rule']['accepted'])
print('Evaluation metrics:',a['evaluation']['metrics'])
PY

echo '=== Validate production frontend in isolated temporary build ==='
BUILD="$(mktemp -d /tmp/frailtyscope-v112-build-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data"
cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-fund --no-audit && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)

git diff --check -- .github/workflows/ci.yml scripts/publish_case_evidence_v11.sh
printf '\nREADY FOR REVIEW: artifact reload independently verified and v0.11 data workbench validated.\n'
printf 'No repeat Optuna search; local learning-curve/calibration fitting only. No GitHub push.\n'
printf 'After reviewing metrics, run: bash scripts/publish_case_evidence_v11.sh\n'
