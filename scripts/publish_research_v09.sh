#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected Git origin';exit 1; }
[[ -f artifacts/realdata_nhanes/cox_v09_local.json ]] || { echo 'ERROR: Run the workstation benchmark first';exit 1; }
.venv/bin/python - <<'PY'
import json
from pathlib import Path
report=json.loads(Path('artifacts/realdata_nhanes/cox_v09_local.json').read_text())
assert report['report_type']=='LOCAL_SURVIVAL_RESEARCH_ONLY'
assert 0<=report['later_cycle']['harrell_c']<=1
assert 0<=report['later_cycle']['ipcw_brier_60m']<=1
public=Path('web/public/data')
assert {p.name for p in public.iterdir() if p.is_file()}=={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json'}
print('PASS: Local exploratory survival analysis exists; public research assets unchanged')
PY
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py \
  tests/test_v08.py tests/test_phq_xport_zero.py tests/test_survival_v09.py tests/test_nhats_v09.py

FILES=(ml/nhanes_survival_v09.py ml/nhats_longitudinal_v09.py tests/test_survival_v09.py tests/test_nhats_v09.py research/NHATS_MAPPING_V09.json research/NHATS_ACCESS_AND_VALIDATION.md scripts/install_research_v09.sh scripts/publish_research_v09.sh .github/workflows/ci.yml)
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Review existing staged changes first';exit 1; }
git add -- "${FILES[@]}"
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for staged in "${STAGED[@]}";do
  approved=0
  for file in "${FILES[@]}";do [[ "$staged" == "$file" ]] && { approved=1;break; };done
  (( approved )) || { printf 'ERROR: Unapproved staged file: %s\n' "$staged";exit 1; }
done
[[ ${#STAGED[@]} -gt 0 ]] || { echo 'No source changes to publish';exit 0; }
git diff --cached --check
git diff --cached --stat
printf '\nNOTE: Only source, tests, and documentation are staged. No survival results or NHATS participant data.\n'
read -r -p 'Publish reviewed source-only release to GitHub main? Type YES: ' CONFIRM
[[ "$CONFIRM" == YES ]] || { echo 'Cancelled; staged code remains for review';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote branch moved; do not force push';exit 1; }
git commit -m 'feat: add private NHANES survival benchmark and registered NHATS wave validator'
git push origin main
printf 'SUCCESS: Source-only release pushed. No registered data was published.\n'
