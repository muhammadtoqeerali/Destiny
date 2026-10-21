#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Require main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected origin';exit 1; }
[[ -f artifacts/realdata_nhanes/quality_v08.json && -f artifacts/realdata_nhanes/km_audit_v08.json ]] || { echo 'ERROR: Run local analysis first';exit 1; }
[[ -f web/public/data/nhanes-cohort-profile.json ]] || { echo 'ERROR: Cohort aggregate missing';exit 1; }
PYTHONPATH=. .venv/bin/python -m ml.nhanes_cohort_profile
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('web/public/data')
names={x.name for x in p.glob('*.json')}
assert names=={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json'},names
for name in names:
    d=json.loads((p/name).read_text()); assert d['provenance']=='REAL_NHANES_AGGREGATE_ONLY'
    assert not any(k in d for k in ('patients','cases','SEQN','records','predictions'))
for x in p.iterdir():
    assert x.name in names,'Unexpected public data file: '+x.name
print('PASS: public files are allowlisted aggregates')
PY
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py tests/test_v08.py
BUILD="$(mktemp -d /tmp/fs-v08-release-build-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data";cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-audit --no-fund && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)
FILES=(ml/nhanes_quality.py ml/nhanes_cohort_profile.py ml/nhanes_survival.py ml/nhats_contract.py scripts/local_respondent_explorer.py scripts/install_and_analyze_v08.sh scripts/publish_v08.sh tests/test_v08.py research/NHATS_MAPPING_TEMPLATE.json web/app/components/clinical-workspace.tsx web/app/nhanes.css web/public/data/nhanes-cohort-profile.json)
# Files from previous interrupted commands may be staged; reject anything unapproved.
git add -- "${FILES[@]}"
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for path in "${STAGED[@]}";do
 approved=0
 for item in "${FILES[@]}";do
   if [[ "$path" == "$item" ]];then approved=1;break;fi
 done
 if (( ! approved ));then echo "ERROR: Unapproved staged path: $path";exit 1;fi
done
git diff --cached --check
if git diff --cached --quiet;then echo 'No new changes to publish';exit 0;fi
git diff --cached --stat
read -r -p 'Push reviewed NHANES aggregate-only release to GitHub main? Type YES: ' APPROVE
[[ "$APPROVE" == YES ]] || { echo 'Publish canceled';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote changed; do not overwrite';exit 1; }
git commit -m 'feat: real NHANES cohort profiles and local longitudinal research tools'
git push origin main
printf '\nPUSH SUCCESS. Check Vercel Ready: https://destiny-amber-phi.vercel.app/\n'
