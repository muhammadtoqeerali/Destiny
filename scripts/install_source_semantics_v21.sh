#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected Git main'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Existing tracked changes; review before installation'; exit 1
fi
[[ -f ml/case_readiness_v19.py && -f ml/case_joint_selection_v16.py ]] || {
  echo 'ERROR: Prior v0.19/v0.16 source required'; exit 1;
}
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local source differs from GitHub main'; exit 1;
}
[[ "$(git rev-parse HEAD)" == eabef62* ]] || {
  echo 'NOTE: Current main is not the expected v0.19 tip; checking ancestry'
  git merge-base --is-ancestor eabef62 HEAD || { echo 'ERROR: Missing v0.19 lineage'; exit 1; }
}
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
 ml/case_source_semantics_v21.py
 research/SOURCE_SEMANTICS_V21.md
 research/cases/nhanes_source_semantics_v21.json
 research/cases/SOURCE_SEMANTICS_TEMPLATE_V21.json
 scripts/install_source_semantics_v21.sh
 scripts/publish_source_semantics_v21.sh
 tests/test_case_source_semantics_v21.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" && ! -e "$file" ]] || { echo "ERROR: Missing release source or existing path: $file"; exit 1; }
done
backup="$(mktemp -d /tmp/frailtyscope-v21-source-backup-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
cleanup() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: Installation interrupted; restoring CI and removing only v0.21 files. Backup: $backup"
    cp "$backup/ci.yml" .github/workflows/ci.yml || true
    for file in "${files[@]}"; do rm -f -- "$file"; done
  fi
}
trap cleanup EXIT
mkdir -p ml research/cases scripts tests
for file in "${files[@]}"; do cat "$RELEASE/$file" > "$file"; done
# Permission-safe: no install(1) and no chmod(1), run scripts through bash.
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text()
anchor='tests/test_case_readiness_v19.py'
assert s.count(anchor)==1 and 'tests/test_case_source_semantics_v21.py' not in s, 'Unexpected CI schema'
p.write_text(s.replace(anchor,anchor+' tests/test_case_source_semantics_v21.py'))
print('PASS: Added v0.21 pure tests to CI')
PY
printf '=== Full source and privacy tests; NO NHANES model fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-aware semantic design preflight; NO fitting ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_source_semantics_v21 --plan
printf '=== Source integrity check ===\n'
git diff --check
trap - EXIT
printf '\nREADY FOR V0.21 WORKSTATION SEMANTIC ENCODING COMPARISON. NO MODEL FITTED.\n'
printf 'To run: PYTHONPATH=. .venv/bin/python -m ml.case_source_semantics_v21 --run\n'
printf 'Temporary original CI backup: %s\n' "$backup"
