#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main'; exit 1; }
[[ -f ml/case_foldsafe_v25.py ]] || { echo 'ERROR: v0.25 not installed'; exit 1; }
files=(
  .github/workflows/ci.yml
  ml/case_foldsafe_v25.py
  research/FOLDSAFE_PREPROCESSING_V25.md
  research/cases/nhanes_foldsafe_v25.json
  research/cases/FOLDSAFE_TEMPLATE_V25.json
  scripts/install_foldsafe_v25.sh
  scripts/publish_foldsafe_v25.sh
  tests/test_case_foldsafe_v25.py
)
allowed_path() {
  for approved in "${files[@]}"; do [[ "$1" == "$approved" ]] && return 0; done
  return 1
}
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed_path "$changed" || { echo "ERROR: Unexpected modified tracked file: $changed"; exit 1; }
done < <(git diff --name-only)
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed_path "$changed" || { echo "ERROR: Unexpected already-staged path: $changed"; exit 1; }
done < <(git diff --cached --name-only)
printf '=== Full Python fixture and privacy tests ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify source-only v0.25 preflight ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_foldsafe_v25 --plan
printf '=== Validate optional PRIVATE audit metadata (not staged) ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_foldsafe_v25 import digest, REPORT_SCHEMA
cfg=json.loads(Path('research/cases/nhanes_foldsafe_v25.json').read_text())
p=(Path('artifacts/cases')/cfg['case_id']/'foldsafe_v25'/
   digest(cfg)[:12]/'foldsafe_review.json')
if p.is_file():
    obj=json.loads(p.read_text())
    assert obj.get('schema')==REPORT_SCHEMA, 'Unexpected private v0.25 schema'
    assert obj.get('config_sha256')==digest(cfg), 'Stale protocol fingerprint'
    assert obj.get('case_id')==cfg['case_id'], 'Wrong case'
    assert obj.get('route')=='BLOCKED_FOR_NEW_ANALYSIS', 'Unexpected model clearance'
    assert obj.get('v24_private_metadata_verified') is True, 'Missing prior metadata check'
    assert obj.get('no_participant_tables_opened') is True, 'Unexpected private table access'
    assert obj.get('no_models_fitted') is True, 'Unexpected models'
    assert obj.get('no_holdout_targets_accessed') is True, 'Unexpected holdout access'
    assert obj.get('public_export') is False, 'Unexpected private export'
    print('PASS: Optional private v0.25 metadata verified and excluded from staging')
else:
    print('Optional --audit not run; source-only publication can proceed')
PY
for item in "${files[@]}"; do [[ -f "$item" ]] || { echo "ERROR: Missing allowlisted file: $item"; exit 1; }; done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Unexpected source-only stage count'; exit 1; }
for item in "${staged[@]}"; do
  allowed_path "$item" || { echo "ERROR: Disallowed file staged: $item"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No participant data, models, private ledgers, predictions or public assets staged.\n'
read -r -p 'Publish v0.25 fold-safe preprocessing source only? Type uppercase YES: ' reply
[[ "$reply" == YES ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Remote main changed; inspect before publication'; exit 1;
}
git commit -m 'feat: synthetic fold-safe preprocessing and partition guards'
git push origin main
printf 'SUCCESS: v0.25 source-only framework published; local private artifacts remain private.\n'
