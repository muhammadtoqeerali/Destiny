#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_task_models_v26.py && -f research/cases/nhanes_task_models_v26.json ]] || {
 echo 'ERROR: Published v0.26 base not installed'; exit 1; }
[[ -f .venv/bin/python ]] || { echo 'ERROR: Workstation Python .venv missing'; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
 echo 'ERROR: Modified tracked source detected; inspect before installation'; exit 1
fi
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
 echo 'ERROR: Local main and origin/main differ; do not install'; exit 1; }
git merge-base --is-ancestor 924e9ba HEAD || { echo 'ERROR: Published v0.26 ancestry missing'; exit 1; }
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
 ml/case_temporal_v27.py
 research/TEMPORAL_SURVIVAL_LONGITUDINAL_V27.md
 research/cases/nhanes_temporal_v27.json
 research/cases/TEMPORAL_TEMPLATE_V27.json
 scripts/install_temporal_v27.sh
 scripts/publish_temporal_v27.sh
 tests/test_case_temporal_v27.py
)
for path in "${files[@]}"; do
 [[ -f "$RELEASE/$path" && ! -e "$path" ]] || {
   echo "ERROR: Missing release file or destination already exists: $path"; exit 1; }
done
backup="$(mktemp -d /tmp/frailtyscope-v27-ci-original-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: v0.27 installation interrupted. Restoring CI; backup: $backup"
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
anchor='tests/test_case_task_models_v26.py'
addition='tests/test_case_temporal_v27.py'
assert s.count(anchor)==1 and addition not in s, 'Unexpected v0.26 CI test anchor'
p.write_text(s.replace(anchor,anchor+' '+addition))
print('PASS: Added synthetic v0.27 tests to CI')
PY
printf '=== Full repository Python fixture/privacy tests; no real fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-only v0.27 plan; no participant datasets ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_temporal_v27 --plan
printf '=== Source whitespace validation ===\n'
git diff --check
trap - EXIT
printf '\nSUCCESS: v0.27 installed. No research data or fitted models accessed.\n'
printf 'Optional PRIVATE metadata audit: PYTHONPATH=. .venv/bin/python -m ml.case_temporal_v27 --audit\n'
printf 'Temporary backup of original CI: %s\n' "$backup"
