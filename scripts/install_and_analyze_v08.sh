#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Switch to main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected repository origin';exit 1; }
[[ -f data/processed/nhanes_5yr_local.csv && -f artifacts/realdata_nhanes/refinement.json ]] || { echo 'ERROR: Local REAL NHANES source/results missing';exit 1; }
[[ -x .venv/bin/python ]] || { echo 'ERROR: Missing workstation Python environment';exit 1; }
echo '=== Fetch GitHub main (no force or reset) ==='
git pull --ff-only origin main
[[ -f web/public/data/nhanes-refinement.json && -f web/public/data/nhanes-aggregate.json ]] || { echo 'ERROR: v0.7 NHANES aggregates missing';exit 1; }
echo '=== Install v0.8 source (content copying; no permission preservation) ==='
FILES=(ml/nhanes_quality.py ml/nhanes_cohort_profile.py ml/nhanes_survival.py ml/nhats_contract.py scripts/local_respondent_explorer.py scripts/install_and_analyze_v08.sh scripts/publish_v08.sh tests/test_v08.py research/NHATS_MAPPING_TEMPLATE.json web/app/components/clinical-workspace.tsx web/app/nhanes.css)
for file in "${FILES[@]}";do
 mkdir -p "$(dirname "$file")"
 cat "$RELEASE/$file" > "$file"
done
echo '=== Audit CDC DPQ raw fields against processed PHQ-9 (aggregate only) ==='
PYTHONPATH=. .venv/bin/python -m ml.nhanes_quality
echo '=== Real-data cohort health profiles (weighted descriptive summaries) ==='
PYTHONPATH=. .venv/bin/python -m ml.nhanes_cohort_profile
echo '=== Kaplan-Meier follow-up audit (LOCAL FILE ONLY) ==='
PYTHONPATH=. .venv/bin/python -m ml.nhanes_survival
echo '=== Run project tests and new research QA tests ==='
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py tests/test_v08.py
echo '=== Reject unapproved public data assets ==='
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('web/public/data');names={x.name for x in p.glob('*.json')}
assert names=={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json'},names
for name in names:
    data=json.loads((p/name).read_text())
    assert data['provenance']=='REAL_NHANES_AGGREGATE_ONLY'
    assert not any(k in data for k in ['patients','cases','records','SEQN','predictions'])
profile=json.loads((p/'nhanes-cohort-profile.json').read_text())
assert len(profile['groups'])>0
for g in profile['groups']:
    assert g['n']>=50
    for row in g['conditions']+g['mobility']:
        assert row['n_observed']>=50
for tsx in Path('web/app').rglob('*.tsx'):
    src=tsx.read_text()
    assert not any(x in src for x in ['multioutcome-demo.json','shap-summary-demo.json','public/data/demo.json']),tsx
print('PASS: aggregate-only publication boundary')
PY
echo '=== Typecheck and build the exact proposed frontend, isolated ==='
TMP="$(mktemp -d /tmp/frailtyscope-v08-frontend-XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$TMP/"
cp -R web/app "$TMP/app"
mkdir -p "$TMP/public/data";cp web/public/data/*.json "$TMP/public/data/"
(cd "$TMP" && npm ci --no-fund --no-audit && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)
echo 'READY FOR REVIEW: no GitHub push performed.'
echo 'Summary: data quality artifacts/realdata_nhanes/quality_v08.json; KM audit artifacts/realdata_nhanes/km_audit_v08.json'
echo 'Local records browser: PYTHONPATH=. .venv/bin/python scripts/local_respondent_explorer.py --port 8501'
echo 'After reviewing aggregate outputs, publish with: bash scripts/publish_v08.sh'
