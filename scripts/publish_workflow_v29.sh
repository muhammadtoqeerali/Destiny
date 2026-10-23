#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_workflow_v29.py ]] || { echo 'ERROR: Install v0.29 before publication'; exit 1; }
files=(
 .github/workflows/ci.yml
 ml/case_workflow_v29.py
 research/INTEGRATED_WORKFLOW_V29.md
 research/cases/nhanes_workflow_v29.json
 research/cases/INTEGRATED_WORKFLOW_TEMPLATE_V29.json
 scripts/install_workflow_v29.sh
 scripts/publish_workflow_v29.sh
 tests/test_case_workflow_v29.py
)
allowed_path() {
 for item in "${files[@]}"; do [[ "$1" == "$item" ]] && return 0; done
 return 1
}
while IFS= read -r modified; do
 [[ -z "$modified" ]] && continue
 allowed_path "$modified" || { echo "ERROR: Unexpected modified tracked source: $modified"; exit 1; }
done < <(git diff --name-only)
while IFS= read -r modified; do
 [[ -z "$modified" ]] && continue
 allowed_path "$modified" || { echo "ERROR: Unapproved staged path: $modified"; exit 1; }
done < <(git diff --cached --name-only)
printf '=== Full repository fixture/privacy tests ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify v0.29 source-only protocol ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_workflow_v29 --plan
printf '=== Verify optional private v0.29 documentary review (never stage) ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_workflow_v29 import digest, REPORT_SCHEMA
cfg=json.loads(Path('research/cases/nhanes_workflow_v29.json').read_text())
p=Path('artifacts/cases')/cfg['case_id']/'workflow_v29'/digest(cfg)[:12]/'workflow_review.json'
if p.exists():
    assert p.is_file() and p.stat().st_size<250_000, 'Unexpected private review file'
    review=json.loads(p.read_text())
    assert review.get('schema')==REPORT_SCHEMA, 'Unexpected v0.29 review schema'
    assert review.get('config_sha256')==digest(cfg) and review.get('case_id')==cfg['case_id'], 'Wrong review source'
    assert review.get('route')=='BLOCKED_FOR_NEW_ANALYSIS', 'Invalid analysis clearance'
    assert review.get('v28_private_metadata_verified') is True, 'Missing v0.28 documentary check'
    assert review.get('no_participant_tables_opened') is True, 'Unexpected participant access'
    assert review.get('no_models_fitted') is True and review.get('no_predictions_generated') is True, 'Unexpected real execution'
    assert review.get('no_holdout_targets_accessed') is True and review.get('public_export') is False, 'Privacy boundary changed'
    print('PASS: Private v0.29 documentary review verified; never staged')
else:
    print('Optional v0.29 audit missing; only source-controlled material may be published')
PY
for path in "${files[@]}"; do [[ -f "$path" ]] || {
 echo "ERROR: Missing whitelisted source: $path"; exit 1; }; done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected eight staged source paths only'; exit 1; }
for path in "${staged[@]}"; do
 allowed_path "$path" || { echo "ERROR: Unsafe staged path: $path"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY: no NHANES/HUNT participants, saved models, private reports or predictions staged.\n'
read -r -p 'Publish v0.29 synthetic-only integrated workflow source? Type uppercase YES: ' response
[[ "$response" == YES ]] || { echo 'Publication declined; NO commit or push'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
 echo 'ERROR: Remote main changed. Inspect before any push'; exit 1; }
git commit -m 'feat: synthetic integrated leakage-safe model and reliability workflow'
git push origin main
printf 'SUCCESS: v0.29 source-only integrated workflow published; private evidence remains local.\n'
