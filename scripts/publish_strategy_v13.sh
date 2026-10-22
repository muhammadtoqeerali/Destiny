#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main';exit 1; }
origin="$(git remote get-url origin)"
[[ "$origin" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$origin" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected remote'; exit 1; }
FILES=(ml/case_strategy_v13.py research/cases/nhanes_strategy_v13.json research/cases/ADAPTIVE_STRATEGY_TEMPLATE_V13.json research/ADAPTIVE_MODEL_SELECTION_V13.md scripts/install_strategy_v13.sh scripts/publish_strategy_v13.sh tests/test_case_strategy_v13.py .github/workflows/ci.yml)
allowed(){ local f; for f in "${FILES[@]}";do [[ "$1" == "$f" ]] && return 0;done;return 1; }
for f in "${FILES[@]}";do [[ -f "$f" ]] || { echo "ERROR: Missing $f";exit 1; };done
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for f in "${STAGED[@]}";do allowed "$f" || { echo "ERROR: Unapproved staged file $f";exit 1; };done
[[ -f artifacts/cases/nhanes_mortality_v10/strategy_v13/selection.json ]] || { echo 'ERROR: Run development-only nested search first';exit 1; }
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('artifacts/cases/nhanes_mortality_v10/strategy_v13/selection.json')
r=json.loads(p.read_text())
assert r['schema']=='FRAILTYSCOPE_CASE_STRATEGY_V13'
assert r['holdout_used_in_selection'] is False
assert len(r['outer_nested_results'])==3
assert (p.parent/'winner_development_only.joblib').is_file()
print('PASS: Local nested selection completed; no evaluation selection leakage')
PY
PYTHONPATH=. .venv/bin/python -m pytest -q tests
git add -- "${FILES[@]}"
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for f in "${STAGED[@]}";do allowed "$f" || { echo "ERROR: Unapproved staged path $f";exit 1; };done
[[ ${#STAGED[@]} -gt 0 ]] || { echo 'Nothing new to publish'; exit 0; }
git diff --cached --check
git diff --cached --stat
printf '\nSource-only publication. No data/, artifacts/, scores, models or public dashboard changes.\n'
read -r -p 'Publish v0.13 source-only strategy? Type uppercase YES: ' confirm
[[ "$confirm" == YES ]] || { echo 'Publication declined';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Branch diverged';exit 1; }
git commit -m 'feat: development-only nested model selection and data-design safeguards'
git push origin main
printf 'SUCCESS: v0.13 source-only strategy pushed, no data or model artifacts.\n'
