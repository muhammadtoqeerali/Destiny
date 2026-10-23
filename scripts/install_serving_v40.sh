#!/usr/bin/env bash
# Atomic source-only local installation; no Git push, participant data, or real model fitting.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='bbef3c6aac5565a8e31b395238b60ae4be59805a'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.39 main required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing tracked changes, no overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote moved, review required';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh tests/browser_inference_v37.py web/app/components/clinical-workspace.tsx web/app/layout.tsx )
added=(
 research/SYNTHETIC_SERVING_V40.md
 scripts/install_serving_v40.sh
 scripts/patch_serving_v40.py
 scripts/publish_serving_v40.sh
 tests/test_serving_v40.py
 tests/browser_serving_v40.py
 web/app/api/inference/synthetic/route.ts
 web/app/lib/synthetic-serving-v40.ts
 web/app/components/synthetic-server-v40.tsx
 web/app/inference-serving-v40.css
)
for f in "${added[@]}"; do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: New file already exists: $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing bundled source: $f";exit 1; }
done
BACKUP="$(mktemp -d /tmp/frailtyscope-v40-original-XXXXXXXX)"
for f in "${tracked[@]}";do
 [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe original: $f";exit 1; }
 mkdir -p "$BACKUP/$(dirname "$f")";cp -p -- "$f" "$BACKUP/$f"
done
rollback(){
 local code=$?
 trap - ERR
 set +e  # A restore failure must not prevent cleanup of the other exact allowlisted paths.
 echo 'ERROR: v0.40 validation failed. Restoring tracked source; removing only v0.40 additions.'
 local failed=0
 for f in "${tracked[@]}"; do
   cp -p -- "$BACKUP/$f" "$f" || { echo "ERROR: Could not restore $f"; failed=1; }
 done
 for f in "${added[@]}"; do
   rm -f -- "$f" || { echo "ERROR: Could not remove $f"; failed=1; }
 done
 if [[ "$failed" -ne 0 ]]; then
   echo "ERROR: Incomplete rollback. Original files retained at: $BACKUP"
 fi
 exit "${code:-1}"
}
trap rollback ERR
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_serving_v40.py --root "$ROOT"
echo '=== Parse v0.40 CSS and validate route source ==='
(cd web && node -e "const fs=require('fs');require('postcss').parse(fs.readFileSync('app/inference-serving-v40.css','utf8'));console.log('PASS: v0.40 CSS parsed')")
echo '=== Full source-only fixtures and research privacy regression ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
echo '=== Historical immutable v0.30 review READ ONLY ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Production types and Next.js build ==='
(cd web && npm run lint && npm run build)
echo '=== Mandatory complete desktop/mobile browser QA ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR
echo 'SUCCESS: v0.40 synthetic serving architecture installed and validated LOCALLY. No commit or push; real patient inference remains disabled.'
echo "Tracked original source backup: $BACKUP"
