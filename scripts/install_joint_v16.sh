#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Existing tracked/staged changes; review before installing v0.16'
  exit 1
fi
[[ -f ml/case_preprocess_selection_v15.py ]] || { echo 'ERROR: Publish/install v0.15 first'; exit 1; }
[[ -f research/cases/nhanes_preprocess_selection_v15.json ]] || { echo 'ERROR: Missing v0.15 protocol'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local main differs from current origin/main'; exit 1;
}
# v0.15 was published at 0bd08dd; later commits are permitted if descended.
git merge-base --is-ancestor 0bd08dd HEAD || { echo 'ERROR: Expected v0.15 GitHub lineage'; exit 1; }
files=(
  ml/case_joint_selection_v16.py
  research/JOINT_MODEL_PREPROCESS_V16.md
  research/cases/nhanes_joint_selection_v16.json
  research/cases/JOINT_SELECTION_TEMPLATE_V16.json
  scripts/install_joint_v16.sh
  scripts/publish_joint_v16.sh
  tests/test_case_joint_selection_v16.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" ]] || { echo "ERROR: Release missing $file"; exit 1; }
  [[ ! -e "$file" ]] || { echo "ERROR: $file exists; refusing overwrite"; exit 1; }
done
[[ -f .github/workflows/ci.yml ]] || { echo 'ERROR: CI workflow missing'; exit 1; }
backup="$(mktemp -d /tmp/frailtyscope-v16-backup-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
mkdir -p ml research/cases scripts tests
for file in "${files[@]}"; do cat "$RELEASE/$file" > "$file"; done
chmod +x scripts/install_joint_v16.sh scripts/publish_joint_v16.sh
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text()
anchor='tests/test_preprocess_selection_v15.py'
assert s.count(anchor)==1 and 'tests/test_case_joint_selection_v16.py' not in s, 'Unexpected v0.15 CI test anchor'
p.write_text(s.replace(anchor,anchor+' tests/test_case_joint_selection_v16.py'))
print('PASS: CI updated for v0.16 pure contract tests')
PY
printf '=== Full Python regression tests; NO real model fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== v0.16 development-only planning; NO fitting or holdout scoring ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_joint_selection_v16 --plan
printf '=== Verify staged/source whitespace safety ===\n'
git diff --check
printf '\nREADY FOR V0.16 WORKSTATION JOINT SEARCH. NO NHANES model was trained by installation.\n'
printf 'To run on this workstation:\n  PYTHONPATH=. .venv/bin/python -m ml.case_joint_selection_v16 --run\n'
printf 'CI backup (temporary): %s\n' "$backup"
