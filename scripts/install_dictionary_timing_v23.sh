#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == "main" ]] || { echo 'ERROR: Expected branch main'; exit 1; }
[[ -f ml/case_governance_v22.py && -f research/cases/nhanes_governance_v22.json ]] || {
  echo 'ERROR: v0.22 prerequisite is absent'; exit 1;
}
[[ -f .venv/bin/python ]] || { echo 'ERROR: Missing workstation Python environment'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Tracked repository changes detected; review before installation'; exit 1
fi
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local main and origin/main differ; resolve before installation'; exit 1
}
git merge-base --is-ancestor c22bf0c HEAD || {
  echo 'ERROR: v0.22 published history not present'; exit 1;
}
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
  ml/case_dictionary_timing_v23.py
  research/FEATURE_AVAILABILITY_V23.md
  research/cases/nhanes_dictionary_timing_v23.json
  research/cases/FEATURE_DICTIONARY_TEMPLATE_V23.json
  scripts/install_dictionary_timing_v23.sh
  scripts/publish_dictionary_timing_v23.sh
  tests/test_case_dictionary_timing_v23.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" && ! -e "$file" ]] || {
     echo "ERROR: Existing path or missing archive source: $file"; exit 1;
  }
done
backup="$(mktemp -d /tmp/frailtyscope-v23-original-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: v0.23 installer failed; restoring existing CI. Backup: $backup"
    cp "$backup/ci.yml" .github/workflows/ci.yml || true
    for file in "${files[@]}"; do rm -f -- "$file"; done
  fi
}
trap rollback EXIT
mkdir -p ml research/cases scripts tests
for file in "${files[@]}"; do cp "$RELEASE/$file" "$file"; done
python3 - <<'PY'
from pathlib import Path
path=Path('.github/workflows/ci.yml')
s=path.read_text()
needle='tests/test_case_governance_v22.py'
assert s.count(needle)==1, 'Expected exactly one v0.22 CI test anchor'
assert 'tests/test_case_dictionary_timing_v23.py' not in s, 'v0.23 tests already configured'
path.write_text(s.replace(needle,needle+' tests/test_case_dictionary_timing_v23.py'))
print('PASS: Added source-only v0.23 tests to CI')
PY
printf '=== Full Python fixture tests; never train real model ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Dictionary-timing preflight; source-only ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_dictionary_timing_v23 --plan
printf '=== Source whitespace check ===\n'
git diff --check
trap - EXIT
printf '\nSUCCESS: v0.23 installed. No models fitted; no data touched.\n'
printf 'Optional private metadata audit: PYTHONPATH=. .venv/bin/python -m ml.case_dictionary_timing_v23 --audit\n'
printf 'Backup of previous CI file: %s\n' "$backup"
