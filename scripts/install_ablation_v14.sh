#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT=/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Use main branch'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Commit or review existing source changes first'; exit 1; }
[[ -f research/cases/nhanes_strategy_v13.json ]] || { echo 'ERROR: v0.13 release not installed'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Local main differs from GitHub main'; exit 1; }
files=(ml/case_ablation_v14.py research/cases/nhanes_ablation_v14.json research/cases/ABLATION_TEMPLATE_V14.json research/DEVELOPMENT_ABLATIONS_V14.md scripts/install_ablation_v14.sh scripts/publish_ablation_v14.sh tests/test_case_ablation_v14.py)
for path in "${files[@]}"; do
  [[ ! -e "$path" ]] || { echo "ERROR: $path exists. Refuse to overwrite."; exit 1; }
  [[ -f "$RELEASE/$path" ]] || { echo "ERROR: Missing release input $path"; exit 1; }
done
mkdir -p ml research/cases scripts tests
for path in "${files[@]}"; do cat "$RELEASE/$path" > "$path"; done
chmod +x scripts/install_ablation_v14.sh scripts/publish_ablation_v14.sh
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text(); old='tests/test_case_strategy_v13.py';new=old+' tests/test_case_ablation_v14.py'
assert s.count(old)==1 and 'tests/test_case_ablation_v14.py' not in s,'Unexpected CI schema'
p.write_text(s.replace(old,new))
print('PASS: Added v0.14 structural tests to GitHub CI')
PY
printf '=== Full regression suite (NO real NHANES fitting) ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Development-only PLAN (NO model fitting) ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_ablation_v14 --plan
git diff --check
printf '\nREADY FOR WORKSTATION ABLATION. NO real NHANES training or publishing occurred.\n'
printf 'To fit repeat-fold diagnostic models locally, execute:\n  PYTHONPATH=. .venv/bin/python -m ml.case_ablation_v14 --run\n'
