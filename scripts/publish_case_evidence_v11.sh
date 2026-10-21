#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected origin';exit 1; }
FILES=(
 ml/case_forensics_v11.py ml/case_enhancement_v11.py ml/case_model_io_v11.py ml/case_engine_v10.py
 scripts/export_case_audit_v11.py scripts/local_transformation_inspector_v11.py scripts/patch_admin_v11.py scripts/patch_layout_v11.py scripts/patch_ci_v11.py
 scripts/install_case_evidence_v11.sh scripts/publish_case_evidence_v11.sh
 tests/test_case_forensics_v11.py tests/test_case_model_io_v11.py tests/test_clean_model_reload_v112.py research/MODEL_ARTIFACT_PROTOCOL_V112.md scripts/repair_model_reload_v112.sh research/CASE_EVIDENCE_V11.md
 web/app/components/evidence-workbench-v11.tsx web/app/nhanes-v11.css
 web/app/components/multi-outcome-admin.tsx web/app/layout.tsx .github/workflows/ci.yml
 web/public/data/nhanes-case-audit-v11.json
)

# Refuse any staged path outside the explicitly reviewed release.
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for file in "${STAGED[@]}";do
 allowed=0
 for item in "${FILES[@]}";do if [[ "$file" == "$item" ]];then allowed=1;break;fi;done
 (( allowed )) || { echo "ERROR: Unapproved pre-staged file: $file";exit 1; }
done

echo '=== Verify report reproducibility and protected release ==='
PYTHONPATH=. .venv/bin/python scripts/export_case_audit_v11.py
PYTHONPATH=. .venv/bin/python -m pytest -q tests
.venv/bin/python - <<'PY'
from pathlib import Path
import json
p=Path('web/public/data')
expected={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json','nhanes-case-audit-v11.json'}
assert {x.name for x in p.iterdir() if x.is_file()}==expected
obj=json.loads((p/'nhanes-case-audit-v11.json').read_text())
assert obj['schema']=='FRAILTYSCOPE_PUBLIC_CASE_AUDIT_V11'
assert obj['provenance']=='REAL_NHANES_AGGREGATE_ONLY'
assert len(obj['features'])==14
assert all(x['n']>=50 for x in obj['evaluation']['calibration'])
assert all(x['n']>=100 for x in obj['evaluation']['subgroups'])
print('PASS: Approved data shapes and disclosure screening')
PY

echo '=== Typecheck, production build and security audit ==='
BUILD="$(mktemp -d /tmp/frailtyscope-v11-publish-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app";mkdir -p "$BUILD/public/data";cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-fund --no-audit && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)

git add -- "${FILES[@]}"
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)
for file in "${STAGED[@]}";do
 allowed=0
 for item in "${FILES[@]}";do if [[ "$file" == "$item" ]];then allowed=1;break;fi;done
 (( allowed )) || { echo "ERROR: Unapproved staged file: $file";exit 1; }
done
[[ ${#STAGED[@]} -gt 0 ]] || { echo 'No changes staged';exit 0; }
git diff --cached --check
git diff --cached --stat
printf '\nONLY reviewed code and aggregate diagnostics will be pushed. No participant records, local reports, or model binaries.\n'
read -r -p 'Approve FrailtyScope v0.11 publication? Type YES: ' CONFIRM
[[ "$CONFIRM" == YES ]] || { echo 'No publication';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main changed; no push';exit 1; }
git commit -m 'feat: deep dataset forensics, fitted preprocessing and evaluated model evidence'
git push origin main
echo 'SUCCESS: v0.11 verified data-science workbench pushed to GitHub main.'
