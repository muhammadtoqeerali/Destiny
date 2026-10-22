#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main'; exit 1; }
[[ -f ml/case_task_models_v26.py ]] || { echo 'ERROR: v0.26 must be installed first'; exit 1; }
files=(
  .github/workflows/ci.yml
  ml/case_task_models_v26.py
  research/TASK_MODEL_VALIDATION_V26.md
  research/cases/nhanes_task_models_v26.json
  research/cases/TASK_MODEL_TEMPLATE_V26.json
  scripts/install_task_models_v26.sh
  scripts/publish_task_models_v26.sh
  tests/test_case_task_models_v26.py
)
allowed_path() {
  for file in "${files[@]}"; do [[ "$1" == "$file" ]] && return 0; done
  return 1
}
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed_path "$changed" || { echo "ERROR: Unexpected modified file: $changed"; exit 1; }
done < <(git diff --name-only)
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed_path "$changed" || { echo "ERROR: Unapproved staged file: $changed"; exit 1; }
done < <(git diff --cached --name-only)
printf '=== Full repository fixture and privacy tests; synthetic only ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify blocked v0.26 source-only preflight ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_task_models_v26 --plan
printf '=== Optional PRIVATE metadata review verification (never staged) ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_task_models_v26 import digest, REPORT_SCHEMA
cfg=json.loads(Path('research/cases/nhanes_task_models_v26.json').read_text())
p=Path('artifacts/cases')/cfg['case_id']/'task_models_v26'/digest(cfg)[:12]/'task_model_review.json'
if p.is_file():
    r=json.loads(p.read_text())
    assert r.get('schema')==REPORT_SCHEMA, 'Wrong review schema'
    assert r.get('config_sha256')==digest(cfg), 'Stale review/config pair'
    assert r.get('case_id')==cfg['case_id'], 'Wrong case in private metadata'
    assert r.get('route')=='BLOCKED_FOR_NEW_ANALYSIS', 'Unexpected clearance'
    assert r.get('v25_private_metadata_verified') is True, 'Missing previous audit verification'
    assert r.get('no_participant_tables_opened') is True, 'Data boundary broken'
    assert r.get('no_models_fitted') is True and r.get('no_predictions_generated') is True, 'Unexpected real execution'
    assert r.get('no_holdout_targets_accessed') is True and r.get('public_export') is False, 'Private boundary broken'
    print('PASS: Private v0.26 documentary audit verified; never staged')
else:
    print('Optional --audit not run; no private evidence required for source-only publication')
PY
for file in "${files[@]}"; do [[ -f "$file" ]] || {
  echo "ERROR: Missing allowlisted source: $file"; exit 1;
}; done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || {
  echo 'ERROR: Expected exactly eight staged source paths'; exit 1;
}
for file in "${staged[@]}"; do
  allowed_path "$file" || { echo "ERROR: Non-source path staged: $file"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No NHANES/HUNT participant data, private metadata, fitted models, predictions or public assets staged.\n'
read -r -p 'Publish v0.26 synthetic task-aware comparison source only? Type uppercase YES: ' reply
[[ "$reply" == YES ]] || { echo 'Publication not authorized'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Remote main changed; inspect before publication'; exit 1;
}
git commit -m 'feat: synthetic task-aware grouped and forward-CV model comparison'
git push origin main
printf 'SUCCESS: v0.26 source-only modeling protocol published; private artifacts remain private.\n'
