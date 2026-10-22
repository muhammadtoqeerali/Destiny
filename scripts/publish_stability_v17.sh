#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_stability_v17.py ]] || { echo 'ERROR: Install v0.17 first'; exit 1; }
printf '=== Source-only research and privacy tests; NO fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Validate local stability metadata without loading any model ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_joint_selection_v16 import digest_json
from ml.case_stability_v17 import validate_local_report
cfg=json.loads(Path('research/cases/nhanes_stability_v17.json').read_text())
joint=json.loads(Path(cfg['v16_config']).read_text())
manifest=json.loads(Path(joint['manifest']).read_text())
path=Path('artifacts/cases')/cfg['case_id']/'stability_v17'/digest_json(cfg)[:12]/'selection_stability.json'
assert path.is_file(), 'Run workstation-only --run before publishing source'
result=json.loads(path.read_text())
print('PASS: Protected development-only report:',validate_local_report(cfg,joint,manifest,result))
print('Real dataset, models, participant predictions and local report are NOT staged.')
PY
files=(
 .github/workflows/ci.yml
 ml/case_stability_v17.py
 research/SELECTION_STABILITY_V17.md
 research/cases/nhanes_stability_v17.json
 research/cases/STABILITY_TEMPLATE_V17.json
 scripts/install_stability_v17.sh
 scripts/publish_stability_v17.sh
 tests/test_case_stability_v17.py
)
mapfile -t before < <(git diff --cached --name-only)
for file in "${before[@]}"; do
  valid=false
  for allowed in "${files[@]}"; do [[ "$file" == "$allowed" ]] && valid=true; done
  "$valid" || { echo "ERROR: Unapproved pre-staged path: $file"; exit 1; }
done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ ${#staged[@]} -eq ${#files[@]} ]] || { echo 'ERROR: Incomplete exact source staging'; exit 1; }
for file in "${staged[@]}"; do
  valid=false
  for allowed in "${files[@]}"; do [[ "$file" == "$allowed" ]] && valid=true; done
  "$valid" || { echo "ERROR: Unapproved staged path: $file"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY: no public aggregate, local model, private dataset or research report.\n'
read -r -p 'Push FrailtyScope v0.17 source-only? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: GitHub main moved; review first'; exit 1;
}
git commit -m 'feat: development-only joint selection stability and calibration audit'
git push origin main
printf 'SUCCESS: v0.17 source-only stability workflow published; no private evidence published.\n'
