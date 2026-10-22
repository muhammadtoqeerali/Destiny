#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Existing tracked or staged source changes require review before installation'; exit 1
fi
[[ -f research/cases/nhanes_joint_selection_v16.json ]] || { echo 'ERROR: v0.16 source missing'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Workstation main differs from GitHub main'; exit 1;
}
git merge-base --is-ancestor 9a72f7a HEAD || { echo 'ERROR: Expected verified v0.16 release ancestry'; exit 1; }
cd "$RELEASE"
sha256sum -c MANIFEST.sha256
cd "$ROOT"
files=(
 ml/case_stability_v17.py
 research/SELECTION_STABILITY_V17.md
 research/cases/nhanes_stability_v17.json
 research/cases/STABILITY_TEMPLATE_V17.json
 scripts/install_stability_v17.sh
 scripts/publish_stability_v17.sh
 tests/test_case_stability_v17.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" ]] || { echo "ERROR: Release input missing: $file"; exit 1; }
  [[ ! -e "$file" ]] || { echo "ERROR: $file already exists. Refusing overwrite"; exit 1; }
done
[[ -f .github/workflows/ci.yml ]] || { echo 'ERROR: CI workflow missing'; exit 1; }
backup="$(mktemp -d /tmp/frailtyscope-v17-ci-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
mkdir -p ml research/cases scripts tests
for file in "${files[@]}"; do cat "$RELEASE/$file" > "$file"; done
chmod +x scripts/install_stability_v17.sh scripts/publish_stability_v17.sh
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml');old=p.read_text()
anchor='tests/test_case_joint_selection_v16.py'
assert old.count(anchor)==1 and 'tests/test_case_stability_v17.py' not in old, 'Unexpected CI source state'
p.write_text(old.replace(anchor,anchor+' tests/test_case_stability_v17.py'))
print('PASS: GitHub CI includes pure v0.17 arithmetic and privacy-contract tests')
PY
printf '=== Full Python regression and contract tests; NO NHANES model fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Check verified existing v0.16 research result and new design only ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_stability_v17 --plan
printf '=== Source whitespace checks ===\n'
git diff --check
printf '\nREADY FOR V0.17 WORKSTATION STABILITY STUDY. NO NHANES MODEL FITTED DURING INSTALLATION.\n'
printf 'To explicitly run development-fold models on this workstation:\n'
printf '  PYTHONPATH=. .venv/bin/python -m ml.case_stability_v17 --run\n'
printf 'Temporary CI backup: %s\n' "$backup"
