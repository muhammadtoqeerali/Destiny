#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main'; exit 1; }
[[ -f ml/case_joint_selection_v16.py ]] || { echo 'ERROR: Install v0.16 first'; exit 1; }
printf '=== Test source contracts; NO real model fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Check local development-only research report; DO NOT publish artifact ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_joint_selection_v16 import digest_json, validate_local_release
p=Path('research/cases/nhanes_joint_selection_v16.json')
cfg=json.loads(p.read_text())
out=Path('artifacts/cases')/cfg['case_id']/'joint_selection_v16'/digest_json(cfg)[:12]
rp=out/'joint_selection.json'
model=out/'winner_development_only.joblib'
assert rp.is_file(), 'Run workstation --run before source publication'
report=json.loads(rp.read_text())
verified=validate_local_release(cfg, report, model.is_file())
print('PASS: Development-only local research artifact verified:', json.dumps(verified, sort_keys=True))
print('Local models and reports will NOT be staged or published')
PY
files=(
 .github/workflows/ci.yml
 ml/case_joint_selection_v16.py
 research/JOINT_MODEL_PREPROCESS_V16.md
 research/cases/nhanes_joint_selection_v16.json
 research/cases/JOINT_SELECTION_TEMPLATE_V16.json
 scripts/install_joint_v16.sh
 scripts/publish_joint_v16.sh
 tests/test_case_joint_selection_v16.py
)
# Reject unrelated staged paths, including data, artifacts or other source changes.
mapfile -t staged_before < <(git diff --cached --name-only)
for file in "${staged_before[@]}"; do
  allowed=false
  for approved in "${files[@]}"; do [[ "$file" == "$approved" ]] && allowed=true; done
  "$allowed" || { echo "ERROR: Unapproved pre-staged path $file"; exit 1; }
done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ ${#staged[@]} == ${#files[@]} ]] || { echo 'ERROR: Exact source-only allowlist mismatch'; exit 1; }
for file in "${staged[@]}"; do
  allowed=false
  for approved in "${files[@]}"; do [[ "$file" == "$approved" ]] && allowed=true; done
  "$allowed" || { echo "ERROR: Unapproved staged path $file"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No data, models, case reports, per-person scores or new public assets.\n'
read -r -p 'Publish v0.16 source-only joint selector? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: GitHub main moved; review before publishing'; exit 1;
}
git commit -m 'feat: nested development-only joint model and preprocessing selection'
git push origin main
printf 'SUCCESS: v0.16 source-only selector pushed; no real-data artifact published.\n'
