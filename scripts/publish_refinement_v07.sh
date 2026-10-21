#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$PROJECT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main';exit 1; }
URL="$(git remote get-url origin)"
[[ "$URL" == 'https://github.com/muhammadtoqeerali/Destiny.git' || "$URL" == 'git@github.com:muhammadtoqeerali/Destiny.git' ]] || { echo 'ERROR: Unexpected Git origin';exit 1; }
[[ -f artifacts/realdata_nhanes/refinement.json && -f web/public/data/nhanes-refinement.json ]] || { echo 'ERROR: Run workstation refinement first';exit 1; }
[[ -f web/public/data/nhanes-aggregate.json ]] || { echo 'ERROR: Baseline aggregate missing';exit 1; }
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from scripts.export_nhanes_refinement import report_to_public
report=json.loads(Path('artifacts/realdata_nhanes/refinement.json').read_text())
expected=report_to_public(report)
export=json.loads(Path('web/public/data/nhanes-refinement.json').read_text())
assert export==expected,'Export does not match current real-data training report'
assert set(p.name for p in Path('web/public/data').glob('*.json'))=={'nhanes-aggregate.json','nhanes-refinement.json'}
for item in Path('web/app').rglob('*.tsx'):
 text=item.read_text()
 assert not any(x in text for x in ['multioutcome-demo.json','shap-summary-demo.json','public/data/demo.json','HUNT transfer','What comes next']),item
print('PASS: Real aggregate data only. No old synthetic panel content.')
PY
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_real_nhanes.py tests/test_public_aggregate.py tests/test_nhanes_refinement.py
BUILD="$(mktemp -d /tmp/frailtyscope-publish-build-XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
cp web/package.json web/package-lock.json web/tsconfig.json web/next.config.mjs web/next-env.d.ts "$BUILD/"
cp -R web/app "$BUILD/app"
mkdir -p "$BUILD/public/data"
cp web/public/data/*.json "$BUILD/public/data/"
(cd "$BUILD" && npm ci --no-audit --no-fund && npm run lint && npm run build && npm audit --omit=dev --audit-level=high)
FILES=(.github/workflows/ci.yml ml/nhanes_refinement.py scripts/export_nhanes_refinement.py scripts/run_nhanes_refinement.sh scripts/publish_refinement_v07.sh tests/test_nhanes_refinement.py web/app/components/clinical-workspace.tsx web/app/components/multi-outcome-admin.tsx web/app/admin/page.tsx web/app/admin/login/page.tsx web/app/layout.tsx web/app/nhanes.css web/public/data/nhanes-refinement.json)
git add -- "${FILES[@]}"
# Publish only explicitly approved release files.
mapfile -d '' -t STAGED < <(git diff --cached --name-only -z)

for staged in "${STAGED[@]}"; do
  approved=0

  for file in "${FILES[@]}"; do
    if [[ "$staged" == "$file" ]]; then
      approved=1
      break
    fi
  done

  if (( ! approved )); then
    printf 'ERROR: Unapproved staged file: %s\n' "$staged"
    exit 1
  fi
done

echo 'PASS: All staged files match release allowlist'

git diff --cached --check
git diff --cached --stat
if git diff --cached --quiet;then echo 'Nothing new to publish';exit 0;fi
echo '=== Push only after metric review and approval ==='
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main has changed. Reconcile without force pushing';exit 1; }
git commit -m 'feat: real NHANES model refinement and clinical research portal'
git push origin main
printf '\nPUBLISHED SOURCE AND AGGREGATES: https://destiny-amber-phi.vercel.app/\n'
