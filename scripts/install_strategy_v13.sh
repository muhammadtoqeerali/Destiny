#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ -x .venv/bin/python ]] || { echo 'ERROR: .venv/bin/python missing'; exit 1; }
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
origin="$(git remote get-url origin)"
[[ "$origin" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$origin" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected origin'; exit 1; }
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Staged changes require review';exit 1; }
[[ -z "$(git diff --name-only)" ]] || { echo 'ERROR: Uncommitted tracked edits require review';exit 1; }
[[ -f ml/case_engine_v10.py && -f ml/case_model_io_v11.py && -f research/cases/nhanes_mortality_v10.json ]] || { echo 'ERROR: v0.12 core prerequisites missing'; exit 1; }

FILES=(
 ml/case_strategy_v13.py
 research/cases/nhanes_strategy_v13.json
 research/cases/ADAPTIVE_STRATEGY_TEMPLATE_V13.json
 research/ADAPTIVE_MODEL_SELECTION_V13.md
 scripts/install_strategy_v13.sh
 scripts/publish_strategy_v13.sh
 tests/test_case_strategy_v13.py
)
for f in "${FILES[@]}"; do
 [[ -f "$RELEASE/$f" ]] || { echo "ERROR: Missing bundled $f";exit 1; }
 [[ ! -e "$f" ]] || { echo "ERROR: Existing path requires manual review $f";exit 1; }
done
[[ -f .github/workflows/ci.yml ]] || { echo 'ERROR: Missing CI workflow';exit 1; }

echo '=== Verify reviewed GitHub release v0.12 ==='
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: main differs from upstream; no changes made'; exit 1; }
BACKUP="$(mktemp -d /tmp/frailtyscope-v13-source-backup-XXXXXX)"
mkdir -p "$BACKUP/.github/workflows"
cat .github/workflows/ci.yml > "$BACKUP/.github/workflows/ci.yml"
printf 'CI source backup: %s\n' "$BACKUP"
for f in "${FILES[@]}"; do mkdir -p "$(dirname "$f")"; cat "$RELEASE/$f" > "$f"; done
PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
p=Path('.github/workflows/ci.yml')
s=p.read_text()
old='tests/test_decision_quality_v12.py'
new=old+' tests/test_case_strategy_v13.py'
if new in s:raise SystemExit('ERROR: CI already modified; review before rerun')
if s.count(old)!=1:raise SystemExit('ERROR: CI patch anchor mismatch')
p.write_text(s.replace(old,new))
print('PASS: CI includes development-only protocol regression tests')
PY

echo '=== Validate v0.13 structure; NO model fitting here or in tests ==='
PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m compileall -q ml/case_strategy_v13.py
bash -n scripts/install_strategy_v13.sh scripts/publish_strategy_v13.sh

echo '=== Real NHANES PLAN ONLY, no fitting, no holdout metrics ==='
PYTHONPATH=. .venv/bin/python -m ml.case_strategy_v13 --plan

echo
printf 'READY FOR SEARCH REVIEW. Source installed locally; no model training, no GitHub push.\n'
printf 'To START staged/nested model training on THIS workstation:\n'
printf '  PYTHONPATH=. .venv/bin/python -m ml.case_strategy_v13 --search 2>&1 | tee ~/frailtyscope-v13-search.log\n'
printf 'The search fits development-fold candidates and saves only local artifacts. It does not evaluate the later-cycle cohort.\n'
