#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_temporal_v27.py ]] || { echo 'ERROR: Install v0.27 first'; exit 1; }
files=(
 .github/workflows/ci.yml
 ml/case_temporal_v27.py
 research/TEMPORAL_SURVIVAL_LONGITUDINAL_V27.md
 research/cases/nhanes_temporal_v27.json
 research/cases/TEMPORAL_TEMPLATE_V27.json
 scripts/install_temporal_v27.sh
 scripts/publish_temporal_v27.sh
 tests/test_case_temporal_v27.py
)
allowed_path() {
  for allowed in "${files[@]}"; do [[ "$1" == "$allowed" ]] && return 0; done
  return 1
}
while IFS= read -r changed; do
 [[ -z "$changed" ]] && continue
 allowed_path "$changed" || { echo "ERROR: Unexpected modified tracked file: $changed"; exit 1; }
done < <(git diff --name-only)
while IFS= read -r changed; do
 [[ -z "$changed" ]] && continue
 allowed_path "$changed" || { echo "ERROR: Unexpected pre-staged file: $changed"; exit 1; }
done < <(git diff --cached --name-only)
printf '=== Full fixture/privacy tests; no real research fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-only blocked v0.27 preflight ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_temporal_v27 --plan
printf '=== Optional immutable PRIVATE audit metadata verification ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_temporal_v27 import digest, REPORT_SCHEMA
cfg=json.loads(Path('research/cases/nhanes_temporal_v27.json').read_text())
p=Path('artifacts/cases')/cfg['case_id']/'temporal_v27'/digest(cfg)[:12]/'temporal_review.json'
if p.is_file():
    report=json.loads(p.read_text())
    assert report.get('schema')==REPORT_SCHEMA, 'Unexpected v0.27 audit schema'
    assert report.get('case_id')==cfg['case_id'] and report.get('config_sha256')==digest(cfg), 'Stale/wrong audit'
    assert report.get('v26_private_metadata_verified') is True, 'Prior v0.26 audit metadata not verified'
    assert report.get('route')=='BLOCKED_FOR_NEW_ANALYSIS', 'Invalid analysis clearance'
    assert report.get('no_participant_tables_opened') is True, 'Unexpected research data access'
    assert report.get('no_models_fitted') is True and report.get('no_predictions_generated') is True, 'Unexpected fitting/scoring'
    assert report.get('no_holdout_targets_accessed') is True and report.get('public_export') is False, 'Privacy boundary changed'
    print('PASS: Private v0.27 documentary metadata verified, never staged')
else:
    print('Optional v0.27 audit absent; source-only publication does not require it')
PY
for path in "${files[@]}"; do [[ -f "$path" ]] || {
 echo "ERROR: Missing approved source file $path"; exit 1; }; done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || {
 echo 'ERROR: Exactly eight approved source paths required'; exit 1; }
for path in "${staged[@]}"; do
 allowed_path "$path" || { echo "ERROR: Disallowed staged file: $path"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY: private reports, data, fitted models, predictions and public assets NOT staged.\n'
read -r -p 'Publish v0.27 synthetic temporal foundations source only? Type uppercase YES: ' reply
[[ "$reply" == YES ]] || { echo 'Publication declined; no commit or push'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
 echo 'ERROR: Origin changed; inspect before publication'; exit 1; }
git commit -m 'feat: synthetic censored survival and next-visit temporal foundations'
git push origin main
printf 'SUCCESS: v0.27 source-only temporal foundations published. Private artifacts remain local.\n'
