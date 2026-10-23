#!/usr/bin/env bash
# Fail-closed source-only installer for exactly v0.40 main; never stages or pushes.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='90a426b131a408cc438c931e03aa43322d81a7e0'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.40 main is required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing tracked changes; refusing overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main changed';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/components/clinical-workspace.tsx web/app/layout.tsx )
added=(
 ml/research_validation_v41.py
 research/VALIDATION_AND_PROMOTION_V41.md
 scripts/install_validation_v41.sh
 scripts/patch_validation_v41.py
 scripts/publish_validation_v41.sh
 tests/test_validation_v41.py
 tests/browser_validation_v41.py
 web/app/api/inference/validation/route.ts
 web/app/components/validation-gate-v41.tsx
 web/app/data/validation-readiness-v41.json
 web/app/validation-v41.css
)
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: Existing v0.41 source $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing/unsafe bundled file $f";exit 1; }
done
BACKUP="$(mktemp -d /tmp/frailtyscope-v41-original-XXXXXXXX)"
for f in "${tracked[@]}";do
 [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe tracked file $f";exit 1; }
 mkdir -p "$BACKUP/$(dirname "$f")";cp -p -- "$f" "$BACKUP/$f"
done
rollback(){
 local status=$?
 trap - ERR INT TERM
 set +e
 echo 'ERROR: v0.41 validation failed; reverting only approved source paths.'
 local failed=0
 for f in "${tracked[@]}";do cp -p -- "$BACKUP/$f" "$f" || failed=1;done
 for f in "${added[@]}";do rm -f -- "$f" || failed=1;done
 if [[ "$failed" -ne 0 ]];then echo "ERROR: Partial rollback; backup $BACKUP";fi
 exit "${status:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_validation_v41.py --root "$ROOT"
bash -n scripts/install_validation_v41.sh
bash -n scripts/publish_validation_v41.sh
echo '=== Verify public documentary gates and invented held-aside metrics ==='
PYTHONPATH=. .venv/bin/python -m ml.research_validation_v41 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/validation-v41.css','utf8'));console.log('PASS: v0.41 CSS parsed')")
echo '=== Complete synthetic/privacy/source regression ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
echo '=== Immutable historical integrity READ ONLY ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== TypeScript and production build ==='
(cd web && npm run lint && npm run build)
echo '=== Mandatory desktop and mobile Chromium browser QA ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: v0.41 synthetic validation and public science gate installed and verified LOCALLY. No commit or push.'
echo "Original tracked source backup: $BACKUP"
