#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ -x .venv/bin/python ]] || { echo 'ERROR: Missing .venv/bin/python';exit 1; }
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Require Git main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected origin';exit 1; }
[[ -f data/processed/nhanes_5yr_local.csv && -f artifacts/realdata_nhanes/report.json ]] || { echo 'ERROR: Existing NHANES cohort/report missing';exit 1; }
[[ -f data/raw/nhanes/2011-2012/DPQ_G.XPT && -f data/raw/nhanes/2013-2014/DPQ_H.XPT ]] || { echo 'ERROR: Raw DPQ source files missing';exit 1; }
[[ -f ml/realdata_nhanes.py && -f ml/nhanes_quality.py && -f ml/nhanes_refinement.py ]] || { echo 'ERROR: Expected v0.8 installed';exit 1; }
FILES=(ml/realdata_nhanes.py ml/nhanes_quality.py .github/workflows/ci.yml tests/test_phq_xport_zero.py scripts/repair_phq_v081.sh scripts/publish_phq_v081.sh)
for file in "${FILES[@]}";do
  if git ls-files --error-unmatch "$file" >/dev/null 2>&1;then
    if ! git diff --quiet -- "$file" || ! git diff --cached --quiet -- "$file";then
      echo "ERROR: Uncommitted source changes: $file";exit 1
    fi
  elif [[ -e "$file" ]];then
    echo "ERROR: Refusing to overwrite existing untracked file: $file";exit 1
  fi
done
if ! git diff --cached --quiet;then echo 'ERROR: Existing staged changes need review first';exit 1;fi
OLD_TOTAL="$(.venv/bin/python - <<'PY'
import pandas as pd
p='data/processed/nhanes_5yr_local.csv'
d=pd.read_csv(p,usecols=['SEQN','cycle','outcome_5yr','data_origin'])
assert set(d.data_origin)=={'NHANES_PUBLIC_2019_LMF'}
assert not d.SEQN.duplicated().any()
print(f'{len(d)}:{int(d.outcome_5yr.sum())}:{sum(d.cycle.eq("2013-2014"))}')
PY
)"
echo "Original cohort/event summary (total:events:later-cycle): $OLD_TOTAL"
BACKUP="$(mktemp -d /tmp/frailtyscope-v081-source-backup-XXXXXX)"
for file in "${FILES[@]}";do
  mkdir -p "$BACKUP/$(dirname "$file")" "$(dirname "$file")"
  if [[ -f "$file" ]];then cat "$file" > "$BACKUP/$file";fi
  cat "$SOURCE/$file" > "$file"
done
echo "Source backups (temporary only): $BACKUP"
echo '=== Regression tests before processing records ==='
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_phq_xport_zero.py

echo '=== Rebuild NHANES participants from cached actual CDC XPT sources ==='
PYTHONPATH=. .venv/bin/python -m ml.realdata_nhanes --cache data/raw/nhanes --output data/processed/nhanes_5yr_local.csv
NEW_TOTAL="$(.venv/bin/python - <<'PY'
import pandas as pd
p='data/processed/nhanes_5yr_local.csv';d=pd.read_csv(p)
assert set(d.data_origin)=={'NHANES_PUBLIC_2019_LMF'}
assert not d.SEQN.duplicated().any()
print(f'{len(d)}:{int(d.outcome_5yr.sum())}:{sum(d.cycle.eq("2013-2014"))}')
PY
)"
[[ "$OLD_TOTAL" == "$NEW_TOTAL" ]] || { echo "ERROR: Cohort/label counts changed: original $OLD_TOTAL, new $NEW_TOTAL";exit 1; }
echo 'PASS: Existing cohort and mortality labels unchanged'

echo '=== Verify PHQ-9 against raw CDC XPT source ==='
PYTHONPATH=. .venv/bin/python -m ml.nhanes_quality
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
report=json.loads(Path('artifacts/realdata_nhanes/quality_v08.json').read_text())
assert report['phq9_flag']=='COVERAGE_OK',report
assert report['phq9_complete_percent']>50,report
assert all(x['mismatch_count']==0 for x in report['phq9_by_cycle'].values()),report
assert all(x['xport_zero_alias_values_corrected']>0 for x in report['phq9_by_cycle'].values()),report
print('PASS: Corrected PHQ-9 coverage:',report['phq9_complete_percent'],'percent')
PY

echo '=== Retrain baseline four-model benchmark with corrected PHQ-9 feature ==='
PYTHONPATH=. .venv/bin/python -m ml.realdata_train --input data/processed/nhanes_5yr_local.csv --report artifacts/realdata_nhanes/report.json
PYTHONPATH=. .venv/bin/python scripts/export_nhanes_aggregate.py --report artifacts/realdata_nhanes/report.json --out web/public/data/nhanes-aggregate.json

echo '=== Re-run refined four-model search (development data only) ==='
PYTHONPATH=. .venv/bin/python -m ml.nhanes_refinement --input data/processed/nhanes_5yr_local.csv --out artifacts/realdata_nhanes/refinement.json --trials "${TRIALS:-10}"
PYTHONPATH=. .venv/bin/python scripts/export_nhanes_refinement.py --report artifacts/realdata_nhanes/refinement.json --output web/public/data/nhanes-refinement.json

echo '=== Rebuild real aggregate health profiles ==='
PYTHONPATH=. .venv/bin/python -m ml.nhanes_cohort_profile

echo '=== Run complete research regression suite ==='
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py tests/test_v08.py tests/test_phq_xport_zero.py

echo '=== Check local reports and only allowlisted public JSON ==='
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from scripts.export_nhanes_aggregate import export
from scripts.export_nhanes_refinement import report_to_public
from ml.nhanes_cohort_profile import build_profile
import pandas as pd
p=Path('web/public/data');expected={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json'}
assert {f.name for f in p.iterdir()}==expected,'Unexpected file in public data directory'
public={f.name:json.loads(f.read_text()) for f in p.iterdir()}
assert public['nhanes-aggregate.json']==export(json.loads(Path('artifacts/realdata_nhanes/report.json').read_text()))
assert public['nhanes-refinement.json']==report_to_public(json.loads(Path('artifacts/realdata_nhanes/refinement.json').read_text()))
q=json.loads(Path('artifacts/realdata_nhanes/quality_v08.json').read_text())
profile=build_profile(pd.read_csv('data/processed/nhanes_5yr_local.csv'),q)
assert public['nhanes-cohort-profile.json']==profile
counts={public[x]['counts']['total'] for x in ('nhanes-aggregate.json','nhanes-refinement.json')}
assert counts=={2422},counts
assert all(public[x]['provenance']=='REAL_NHANES_AGGREGATE_ONLY' for x in expected)
assert 'PHQ-9 excluded from descriptive profiles pending raw-data completeness review' not in profile.get('notes',[])
print('PASS: Model reports and aggregate-only public files are in sync')
PY

echo '=== Isolated Next.js production build and audit ==='
BUILD="$(mktemp -d /tmp/frailtyscope-v081-build-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app";mkdir -p "$BUILD/public/data";cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-audit --no-fund && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)

echo '=== Current corrected findings (do not assume improvement) ==='
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
for fname in ['nhanes-aggregate.json','nhanes-refinement.json']:
    d=json.loads((Path('web/public/data')/fname).read_text())
    print(fname,'model:',d['selectedModel'],'test ROC-AUC:',d['testAtF2']['roc_auc'] if 'testAtF2' in d else d['test']['roc_auc'])
print('PHQ-9 observed:',json.loads(Path('artifacts/realdata_nhanes/quality_v08.json').read_text())['phq9_complete_percent'],'percent')
PY
printf '\nREADY FOR REVIEW. No GitHub push performed.\n'
printf 'To publish only after reviewing results: bash scripts/publish_phq_v081.sh\n'
