#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: expected main branch';exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: existing tracked/staged changes; review before v0.18 install';exit 1
fi
[[ -f research/cases/nhanes_stability_v17.json ]] || { echo 'ERROR: v0.17 must be installed';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: local main differs from GitHub main';exit 1; }
git merge-base --is-ancestor 2182050 HEAD || { echo 'ERROR: v0.17 GitHub lineage not found';exit 1; }
[[ -f "$RELEASE/SHA256SUMS" ]] || { echo 'ERROR: missing checksum inventory';exit 1; }
(cd "$RELEASE" && sha256sum -c SHA256SUMS)
files=(
 ml/case_reliability_v18.py
 research/RELIABILITY_AND_MISSINGNESS_V18.md
 research/cases/nhanes_reliability_v18.json
 research/cases/RELIABILITY_TEMPLATE_V18.json
 scripts/install_reliability_v18.sh
 scripts/publish_reliability_v18.sh
 tests/test_case_reliability_v18.py
)
for file in "${files[@]}";do
  [[ -f "$RELEASE/$file" ]] || { echo "ERROR: missing $file";exit 1; }
  [[ ! -e "$file" ]] || { echo "ERROR: $file already exists; refuse overwrite";exit 1; }
done
[[ -f .github/workflows/ci.yml ]] || { echo 'ERROR: missing CI workflow';exit 1; }
backup="$(mktemp -d /tmp/frailtyscope-v18-ci-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
mkdir -p ml research/cases scripts tests
for file in "${files[@]}";do cat "$RELEASE/$file" > "$file";done
chmod +x scripts/install_reliability_v18.sh scripts/publish_reliability_v18.sh
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml');s=p.read_text()
anchor='tests/test_case_stability_v17.py'
assert s.count(anchor)==1 and 'tests/test_case_reliability_v18.py' not in s, 'CI patch anchor mismatch'
p.write_text(s.replace(anchor,anchor+' tests/test_case_reliability_v18.py'))
print('PASS: v0.18 fixture tests added to CI')
PY
printf '=== Full repository tests; NO fitted NHANES model ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== v0.18 preflight only; NO fitting or evaluation scoring ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_reliability_v18 --plan
git diff --check
printf '\nREADY FOR V0.18 WORKSTATION RELIABILITY STUDY. No fitting, GitHub push or public export.\n'
printf 'To run local diagnostics explicitly:\n  PYTHONPATH=. .venv/bin/python -m ml.case_reliability_v18 --run\n'
printf 'Temporary CI backup: %s\n' "$backup"
