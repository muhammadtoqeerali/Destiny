#!/usr/bin/env bash
# Atomic local source-only installer. Never commits, pushes, loads real participant data or clinical models.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='5b77d2ebab4f742926981a55ca2473f422f1fbc9'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.38 main required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing tracked/staged changes, no overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote moved, review required';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=(
 .github/workflows/ci.yml
 scripts/run_browser_qa_v34.sh
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
)
added=(
 ml/inference_readiness_v39.py
 research/MODEL_READINESS_V39.md
 scripts/patch_readiness_v39.py
 scripts/install_readiness_v39.sh
 scripts/publish_readiness_v39.sh
 tests/test_inference_readiness_v39.py
 tests/browser_readiness_v39.py
 web/app/data/inference-readiness-v39.json
 web/app/api/inference/readiness/route.ts
 web/app/components/inference-evidence-v39.tsx
 web/app/inference-v39.css
)
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: New path already exists: $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing bundled source: $f";exit 1; }
done
BACKUP="$(mktemp -d /tmp/frailtyscope-v39-original-XXXXXXXX)"
for f in "${tracked[@]}";do
 [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/symlink original $f";exit 1; }
 mkdir -p "$BACKUP/$(dirname "$f")";cp -p -- "$f" "$BACKUP/$f"
done
rollback(){
 local code=$?
 trap - ERR
 echo 'ERROR: v0.39 installation failed. Restore tracked originals; remove only v0.39 additions.'
 for f in "${tracked[@]}";do cp -p -- "$BACKUP/$f" "$f";done
 for f in "${added[@]}";do rm -f -- "$f";done
 exit "$code"
}
trap rollback ERR
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_readiness_v39.py --root "$ROOT"
echo '=== Public-document-only inference readiness verification ==='
PYTHONPATH=. .venv/bin/python -m ml.inference_readiness_v39 --check
echo '=== CSS syntax ==='
(cd web && node -e "const fs=require('fs');const p=require('postcss');p.parse(fs.readFileSync('app/inference-v39.css','utf8'));console.log('PASS: v0.39 CSS parsed')")
echo '=== Complete fixture and privacy regression suite ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
echo '=== Immutable private review READ ONLY ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== TypeScript and Next.js production build ==='
(cd web && npm run lint && npm run build)
echo '=== All desktop and mobile Chromium QA ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR
echo 'SUCCESS: v0.39 documentary model readiness and portable CI browser runner validated LOCALLY. No commit or push.'
echo "Backups: $BACKUP"
