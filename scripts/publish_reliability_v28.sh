#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_reliability_v28.py ]] || { echo 'ERROR: Install v0.28 first'; exit 1; }
files=(
  .github/workflows/ci.yml
  ml/case_reliability_v28.py
  research/RELIABILITY_UNCERTAINTY_V28.md
  research/cases/nhanes_reliability_v28.json
  research/cases/RELIABILITY_TEMPLATE_V28.json
  scripts/install_reliability_v28.sh
  scripts/publish_reliability_v28.sh
  tests/test_case_reliability_v28.py
)
allowed_path() {
  for path in "${files[@]}"; do [[ "$1" == "$path" ]] && return 0; done
  return 1
}
while IFS= read -r edited; do
  [[ -z "$edited" ]] && continue
  allowed_path "$edited" || { echo "ERROR: Disallowed modified file: $edited"; exit 1; }
done < <(git diff --name-only)
while IFS= read -r staged_path; do
  [[ -z "$staged_path" ]] && continue
  allowed_path "$staged_path" || { echo "ERROR: Disallowed pre-staged file: $staged_path"; exit 1; }
done < <(git diff --cached --name-only)
printf '=== Full fixture/privacy regression suite, synthetic only ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify blocked v0.28 documentary plan ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_reliability_v28 --plan
printf '=== Optional immutable PRIVATE metadata verification ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_reliability_v28 import digest, REPORT_SCHEMA
cfg=json.loads(Path('research/cases/nhanes_reliability_v28.json').read_text())
p=(Path('artifacts/cases')/cfg['case_id']/'reliability_v28'/
   digest(cfg)[:12]/'reliability_review.json')
if p.exists():
    assert p.is_file() and p.stat().st_size<250_000, 'Unexpected report file'
    obj=json.loads(p.read_text())
    assert obj.get('schema')==REPORT_SCHEMA and obj.get('config_sha256')==digest(cfg), 'Review mismatched'
    assert obj.get('case_id')==cfg['case_id'] and obj.get('route')=='BLOCKED_FOR_NEW_ANALYSIS', 'Wrong case or clearance'
    assert obj.get('v27_private_metadata_verified') is True, 'Missing predecessor verification'
    assert obj.get('no_participant_tables_opened') is True and obj.get('no_models_fitted') is True, 'Unexpected real-data work'
    assert obj.get('no_predictions_generated') is True and obj.get('no_holdout_targets_accessed') is True, 'Unexpected target access'
    assert obj.get('public_export') is False and obj.get('synthetic_only') is True, 'Private boundary changed'
    print('PASS: Optional private metadata-only review verified, never staged')
else:
    print('Optional --audit has not been run; source-only publication can be reviewed')
PY
for file in "${files[@]}"; do [[ -f "$file" ]] || {
  echo "ERROR: Missing approved source file: $file"; exit 1;
}; done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq 8 ]] || { echo 'ERROR: Expected eight source paths only'; exit 1; }
for file in "${staged[@]}"; do
  allowed_path "$file" || { echo "ERROR: Unsafe staged path: $file"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No NHANES/HUNT tables, reports, models, outputs or public assets staged.\n'
read -r -p 'Publish v0.28 synthetic-only reliability diagnostics source? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; NO commit or push'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Remote main changed; review before publication'; exit 1;
}
git commit -m 'feat: synthetic OOF calibration and conditional cluster uncertainty diagnostics'
git push origin main
printf 'SUCCESS: v0.28 source-only reliability module published; private artifacts stay local.\n'
