#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_harmonization_v24.py ]] || { echo 'ERROR: Install v0.24 first'; exit 1; }
files=(
  .github/workflows/ci.yml
  ml/case_harmonization_v24.py
  research/HARMONIZATION_CONTRACT_V24.md
  research/cases/nhanes_harmonization_v24.json
  research/cases/HARMONIZATION_TEMPLATE_V24.json
  scripts/install_harmonization_v24.sh
  scripts/publish_harmonization_v24.sh
  tests/test_case_harmonization_v24.py
)
allowed_path() {
  for allowed in "${files[@]}"; do [[ "$1" == "$allowed" ]] && return 0; done
  return 1
}
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed_path "$changed" || { echo "ERROR: Unexpected changed source path: $changed"; exit 1; }
done < <(git diff --name-only)
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed_path "$changed" || { echo "ERROR: Unapproved already-staged path: $changed"; exit 1; }
done < <(git diff --cached --name-only)
printf '=== Full Python tests; no NHANES fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== v0.24 source-only preflight ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_harmonization_v24 --plan
printf '=== Optional PRIVATE metadata review verification ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_harmonization_v24 import digest, REPORT_SCHEMA
cfg=json.loads(Path('research/cases/nhanes_harmonization_v24.json').read_text())
p=(Path('artifacts/cases')/cfg['case_id']/'harmonization_v24'/
   digest(cfg)[:12]/'harmonization_review.json')
if p.is_file():
    r=json.loads(p.read_text())
    assert r.get('schema')==REPORT_SCHEMA, 'Invalid aggregate review schema'
    assert r.get('config_sha256')==digest(cfg), 'Stale review version'
    assert r.get('case_id')==cfg['case_id'], 'Wrong audit case'
    assert r.get('route')=='BLOCKED_FOR_NEW_ANALYSIS', 'Unexpected research clearance'
    assert r.get('v23_private_metadata_verified') is True, 'Missing v0.23 metadata check'
    assert r.get('no_participant_tables_opened') is True, 'Private table boundary violated'
    assert r.get('no_models_fitted') is True, 'Unexpected model fit'
    assert r.get('no_holdout_targets_accessed') is True, 'Unexpected holdout access'
    assert r.get('public_export') is False, 'Private evidence export attempted'
    print('PASS: Private source-only v0.24 metadata checked, report excluded from staging')
else:
    print('Optional metadata audit not yet executed; source-only publication remains permitted')
PY
for path in "${files[@]}"; do [[ -f "$path" ]] || {
  echo "ERROR: Missing approved source file: $path"; exit 1;
}; done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || {
  echo 'ERROR: Expected exactly eight source-only paths'; exit 1;
}
for path in "${staged[@]}"; do
  allowed_path "$path" || { echo "ERROR: Disallowed staged path: $path"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY: no HUNT/NHANES participant data, models, private reports or predictions.\n'
read -r -p 'Publish v0.24 source-only harmonization blueprint? Type uppercase YES: ' reply
[[ "$reply" == YES ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Remote main changed; review before publication'; exit 1;
}
git commit -m 'feat: source-aware harmonization contracts and synthetic mapper'
git push origin main
printf 'SUCCESS: v0.24 source-only contract published; research artifacts remain private.\n'
