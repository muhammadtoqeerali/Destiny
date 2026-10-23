#!/usr/bin/env bash
# Source-only fail-closed v0.37 install; no protected research writes.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='55b1d48e0a2496144722d7e704310da579e21eaf'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected published v0.36 main baseline'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Unexpected tracked or staged edits'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main moved. Fresh review required.'; exit 1; }
(cd "$PKG" && sha256sum -c SHA256SUMS)
tracked=(
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
 scripts/run_browser_qa_v34.sh
 .github/workflows/ci.yml
)
expected=(
 0e5bf1872d0500795126fd8eafb5402b35b1100c
 ddf08f192e6a73ff3ade9d0a5a370005b6af8492
 cea793010c649a9080b0460bd2779deb572e6db1
 cb55a546fb0307f126bd78eca9114ad50a226356
)
new=(
 research/INFERENCE_READINESS_V37.md
 scripts/patch_inference_v37.py
 scripts/install_inference_v37.sh
 scripts/publish_inference_v37.sh
 tests/test_runtime_gate_v37.py
 tests/browser_inference_v37.py
 web/app/components/inference-readiness-v37.tsx
 web/app/inference-v37.css
)
for i in "${!tracked[@]}";do
 p="${tracked[$i]}"
 [[ -f "$p" && ! -L "$p" && "$(git hash-object "$p")" == "${expected[$i]}" ]] || { echo "ERROR: Tracked baseline differs: $p"; exit 1; }
done
for p in "${new[@]}";do [[ ! -e "$p" && ! -L "$p" ]] || { echo "ERROR: Refusing to overwrite existing source: $p"; exit 1; };done
BACKUP="$(mktemp -d /tmp/frailtyscope-v37-original-XXXXXXXX)"
for p in "${tracked[@]}";do mkdir -p "$BACKUP/$(dirname "$p")"; cp "$p" "$BACKUP/$p";done
rollback(){
 echo 'ERROR: v0.37 validation failed. Restoring original tracked source; removing only v0.37 additions.'
 for p in "${tracked[@]}";do cp "$BACKUP/$p" "$p";done
 for p in "${new[@]}";do rm -f -- "$p";done
}
trap rollback ERR
for p in "${new[@]}";do mkdir -p "$(dirname "$p")";cp "$PKG/$p" "$p";done
.venv/bin/python scripts/patch_inference_v37.py "$ROOT"
printf '=== Parse synthetic-scoring CSS via actual web PostCSS ===\n'
(cd web && node -e "const fs=require('fs'),pc=require('postcss');pc.parse(fs.readFileSync('app/inference-v37.css','utf8'));console.log('PASS: CSS parses')")
printf '=== All synthetic/privacy/browser source regressions ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Private immutable integrity check READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== TypeScript and Next.js production build ===\n'
(cd web && npm run lint && npm run build)
printf '=== Real Chromium QA: all prior versions plus v0.37 ===\n'
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR
echo 'SUCCESS: v0.37 local synthetic scoring example and clinical inference gate passed. NO push.'
printf 'Original source backup: %s\n' "$BACKUP"
