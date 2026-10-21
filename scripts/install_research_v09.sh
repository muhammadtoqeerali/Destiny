#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ -x .venv/bin/python ]] || { echo 'ERROR: Missing workstation virtualenv';exit 1; }
[[ "$(git branch --show-current)" == 'main' ]] || { echo 'ERROR: Expected main branch';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected repository';exit 1; }
[[ -f data/processed/nhanes_5yr_local.csv && -f artifacts/realdata_nhanes/quality_v08.json ]] || { echo 'ERROR: Corrected local NHANES data not available';exit 1; }
[[ -f ml/realdata_nhanes.py && -f ml/nhanes_survival.py && -f tests/test_phq_xport_zero.py ]] || { echo 'ERROR: Expected FrailtyScope v0.8.1 on workstation';exit 1; }
.venv/bin/python - <<'PY'
import json
import pandas as pd
from pathlib import Path
q=json.loads(Path('artifacts/realdata_nhanes/quality_v08.json').read_text())
assert q['phq9_flag']=='COVERAGE_OK' and q['phq9_complete_percent']>80,'PHQ correction is not validated'
d=pd.read_csv('data/processed/nhanes_5yr_local.csv',usecols=['data_origin','cycle','phq9_score'])
assert len(d)==2422 and set(d.data_origin)=={'NHANES_PUBLIC_2019_LMF'}
assert round(100*d.phq9_score.notna().mean(),2)==q['phq9_complete_percent']
print('PASS: 2,422 real NHANES records; corrected PHQ-9 coverage',q['phq9_complete_percent'])
PY
if ! git diff --cached --quiet;then echo 'ERROR: Review existing staged files first';exit 1;fi
FILES=(ml/nhanes_survival_v09.py ml/nhats_longitudinal_v09.py tests/test_survival_v09.py tests/test_nhats_v09.py research/NHATS_MAPPING_V09.json research/NHATS_ACCESS_AND_VALIDATION.md scripts/install_research_v09.sh scripts/publish_research_v09.sh .github/workflows/ci.yml)
for file in "${FILES[@]}";do
  [[ -f "$SOURCE/$file" ]] || { echo "ERROR: Release missing $file";exit 1; }
  if git ls-files --error-unmatch "$file" >/dev/null 2>&1;then
    if ! git diff --quiet -- "$file";then echo "ERROR: Uncommitted change: $file";exit 1;fi
  elif [[ -e "$file" ]];then echo "ERROR: Existing untracked file would be overwritten: $file";exit 1;fi
done
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Local main is not at remote main; no changes made';exit 1; }
BACKUP="$(mktemp -d /tmp/frailtyscope-v09-code-backup-XXXXXX)"
for file in "${FILES[@]}";do
  mkdir -p "$(dirname "$file")" "$BACKUP/$(dirname "$file")"
  if [[ -f "$file" ]];then cat "$file" > "$BACKUP/$file";fi
  cat "$SOURCE/$file" > "$file"
done
printf 'Source backups (temporary): %s\n' "$BACKUP"

echo '=== Test current research and release safety ==='
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py \
  tests/test_v08.py tests/test_phq_xport_zero.py tests/test_survival_v09.py tests/test_nhats_v09.py

echo '=== Run exploratory Cox time-to-event benchmark on cached REAL NHANES ==='
PYTHONPATH=. .venv/bin/python -m ml.nhanes_survival_v09 \
  --raw-dir data/raw/nhanes \
  --output artifacts/realdata_nhanes/cox_v09_local.json

echo '=== Inspect only local aggregate research report ==='
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('artifacts/realdata_nhanes/cox_v09_local.json')
d=json.loads(p.read_text())
assert d['report_type']=='LOCAL_SURVIVAL_RESEARCH_ONLY'
assert d['counts']['development']>=1165 and d['counts']['later_cycle']>=1257
assert 0<=d['later_cycle']['harrell_c']<=1 and 0<=d['later_cycle']['ipcw_brier_60m']<=1
assert not ({'SEQN','records','patients','individual_risk','raw_predictions'} & d.keys())
print('Later-cycle model metrics (exploratory):',json.dumps(d['later_cycle'],indent=2))
public=Path('web/public/data')
assert sorted(p.name for p in public.iterdir() if p.is_file())==[
  'nhanes-aggregate.json','nhanes-cohort-profile.json','nhanes-refinement.json']
print('PASS: Public dashboard data unchanged. NHATS has not been downloaded or modeled.')
PY

printf '\nREADY FOR REVIEW. v0.9 research code installed locally. No GitHub push, no new public predictions.\n'
printf 'Only after review, publish SOURCE CODE ONLY with bash scripts/publish_research_v09.sh\n'
