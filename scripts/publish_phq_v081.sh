#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Require Git main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected origin';exit 1; }
[[ -x .venv/bin/python ]] || { echo 'ERROR: Python environment missing';exit 1; }
[[ -f artifacts/realdata_nhanes/quality_v08.json ]] || { echo 'ERROR: Corrected PHQ-9 audit missing';exit 1; }

printf '=== Ensure real-data results were rebuilt and approved export matches local research ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
import pandas as pd, json
from scripts.export_nhanes_aggregate import export
from scripts.export_nhanes_refinement import report_to_public
from ml.nhanes_cohort_profile import build_profile
q=json.loads(Path('artifacts/realdata_nhanes/quality_v08.json').read_text())
assert q['phq9_flag']=='COVERAGE_OK' and q['phq9_complete_percent']>50,'Incomplete PHQ correction'
assert all(v['mismatch_count']==0 and v['xport_zero_alias_values_corrected']>0 for v in q['phq9_by_cycle'].values())
d=pd.read_csv('data/processed/nhanes_5yr_local.csv')
assert len(d)==2422 and set(d.data_origin)=={'NHANES_PUBLIC_2019_LMF'}
assert round(100*d.phq9_score.notna().mean(),2)==q['phq9_complete_percent']
p=Path('web/public/data')
expected={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json'}
assert {f.name for f in p.iterdir() if f.is_file()}==expected,'Unexpected public files'
exports={f.name:json.loads(f.read_text()) for f in p.iterdir() if f.is_file()}
assert exports['nhanes-aggregate.json']==export(json.loads(Path('artifacts/realdata_nhanes/report.json').read_text()))
assert exports['nhanes-refinement.json']==report_to_public(json.loads(Path('artifacts/realdata_nhanes/refinement.json').read_text()))
assert exports['nhanes-cohort-profile.json']==build_profile(d,q)
for data in exports.values():
    assert data['provenance']=='REAL_NHANES_AGGREGATE_ONLY'
    assert not any(k in data for k in ('SEQN','patients','cases','records','individual_predictions'))
print('PASS: Corrected PHQ-9 data, metrics and three disclosure-screened exports')
PY

printf '=== Python research and safety tests ===\n'
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py tests/test_v08.py tests/test_phq_xport_zero.py

printf '=== Isolated production build and npm audit ===\n'
BUILD="$(mktemp -d /tmp/frailtyscope-v081-publish-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app";mkdir -p "$BUILD/public/data";cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-audit --no-fund && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)

printf '=== Stage only explicitly approved files; reject ANY other staged file ===\n'
FILES=(.github/workflows/ci.yml ml/realdata_nhanes.py ml/nhanes_quality.py tests/test_phq_xport_zero.py scripts/repair_phq_v081.sh scripts/publish_phq_v081.sh web/public/data/nhanes-aggregate.json web/public/data/nhanes-refinement.json web/public/data/nhanes-cohort-profile.json)
git add -- "${FILES[@]}"
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for staged in "${STAGED[@]}";do
  approved=0
  for file in "${FILES[@]}";do
    if [[ "$staged" == "$file" ]];then approved=1;break;fi
  done
  if (( !approved ));then
    echo "ERROR: Unapproved staged file: $staged"
    exit 1
  fi
done
for dir in data artifacts private restricted approved_data hunt_data node_modules catboost_info;do
  for staged in "${STAGED[@]}";do
    if [[ "$staged" == "$dir/"* ]];then echo "ERROR: Local research file staged: $staged";exit 1;fi
  done
done
git diff --cached --check
git diff --cached --stat
if git diff --cached --quiet;then echo 'Nothing new to publish';exit 0;fi
printf 'Model and data provenance corrected. Inspect the metrics above carefully.\n'
read -r -p 'Push these reviewed aggregate-only changes to GitHub main? Type YES: ' CONFIRM
[[ "$CONFIRM" == YES ]] || { echo 'Publication cancelled; source and reports retained locally';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main changed; do not force push';exit 1; }
git commit -m 'fix: decode NHANES PHQ-9 zero responses and refresh real-data metrics'
git push origin main
printf '\nSUCCESS: Corrected source and aggregates pushed. Verify Vercel Ready status.\n'
