#!/usr/bin/env bash
set -euo pipefail
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Use main branch'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Review tracked or staged changes before installation'; exit 1; }
[[ -f research/cases/nhanes_ablation_v14.json ]] || { echo 'ERROR: v0.14 must be installed'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Current branch differs from origin/main'; exit 1; }
git merge-base --is-ancestor d17da1a3da4a21f60fe8d45ee8a7c4867609c1c7 HEAD || { echo 'ERROR: v0.14 commit is required'; exit 1; }
files=(
  ml/case_preprocess_selection_v15.py
  research/cases/nhanes_preprocess_selection_v15.json
  research/cases/PREPROCESS_SELECTION_TEMPLATE_V15.json
  research/NESTED_PREPROCESS_SELECTION_V15.md
  scripts/install_preprocess_v15.sh
  scripts/publish_preprocess_v15.sh
  tests/test_preprocess_selection_v15.py
)
for path in "${files[@]}"; do
  [[ ! -e "$path" ]] || { echo "ERROR: Refuse to overwrite existing $path"; exit 1; }
  [[ -f "$RELEASE/$path" ]] || { echo "ERROR: Missing release input $path"; exit 1; }
done
[[ -f .github/workflows/ci.yml ]] || { echo 'ERROR: Missing CI workflow'; exit 1; }
PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
s=Path('.github/workflows/ci.yml').read_text()
anchor='tests/test_case_ablation_v14.py'
assert s.count(anchor)==1, 'Unexpected v0.14 CI workflow state'
assert 'tests/test_preprocess_selection_v15.py' not in s
print('PASS: CI patch anchor verified')
PY
for path in "${files[@]}"; do
  mkdir -p "$(dirname "$path")"
  cat "$RELEASE/$path" > "$path"
done
chmod +x scripts/install_preprocess_v15.sh scripts/publish_preprocess_v15.sh
PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text()
anchor='tests/test_case_ablation_v14.py'
assert s.count(anchor)==1 and 'tests/test_preprocess_selection_v15.py' not in s
p.write_text(s.replace(anchor,anchor+' tests/test_preprocess_selection_v15.py'))
print('PASS: CI includes v0.15 structural tests')
PY
printf '=== Structural regression tests; NO NHANES model fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Real local dataset/selection PRE-FLIGHT ONLY (NO FITTING) ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_preprocess_selection_v15 --plan
git diff --check
printf '\nREADY FOR V0.15 DEVELOPMENT STUDY. No models trained or GitHub push.\n'
printf 'Separate workstation-only fitting command:\n  PYTHONPATH=. .venv/bin/python -m ml.case_preprocess_selection_v15 --run\n'
