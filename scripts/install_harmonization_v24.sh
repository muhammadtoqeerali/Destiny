#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ -f ml/case_dictionary_timing_v23.py && -f .venv/bin/python ]] || {
  echo 'ERROR: v0.23 and local Python environment required'; exit 1;
}
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo 'ERROR: Tracked source changes exist; review before installation'; exit 1
fi
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || {
  echo 'ERROR: Local and remote main differ'; exit 1;
}
git merge-base --is-ancestor a21df04 HEAD || {
  echo 'ERROR: Published v0.23 history required'; exit 1;
}
(cd "$RELEASE" && sha256sum --check SHA256SUMS)
files=(
  ml/case_harmonization_v24.py
  research/HARMONIZATION_CONTRACT_V24.md
  research/cases/nhanes_harmonization_v24.json
  research/cases/HARMONIZATION_TEMPLATE_V24.json
  scripts/install_harmonization_v24.sh
  scripts/publish_harmonization_v24.sh
  tests/test_case_harmonization_v24.py
)
for file in "${files[@]}"; do
  [[ -f "$RELEASE/$file" && ! -e "$file" ]] || {
    echo "ERROR: Unexpected existing target or absent source: $file"; exit 1;
  }
done
backup="$(mktemp -d /tmp/frailtyscope-v24-original-XXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
rollback() {
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: Installation failed; restoring CI and removing only v0.24 files. Backup: $backup"
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
old='tests/test_case_dictionary_timing_v23.py'
new='tests/test_case_harmonization_v24.py'
assert s.count(old)==1 and new not in s, 'Expected exactly one v0.23 CI anchor'
p.write_text(s.replace(old, old+' '+new))
print('PASS: Installed v0.24 synthetic checks into CI')
PY
printf '=== Full Python source/privacy tests; no research fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Metadata harmonization preflight ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_harmonization_v24 --plan
printf '=== Source whitespace ===\n'
git diff --check
trap - EXIT
printf '\nSUCCESS: v0.24 SOURCE blueprint installed; no participant files or models touched.\n'
printf 'Optional immutable private metadata audit: PYTHONPATH=. .venv/bin/python -m ml.case_harmonization_v24 --audit\n'
printf 'Temporary CI backup: %s\n' "$backup"
