#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Checkout main first'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Tracked source changes already present; review before installing'; exit 1
fi
[[ -f ml/case_reliability_v18.py ]] || { echo 'ERROR: v0.18 source not present'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local and origin/main differ; review before continuing'; exit 1;
}
git merge-base --is-ancestor bdf991d HEAD || { echo 'ERROR: Expected reviewed v0.18 lineage'; exit 1; }
cd "$RELEASE"
sha256sum --check SHA256SUMS
cd "$ROOT"
files=(
  ml/case_readiness_v19.py
  research/DATA_READINESS_GATE_V19.md
  research/cases/READINESS_TEMPLATE_V19.json
  research/cases/nhanes_readiness_v19.json
  scripts/install_readiness_v19.sh
  scripts/publish_readiness_v19.sh
  tests/test_case_readiness_v19.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" ]] || { echo "ERROR: Release file missing $file"; exit 1; }
  [[ ! -e "$file" ]] || { echo "ERROR: $file exists; refusing overwrite"; exit 1; }
done
[[ -f .github/workflows/ci.yml ]] || { echo 'ERROR: Missing CI config'; exit 1; }
backup="$(mktemp -d /tmp/frailtyscope-v19-source-backup-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  local rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: v0.19 installation interrupted. Restoring CI and removing only v0.19 files. Backup $backup"
    cp "$backup/ci.yml" .github/workflows/ci.yml
    for file in "${files[@]}"; do rm -f -- "$file"; done
  fi
}
trap rollback EXIT
# Copy CONTENTS only. `install -m` and `chmod` call fchmod/chmod, which fails
# on some workstation mounts (e.g. NTFS/FUSE permission-mapping). Shell scripts
# are invoked with `bash` and therefore do not require executable mode bits.
# Use redirection into newly created, checked paths; no permission mutation.
mkdir -p ml research/cases scripts tests
for file in "${files[@]}"; do
  [[ ! -e "$file" && ! -L "$file" ]] || {
    echo "ERROR: Destination appeared during installation: $file"; exit 1;
  }
  cat -- "$RELEASE/$file" > "$file"
done
python3 - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml');s=p.read_text()
anchor='tests/test_case_reliability_v18.py'
assert s.count(anchor)==1 and 'tests/test_case_readiness_v19.py' not in s, 'Unexpected CI source'
p.write_text(s.replace(anchor, anchor+' tests/test_case_readiness_v19.py'))
print('PASS: CI includes v0.19 no-fitting intake contracts')
PY
printf '=== Test all source contracts; NO model fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Read-only NHANES development intake preflight; no holdout outcomes ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_readiness_v19 --plan
printf '=== Source integrity ===\n'
git diff --check
trap - EXIT
printf '\nREADY FOR V0.19 PRIVATE READINESS AUDIT. No model trained or published.\n'
printf 'To save the private development-only audit: PYTHONPATH=. .venv/bin/python -m ml.case_readiness_v19 --audit\n'
printf 'Temporary original-CI backup: %s\n' "$backup"
