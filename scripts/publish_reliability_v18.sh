#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: expected main branch';exit 1; }
[[ -f ml/case_reliability_v18.py ]] || { echo 'ERROR: install v0.18 first';exit 1; }
printf '=== Source-only tests; NO model fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Local metadata integrity check (no model loading) ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_reliability_v18 import get_context,validate_local_report
from ml.case_joint_selection_v16 import digest_json
root=Path('.').resolve()
p=root/'research/cases/nhanes_reliability_v18.json'
cfg,orig,saved,plan=get_context(root,p)
joint,manifest,_,_,sha,_,_,_=orig
report_path=root/'artifacts'/'cases'/cfg['case_id']/'reliability_v18'/digest_json(cfg)[:12]/'reliability_audit.json'
assert report_path.is_file(), 'Run workstation --run before publication'
report=json.loads(report_path.read_text())
assert report.get('dataset_sha256')==sha, 'Dataset changed since local reliability study'
result=validate_local_report(cfg,joint,manifest,report)
print('PASS: local v0.18 metadata validated:',json.dumps(result,sort_keys=True))
print('Participant-level records, models, and local reports remain ignored/private.')
PY
files=(
 .github/workflows/ci.yml
 ml/case_reliability_v18.py
 research/RELIABILITY_AND_MISSINGNESS_V18.md
 research/cases/nhanes_reliability_v18.json
 research/cases/RELIABILITY_TEMPLATE_V18.json
 scripts/install_reliability_v18.sh
 scripts/publish_reliability_v18.sh
 tests/test_case_reliability_v18.py
)
mapfile -t existing < <(git diff --cached --name-only)
for p in "${existing[@]}";do
  approved=false
  for allowed in "${files[@]}";do [[ "$p" == "$allowed" ]] && approved=true;done
  "$approved" || { echo "ERROR: unapproved already staged file: $p";exit 1; }
done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: staged source allowlist incomplete';exit 1; }
for p in "${staged[@]}";do
  approved=false
  for allowed in "${files[@]}";do [[ "$p" == "$allowed" ]] && approved=true;done
  "$approved" || { echo "ERROR: unexpected staged path $p";exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No medical rows, local research outputs, predictions, new fitted calibrator or trained model binary.\n'
read -r -p 'Publish v0.18 source-only reliability workflow? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: origin/main advanced; review first';exit 1; }
git commit -m 'feat: post-hoc development calibration and missingness reliability audit'
git push origin main
printf 'SUCCESS: v0.18 source-only release published. Private diagnostics remain local.\n'
