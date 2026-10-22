#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_source_semantics_v21.py ]] || { echo 'ERROR: Install v0.21 source first'; exit 1; }
printf '=== Full repository tests; NO NHANES fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify LOCAL research report; never publish the report ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_source_semantics_v21 import canonical_sha,validate_report
cfg=json.loads(Path('research/cases/nhanes_source_semantics_v21.json').read_text())
path=(Path('artifacts/cases')/cfg['case_id']/'source_semantics_v21'/
      canonical_sha(cfg)[:12]/'encoding_diagnostic.json')
assert path.is_file(), 'Run v0.21 development-only diagnostic on workstation before publishing source'
r=json.loads(path.read_text())
print('PASS: Private report verified:',validate_report(cfg,r))
print('Participant rows and local model diagnostics NOT staged')
PY
files=(
 .github/workflows/ci.yml
 ml/case_source_semantics_v21.py
 research/SOURCE_SEMANTICS_V21.md
 research/cases/nhanes_source_semantics_v21.json
 research/cases/SOURCE_SEMANTICS_TEMPLATE_V21.json
 scripts/install_source_semantics_v21.sh
 scripts/publish_source_semantics_v21.sh
 tests/test_case_source_semantics_v21.py
)
mapfile -t staged_before < <(git diff --cached --name-only)
for file in "${staged_before[@]}"; do
  approved=false
  for item in "${files[@]}"; do [[ "$file" == "$item" ]] && approved=true; done
  "$approved" || { echo "ERROR: Unapproved previously staged path: $file"; exit 1; }
done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Incomplete source allowlist'; exit 1; }
for file in "${staged[@]}"; do
  approved=false
  for item in "${files[@]}"; do [[ "$file" == "$item" ]] && approved=true; done
  "$approved" || { echo "ERROR: Unapproved staged path: $file"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No raw/processed data, models, local research reports or public dashboard changes.\n'
read -r -p 'Publish v0.21 source-only encoding diagnostic? Type uppercase YES: ' reply
[[ "$reply" == YES ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Origin/main changed; review before publication'; exit 1;
}
git commit -m 'feat: source-aware physical-function encoding diagnostics'
git push origin main
printf 'SUCCESS: v0.21 source-only experiment published; local data and results remain private.\n'
