#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_dictionary_timing_v23.py ]] || { echo 'ERROR: v0.23 source not installed'; exit 1; }
files=(
  .github/workflows/ci.yml
  ml/case_dictionary_timing_v23.py
  research/FEATURE_AVAILABILITY_V23.md
  research/cases/nhanes_dictionary_timing_v23.json
  research/cases/FEATURE_DICTIONARY_TEMPLATE_V23.json
  scripts/install_dictionary_timing_v23.sh
  scripts/publish_dictionary_timing_v23.sh
  tests/test_case_dictionary_timing_v23.py
)
allowed_path() {
  for path in "${files[@]}"; do [[ "$1" == "$path" ]] && return 0; done
  return 1
}
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed_path "$changed" || { echo "ERROR: Unapproved unstaged change: $changed"; exit 1; }
done < <(git diff --name-only)
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed_path "$changed" || { echo "ERROR: Unapproved pre-staged change: $changed"; exit 1; }
done < <(git diff --cached --name-only)
printf '=== Full source/privacy regression tests; no data fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify source-only source-index preflight ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_dictionary_timing_v23 --plan
printf '=== Validate optional immutable PRIVATE documentary ledger metadata ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_dictionary_timing_v23 import SCHEMA, REPORT_SCHEMA, digest
config=json.loads(Path('research/cases/nhanes_dictionary_timing_v23.json').read_text())
assert config['schema']==SCHEMA, 'Wrong source dictionary protocol'
p=(Path('artifacts/cases')/config['case_id']/'field_timing_v23'/
   digest(config)[:12]/'dictionary_timing_audit.json')
if p.exists():
    report=json.loads(p.read_text())
    assert report['schema']==REPORT_SCHEMA, 'Unexpected private audit schema'
    assert report['protocol_sha256']==digest(config), 'Wrong private audit source version'
    assert report['no_models_fitted'] is True, 'Unexpected model fitting'
    assert report['no_data_rows_opened'] is True, 'Unexpected private table access'
    assert report['no_holdout_targets_accessed'] is True, 'Unexpected holdout access'
    assert report['public_export'] is False, 'Private audit export policy broken'
    assert report['route']=='BLOCKED_FOR_PREDICTION_PROTOCOL_REVIEW', 'Unexpected override'
    print('PASS: Optional private v0.23 audit metadata verified and excluded from staging')
else:
    print('Optional v0.23 --audit not yet run; source publication can proceed safely')
PY
for file in "${files[@]}"; do
  [[ -f "$file" ]] || { echo "ERROR: Missing whitelisted file: $file"; exit 1; }
done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || {
  echo 'ERROR: Expected exactly eight source-only files'; exit 1;
}
for changed in "${staged[@]}"; do
  allowed_path "$changed" || { echo "ERROR: Unsafe staged path $changed"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. Private data, saved model, patient records, predictions and aggregate reports are NOT staged.\n'
read -r -p 'Publish v0.23 feature dictionary and index gate? Type uppercase YES: ' reply
[[ "$reply" == YES ]] || { echo 'Publication not authorized'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Origin changed since installation; review before publishing'; exit 1;
}
git commit -m 'feat: metadata-only predictor dictionary and timing gate'
git push origin main
printf 'SUCCESS: v0.23 source-only protocol published; all local research artifacts remain private.\n'
