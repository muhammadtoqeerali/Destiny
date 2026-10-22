#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main'; exit 1; }
[[ -f ml/case_readiness_v19.py ]] || { echo 'ERROR: Install v0.19 first'; exit 1; }
printf '=== Pure source regression tests; NO NHANES training ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Validate PRIVATE intake report metadata only ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_readiness_v19 import canonical_hash,validate_report
cfg=json.loads(Path('research/cases/nhanes_readiness_v19.json').read_text())
out=Path('artifacts/cases')/cfg['case_id']/'readiness_v19'/canonical_hash(cfg)[:12]/'readiness_audit.json'
assert out.is_file(), 'Run the read-only --audit on your workstation first'
r=json.loads(out.read_text())
assert r['dataset_sha256']==cfg['source']['expected_sha256'], 'Wrong dataset fingerprint'
print('PASS: private v0.19 report contract:',validate_report(cfg,r))
print('Participant rows and local reports will NOT be published')
PY
files=(
  .github/workflows/ci.yml
  ml/case_readiness_v19.py
  research/DATA_READINESS_GATE_V19.md
  research/cases/READINESS_TEMPLATE_V19.json
  research/cases/nhanes_readiness_v19.json
  scripts/install_readiness_v19.sh
  scripts/publish_readiness_v19.sh
  tests/test_case_readiness_v19.py
)
mapfile -t already < <(git diff --cached --name-only)
for entry in "${already[@]}"; do
  approved=false
  for permitted in "${files[@]}"; do [[ "$entry" == "$permitted" ]] && approved=true; done
  "$approved" || { echo "ERROR: Unexpected pre-staged file $entry"; exit 1; }
done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Incomplete source-only publication allowlist'; exit 1; }
for entry in "${staged[@]}"; do
  approved=false
  for permitted in "${files[@]}"; do [[ "$entry" == "$permitted" ]] && approved=true; done
  "$approved" || { echo "ERROR: Unapproved staged file $entry"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No personal records, private intake reports, model binaries or public dashboard assets.\n'
read -r -p 'Publish v0.19 source-only dataset-readiness gate? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: GitHub main moved; review first'; exit 1;
}
git commit -m 'feat: pre-model dataset readiness and missingness semantics gate'
git push origin main
printf 'SUCCESS: v0.19 source-only readiness gate pushed; private audit remains local.\n'
