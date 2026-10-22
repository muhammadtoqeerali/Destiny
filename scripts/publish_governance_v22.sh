#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected Git main branch'; exit 1; }
[[ -f ml/case_governance_v22.py ]] || { echo 'ERROR: Install v0.22 first'; exit 1; }
files=(
 .github/workflows/ci.yml
 ml/case_governance_v22.py
 research/RESEARCH_METHODS_ATLAS_V22.md
 research/cases/nhanes_governance_v22.json
 research/cases/RESEARCH_GOVERNANCE_TEMPLATE_V22.json
 scripts/install_governance_v22.sh
 scripts/publish_governance_v22.sh
 tests/test_case_governance_v22.py
)
# Avoid accidentally incorporating unrelated edited tracked files.
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed=false
  for path in "${files[@]}"; do [[ "$changed" == "$path" ]] && allowed=true; done
  "$allowed" || { echo "ERROR: Unexpected modified tracked source: $changed"; exit 1; }
done < <(git diff --name-only)
printf '=== Full repository regression and privacy tests; NO fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify private aggregate evidence metadata ONLY ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_governance_v22 import validate_protocol,validate_ledger,digest_json
cfg=validate_protocol(json.loads(Path('research/cases/nhanes_governance_v22.json').read_text()))
p=(Path('artifacts/cases')/cfg['case_id']/'governance_v22'/
   digest_json(cfg)[:12]/'evidence_ledger.json')
assert p.is_file(),'Run v0.22 --audit first; do not push private evidence'
report=json.loads(p.read_text())
summary=validate_ledger(cfg,report)
checks = report.get('local_evidence_checks', [])
assert (
    len(checks) == 3
    and all(item.get('state') == 'metadata_valid' for item in checks)
), 'Expected local v0.19/v0.20/v0.21 metadata checks'
print('PASS: Private source evidence ledger metadata:',summary)
print('PRIVATE LEDGER, AUDIT CONTENT, DATASETS AND MODELS ARE NOT STAGED')
PY
while IFS= read -r changed; do
  [[ -z "$changed" ]] && continue
  allowed=false
  for path in "${files[@]}"; do [[ "$changed" == "$path" ]] && allowed=true; done
  "$allowed" || { echo "ERROR: Unexpected path already staged: $changed"; exit 1; }
done < <(git diff --cached --name-only)
for path in "${files[@]}"; do [[ -f "$path" ]] || { echo "ERROR: Missing whitelisted source $path"; exit 1; }; done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Source allowlist mismatch'; exit 1; }
for changed in "${staged[@]}"; do
  allowed=false
  for path in "${files[@]}"; do [[ "$changed" == "$path" ]] && allowed=true; done
  "$allowed" || { echo "ERROR: Disallowed path staged: $changed"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE-ONLY: no raw tables, HUNT data, fitted models, local aggregate reports, or public prediction assets.\n'
read -r -p 'Publish v0.22 source-only research evidence framework? Type uppercase YES: ' reply
[[ "$reply" == YES ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Remote main changed; review before publication'; exit 1;
}
git commit -m 'feat: case-independent research evidence and methods readiness register'
git push origin main
printf 'SUCCESS: v0.22 source-only framework published; all local research evidence remains private.\n'
