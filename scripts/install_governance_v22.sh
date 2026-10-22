#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected Git main branch'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Existing tracked modifications: resolve/review before source install'; exit 1
fi
[[ -f ml/case_source_semantics_v21.py && -f ml/case_readiness_v19.py ]] || {
  echo 'ERROR: v0.21/v0.19 source missing'; exit 1;
}
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local main differs from remote main; review divergence'; exit 1;
}
git merge-base --is-ancestor f070a46 HEAD || { echo 'ERROR: v0.21 source lineage missing'; exit 1; }
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
 ml/case_governance_v22.py
 research/RESEARCH_METHODS_ATLAS_V22.md
 research/cases/nhanes_governance_v22.json
 research/cases/RESEARCH_GOVERNANCE_TEMPLATE_V22.json
 scripts/install_governance_v22.sh
 scripts/publish_governance_v22.sh
 tests/test_case_governance_v22.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" && ! -e "$file" ]] || { echo "ERROR: Release source missing or path exists: $file"; exit 1; }
done
backup="$(mktemp -d /tmp/frailtyscope-v22-source-backup-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: v0.22 install interrupted. Restoring CI and removing only v0.22 files. Backup: $backup"
    cp "$backup/ci.yml" .github/workflows/ci.yml || true
    for file in "${files[@]}"; do rm -f -- "$file"; done
  fi
}
trap rollback EXIT
mkdir -p ml research/cases scripts tests
# Permission safe on backup-mounted filesystems; no install(1), chmod(1), sudo.
for file in "${files[@]}"; do cat "$RELEASE/$file" > "$file"; done
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text()
anchor='tests/test_case_source_semantics_v21.py'
assert s.count(anchor)==1 and 'tests/test_case_governance_v22.py' not in s, 'Unexpected GitHub CI test list'
p.write_text(s.replace(anchor,anchor+' tests/test_case_governance_v22.py'))
print('PASS: Added v0.22 fixture-only governance contracts to CI')
PY
printf '=== Full test suite (pure fixture tests only); NO research fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-only v0.22 preflight; NO private artifacts opened ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_governance_v22 --plan
printf '=== Check source whitespace ===\n'
git diff --check
trap - EXIT
printf '\nREADY FOR V0.22 PRIVATE EVIDENCE LEDGER REVIEW. NO RESEARCH DATA OR MODEL TOUCHED.\n'
printf 'To inspect aggregate local audit metadata and save a PRIVATE ledger:\n'
printf '  PYTHONPATH=. .venv/bin/python -m ml.case_governance_v22 --audit\n'
printf 'Temporary CI backup: %s\n' "$backup"
