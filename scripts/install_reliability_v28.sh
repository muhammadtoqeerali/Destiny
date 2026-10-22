#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_temporal_v27.py && -f research/cases/nhanes_temporal_v27.json ]] || {
  echo 'ERROR: Published v0.27 source prerequisite absent'; exit 1;
}
[[ -f .venv/bin/python ]] || { echo 'ERROR: Workstation Python .venv unavailable'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Tracked edits/staged files exist; inspect before installing'; exit 1
fi
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local main differs from remote main'; exit 1;
}
git merge-base --is-ancestor 9471eae HEAD || {
  echo 'ERROR: Published v0.27 ancestry not found'; exit 1;
}
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
  ml/case_reliability_v28.py
  research/RELIABILITY_UNCERTAINTY_V28.md
  research/cases/nhanes_reliability_v28.json
  research/cases/RELIABILITY_TEMPLATE_V28.json
  scripts/install_reliability_v28.sh
  scripts/publish_reliability_v28.sh
  tests/test_case_reliability_v28.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" && ! -e "$file" ]] || {
    echo "ERROR: Release source missing or target path already exists: $file"; exit 1;
  }
done
backup="$(mktemp -d /tmp/frailtyscope-v28-ci-original-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: v0.28 installation failed, restoring CI and new sources; backup $backup"
    cp "$backup/ci.yml" .github/workflows/ci.yml || true
    for file in "${files[@]}"; do rm -f -- "$file"; done
  fi
}
trap rollback EXIT
mkdir -p ml research/cases scripts tests
for file in "${files[@]}"; do cat "$RELEASE/$file" > "$file"; done
python3 - <<'PY'
from pathlib import Path
ci=Path('.github/workflows/ci.yml')
s=ci.read_text()
needle='tests/test_case_temporal_v27.py'
new='tests/test_case_reliability_v28.py'
assert s.count(needle)==1 and new not in s, 'Unexpected v0.27 CI test-list anchor'
ci.write_text(s.replace(needle, needle+' '+new))
print('PASS: Registered v0.28 synthetic reliability tests in CI')
PY
printf '=== Full repository fixture/privacy tests; NO NHANES/HUNT analysis ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-only reliability readiness plan ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_reliability_v28 --plan
printf '=== Whitespace validation ===\n'
git diff --check
trap - EXIT
printf '\nSUCCESS: v0.28 source installed. No participant data or fitted research model opened.\n'
printf 'Private metadata-only audit (optional): PYTHONPATH=. .venv/bin/python -m ml.case_reliability_v28 --audit\n'
printf 'Original CI backup: %s\n' "$backup"
