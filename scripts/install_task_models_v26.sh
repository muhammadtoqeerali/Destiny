#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_foldsafe_v25.py && -f research/cases/nhanes_foldsafe_v25.json ]] || {
  echo 'ERROR: Published v0.25 prerequisite unavailable'; exit 1;
}
[[ -f .venv/bin/python ]] || { echo 'ERROR: Missing workstation Python environment'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Uncommitted tracked source; review before installation'; exit 1
fi
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local and remote main differ'; exit 1;
}
git merge-base --is-ancestor fe3b0a1 HEAD || {
  echo 'ERROR: Published v0.25 base commit absent'; exit 1;
}
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
  ml/case_task_models_v26.py
  research/TASK_MODEL_VALIDATION_V26.md
  research/cases/nhanes_task_models_v26.json
  research/cases/TASK_MODEL_TEMPLATE_V26.json
  scripts/install_task_models_v26.sh
  scripts/publish_task_models_v26.sh
  tests/test_case_task_models_v26.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" && ! -e "$file" ]] || {
    echo "ERROR: Missing release source or existing destination $file"; exit 1;
  }
done
backup="$(mktemp -d /tmp/frailtyscope-v26-source-backup-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: v0.26 installation interrupted. Restoring CI and new files. Backup: $backup"
    cp "$backup/ci.yml" .github/workflows/ci.yml || true
    for file in "${files[@]}"; do rm -f -- "$file"; done
  fi
}
trap rollback EXIT
mkdir -p ml research/cases scripts tests
for file in "${files[@]}"; do cp "$RELEASE/$file" "$file"; done
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text()
old='tests/test_case_foldsafe_v25.py'
new='tests/test_case_task_models_v26.py'
assert s.count(old)==1 and new not in s, 'Expected exactly one v0.25 GitHub CI anchor'
p.write_text(s.replace(old, old+' '+new))
print('PASS: Added synthetic v0.26 tests to CI')
PY
printf '=== Complete Python fixture/privacy tests; NO research fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== v0.26 source-only plan; NO real model execution ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_task_models_v26 --plan
printf '=== Source whitespace check ===\n'
git diff --check
trap - EXIT
printf '\nSUCCESS: v0.26 installed. No research data or model artifacts modified.\n'
printf 'Optional immutable private documentary audit:\n'
printf '  PYTHONPATH=. .venv/bin/python -m ml.case_task_models_v26 --audit\n'
printf 'Temporary CI backup: %s\n' "$backup"
