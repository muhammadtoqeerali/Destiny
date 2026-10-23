#!/usr/bin/env bash
# Atomic install: strict base, exact original blob hashes, backups, rollback, no git stage/commit/push.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='79698cf9874814a2f8d9154b26bc68d51bf3bae8'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: v0.37 main HEAD required. No changes made.';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Tracked/staged work present; refusing to overwrite.';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main moved. Fresh review required.';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=(
 .github/workflows/ci.yml
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
 scripts/run_browser_qa_v34.sh
 tests/browser_doctor_v35.py
 tests/browser_doctor_v36.py
 tests/browser_inference_v37.py
 tests/test_demo_qa_v34.py
 tests/test_doctor_v35.py
)
added=(
 research/CONSOLIDATED_PLATFORM_V38.md
 scripts/build_fictional_models_v38.py
 scripts/patch_platform_v38.py
 scripts/install_platform_v38.sh
 scripts/publish_platform_v38.sh
 tests/test_platform_v38.py
 tests/browser_platform_v38.py
 web/app/components/multioutcome-lab-v38.tsx
 web/app/inference-v38.css
 web/app/api/inference/route.ts
 web/app/data/fictional-model-registry-v38.json
)
for f in "${added[@]}"; do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: New source already exists: $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing/unsafe package source: $f";exit 1; }
done
BACKUP="$(mktemp -d /tmp/frailtyscope-v38-original-XXXXXXXX)"
for f in "${tracked[@]}"; do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe tracked file: $f";exit 1; }; mkdir -p "$BACKUP/$(dirname "$f")";cp -p -- "$f" "$BACKUP/$f";done
started=1
rollback(){
 local exit_code=$?
 trap - ERR
 echo 'ERROR: v0.38 validation/install failed. Restoring tracked originals; deleting only v0.38 additions.'
 for f in "${tracked[@]}";do cp -p -- "$BACKUP/$f" "$f";done
 for f in "${added[@]}";do rm -f -- "$f";done
 exit "$exit_code"
}
trap rollback ERR
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_platform_v38.py --root "$ROOT"
echo '=== Deterministically regenerate synthetic model registry (verification only) ==='
.venv/bin/python scripts/build_fictional_models_v38.py --check
echo '=== Parse new CSS with Next.js PostCSS ==='
(cd web && node -e "const fs=require('fs');require('postcss').parse(fs.readFileSync('app/inference-v38.css','utf8'));console.log('PASS: v0.38 CSS parsed')")
echo '=== Full research fixtures, governance and API/model source checks ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
echo '=== Read-only immutable private v0.30 review ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Production TypeScript and Next.js build ==='
(cd web && npm run lint && npm run build)
echo '=== Complete desktop/mobile v0.34-v0.38 browser QA ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR
echo 'SUCCESS: v0.38 consolidated platform installed and validated locally. No push, real participant inference or clinical serving.'
echo "Tracked originals retained at: $BACKUP"
