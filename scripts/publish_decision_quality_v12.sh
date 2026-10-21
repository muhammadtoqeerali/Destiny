#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main';exit 1; }
ORIGIN="$(git remote get-url origin)"
[[ "$ORIGIN" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$ORIGIN" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected origin';exit 1; }
FILES=(
 ml/case_decision_quality_v12.py
 scripts/export_decision_quality_v12.py scripts/patch_ui_ci_v12.py
 scripts/install_decision_quality_v12.sh scripts/publish_decision_quality_v12.sh
 tests/test_decision_quality_v12.py research/DECISION_EVALUATION_V12.md
 web/app/components/decision-quality-v12.tsx web/app/nhanes-v12.css
 web/app/components/multi-outcome-admin.tsx web/app/layout.tsx .github/workflows/ci.yml
 web/public/data/nhanes-decision-quality-v12.json
)
allowed(){ local f="$1";for a in "${FILES[@]}";do [[ "$f" == "$a" ]] && return 0;done;return 1; }
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for f in "${STAGED[@]}";do allowed "$f" || { echo "ERROR: Unapproved staged path: $f";exit 1; };done
for f in "${FILES[@]}";do [[ -f "$f" ]] || { echo "ERROR: Missing release file $f";exit 1; };done
[[ -f artifacts/cases/nhanes_mortality_v10/decision_quality_v12_local.json ]] || { echo 'ERROR: Run workstation evaluation first';exit 1; }

echo '=== Reproducible real aggregate check; NO training ==='
PYTHONPATH=. .venv/bin/python scripts/export_decision_quality_v12.py
PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
import json
p=Path('web/public/data')
assert {x.name for x in p.iterdir() if x.is_file()}=={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json','nhanes-case-audit-v11.json','nhanes-decision-quality-v12.json'}
d=json.loads((p/'nhanes-decision-quality-v12.json').read_text())
assert d['counts']=={'validation':292,'evaluation':1257,'events':246}
assert d['provenance']=='REAL_NHANES_AGGREGATE_ONLY'
assert all(z['n']>=100 and min(z['events'],z['n']-z['events'])>=20 for z in d['subgroups'])
assert all(z['n']>=50 and min(z['events'],z['n']-z['events'])>=10 for z in d['calibration_bands'])
print('PASS: Validated real-data aggregate boundary')
PY

echo '=== Validate exact production frontend and dependencies ==='
BUILD="$(mktemp -d /tmp/frailtyscope-v12-publish-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data"; cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-fund --no-audit && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)

git add -- "${FILES[@]}"
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for f in "${STAGED[@]}";do allowed "$f" || { echo "ERROR: Unapproved staged file: $f";exit 1; };done
[[ ${#STAGED[@]} -gt 0 ]] || { echo 'No new changes staged';exit 0; }
git diff --cached --check
git diff --cached --stat
printf '\nOnly source, tests, documentation and disclosure-screened NHANES aggregate data will be published.\n'
read -r -p 'Approve FrailtyScope v0.12 decision-quality source and aggregate release? Type YES: ' APPROVAL
[[ "$APPROVAL" == YES ]] || { echo 'Publication declined';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: main diverged; refuse push';exit 1; }
git commit -m 'feat: decision-quality evaluation with confidence, calibration and subgroup audits'
git push origin main
echo 'SUCCESS: FrailtyScope v0.12 pushed; no participant records or fitted models published.'
