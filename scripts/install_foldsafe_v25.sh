#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected branch main'; exit 1; }
[[ -f .venv/bin/python && -f ml/case_harmonization_v24.py ]] || { echo 'ERROR: Python or v0.24 prerequisite missing'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Local tracked changes exist; review before installing'; exit 1
fi
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local branch diverges from origin/main'; exit 1;
}
git merge-base --is-ancestor 9ec89d6 HEAD || {
  echo 'ERROR: Expected published v0.24 lineage missing'; exit 1;
}
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
  ml/case_foldsafe_v25.py
  research/FOLDSAFE_PREPROCESSING_V25.md
  research/cases/nhanes_foldsafe_v25.json
  research/cases/FOLDSAFE_TEMPLATE_V25.json
  scripts/install_foldsafe_v25.sh
  scripts/publish_foldsafe_v25.sh
  tests/test_case_foldsafe_v25.py
)
for item in "${files[@]}"; do
  [[ -f "$RELEASE/$item" && ! -e "$item" ]] || { echo "ERROR: Existing or absent source: $item"; exit 1; }
done
backup="$(mktemp -d /tmp/frailtyscope-v25-original-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: Failed install; restoring CI and removing only v0.25 files. Backup: $backup"
    cp "$backup/ci.yml" .github/workflows/ci.yml || true
    for item in "${files[@]}"; do rm -f -- "$item"; done
  fi
}
trap rollback EXIT
mkdir -p ml research/cases scripts tests
for item in "${files[@]}"; do cp "$RELEASE/$item" "$item"; done
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text()
old='tests/test_case_harmonization_v24.py'
new='tests/test_case_foldsafe_v25.py'
assert s.count(old)==1 and new not in s, 'Expected v0.24 CI anchor exactly once'
p.write_text(s.replace(old,old+' '+new))
print('PASS: Added v0.25 synthetic-only tests to CI')
PY
printf '=== All repository fixture/privacy tests; NO real model fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-only v0.25 plan; NO participant datasets ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_foldsafe_v25 --plan
printf '=== Source whitespace ===\n'
git diff --check
trap - EXIT
printf '\nSUCCESS: v0.25 installed. No real data or saved models touched.\n'
printf 'Optional PRIVATE metadata audit: PYTHONPATH=. .venv/bin/python -m ml.case_foldsafe_v25 --audit\n'
printf 'Temporary original CI backup: %s\n' "$backup"
