#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_reliability_v28.py && -f research/cases/nhanes_reliability_v28.json ]] || {
 echo 'ERROR: Published v0.28 source prerequisite is missing'; exit 1; }
[[ -f .venv/bin/python ]] || { echo 'ERROR: Missing workstation Python environment'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
 echo 'ERROR: Tracked working-tree/staged changes exist; review before installation'; exit 1
fi
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
 echo 'ERROR: Local and remote main differ; review before installation'; exit 1; }
git merge-base --is-ancestor 85c29dc HEAD || {
 echo 'ERROR: Published v0.28 commit is not in local history'; exit 1; }
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
 ml/case_workflow_v29.py
 research/INTEGRATED_WORKFLOW_V29.md
 research/cases/nhanes_workflow_v29.json
 research/cases/INTEGRATED_WORKFLOW_TEMPLATE_V29.json
 scripts/install_workflow_v29.sh
 scripts/publish_workflow_v29.sh
 tests/test_case_workflow_v29.py
)
for path in "${files[@]}"; do
 [[ -f "$RELEASE/$path" && ! -e "$path" ]] || {
 echo "ERROR: Missing release file or existing destination: $path"; exit 1; }
done
backup="$(mktemp -d /tmp/frailtyscope-v29-original-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: v0.29 installation interrupted; restoring CI, backup: $backup"
    cp "$backup/ci.yml" .github/workflows/ci.yml || true
    for path in "${files[@]}"; do rm -f -- "$path"; done
  fi
}
trap rollback EXIT
mkdir -p ml research/cases scripts tests
for path in "${files[@]}"; do cp "$RELEASE/$path" "$path"; done
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text()
anchor='tests/test_case_reliability_v28.py'
new='tests/test_case_workflow_v29.py'
assert s.count(anchor)==1 and new not in s, 'Unexpected v0.28 CI test anchor'
p.write_text(s.replace(anchor,anchor+' '+new))
print('PASS: Added v0.29 synthetic-only integration tests to CI')
PY
printf '=== Full repository Python synthetic/privacy tests; no research fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-only integrated workflow plan ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_workflow_v29 --plan
printf '=== Whitespace validation ===\n'
git diff --check
trap - EXIT
printf '\nSUCCESS: v0.29 source installed; no research data or models accessed.\n'
printf 'Private metadata audit: PYTHONPATH=. .venv/bin/python -m ml.case_workflow_v29 --audit\n'
printf 'Original CI backup: %s\n' "$backup"
