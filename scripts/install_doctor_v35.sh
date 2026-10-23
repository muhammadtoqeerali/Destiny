#!/usr/bin/env bash
# Guarded source-only v0.35 Doctor Portal installation, no commit/push.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='d8c43e380d0b3296440c3eeb3ce5e7331e59ac97'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected reviewed v0.34 main baseline'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Preexisting tracked or staged changes; review before install'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main changed; stop'; exit 1; }
(cd "$PKG" && sha256sum -c SHA256SUMS)
tracked=(
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
 scripts/run_browser_qa_v34.sh
 .github/workflows/ci.yml
 tests/test_demo_qa_v34.py
 tests/browser_qa_v34.py
)
expected=(
 75d11953b4f773f94cf6d62e7e5517936cea3b0c
 88049a29799782aa49d35d1bdfb615b702cb9d85
 00a776b15d4199087f7c196c37b1d73fc4ab596c
 9f615f1a36246abfc792132e7631519e329723ba
 87025a098b394bfab0d076b82b9e9a7ddecf7cfb
 9ea27d426d2e67a2962451adbff59393fb3ebcd5
)
added=(
 web/app/components/doctor-visuals-v35.tsx
 web/app/doctor-v35.css
 scripts/patch_doctor_v35.py
 scripts/install_doctor_v35.sh
 scripts/publish_doctor_v35.sh
 tests/test_doctor_v35.py
 tests/browser_doctor_v35.py
 research/DOCTOR_PORTAL_V35.md
)
for i in "${!tracked[@]}"; do
 p="${tracked[$i]}"
 [[ -f "$p" && ! -L "$p" && "$(git hash-object "$p")" == "${expected[$i]}" ]] || { echo "ERROR: Unexpected baseline source: $p"; exit 1; }
done
for p in "${added[@]}"; do [[ ! -e "$p" && ! -L "$p" ]] || { echo "ERROR: Refusing to overwrite $p"; exit 1; }; done
BACKUP="$(mktemp -d /tmp/frailtyscope-v35-original-XXXXXXXX)"
for p in "${tracked[@]}"; do mkdir -p "$BACKUP/$(dirname "$p")"; cp "$p" "$BACKUP/$p"; done
rollback(){
 echo 'ERROR: v0.35 validation failed. Restoring original tracked files, deleting only v0.35 additions.'
 for p in "${tracked[@]}"; do cp "$BACKUP/$p" "$p"; done
 for p in "${added[@]}"; do rm -f -- "$p"; done
}
trap rollback ERR
for p in "${added[@]}"; do mkdir -p "$(dirname "$p")"; cp "$PKG/$p" "$p"; done
.venv/bin/python scripts/patch_doctor_v35.py "$ROOT"
printf '=== Parse Doctor CSS with the Next.js PostCSS dependency ===\n'
(cd web && node -e "const fs=require('fs'); const postcss=require('postcss'); const css=fs.readFileSync('app/doctor-v35.css','utf8'); postcss.parse(css,{from:'app/doctor-v35.css'}); console.log('PASS: Doctor Portal CSS parses successfully')")
printf '=== Complete fixture, research-privacy and Doctor design regressions ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Prior immutable integrity review: READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== TypeScript and production build ===\n'
(cd web && npm run lint && npm run build)
printf '=== Mandatory full desktop/mobile Chromium QA, including Doctor v0.35 ===\n'
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR
printf 'SUCCESS: v0.35 Doctor Portal redesigned and validated LOCALLY. Nothing committed or pushed.\n'
printf 'Tracked source backup: %s\n' "$BACKUP"
