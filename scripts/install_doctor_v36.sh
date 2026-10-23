#!/usr/bin/env bash
# v0.36 source-only install; preserve all unrelated files and original case integrity.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='332cbf33d3102420e3ee1e1e414884fb8ae99323'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected reviewed published v0.35 main'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Unreviewed tracked or staged modifications'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main moved; review again'; exit 1; }
(cd "$PKG" && sha256sum -c SHA256SUMS)
tracked=(
 web/app/components/clinical-workspace.tsx
 web/app/layout.tsx
 tests/browser_doctor_v35.py
 tests/browser_qa_v34.py
 scripts/run_browser_qa_v34.sh
 .github/workflows/ci.yml
)
new=(
 web/app/components/doctor-journey-v36.tsx
 web/app/doctor-journey-v36.css
 tests/browser_doctor_v36.py
 tests/test_doctor_journey_v36.py
 scripts/patch_doctor_v36.py
 scripts/install_doctor_v36.sh
 scripts/publish_doctor_v36.sh
 research/DOCTOR_JOURNEY_V36.md
)
expected=(
 8939aa42055f9ca3b80eb9fbd1dd129bd2275f7e
 9637de72793ed247360698addc897cf1d0ddee04
 c7501ae1acd7a78e2794fd6c2fd2a7a31a61116c
 fd63308d90e7426488cf2e4cd952d3ae03342ad8
 25dc1fb37f08c7740295732b0b1b8f392d6a1c7f
 6fffc1a54c4ac6a4dc8b30939515e9f768a43012
)
for i in "${!tracked[@]}"; do
 p="${tracked[$i]}"
 [[ -f "$p" && ! -L "$p" ]] || { echo "ERROR: Missing or symlink tracked file $p"; exit 1; }
 [[ "$(git hash-object "$p")" == "${expected[$i]}" ]] || { echo "ERROR: Source baseline differs $p"; exit 1; }
done
for p in "${new[@]}"; do [[ ! -e "$p" && ! -L "$p" ]] || { echo "ERROR: Refusing overwrite $p"; exit 1; }; done
BACKUP="$(mktemp -d /tmp/frailtyscope-v36-original-XXXXXXXX)"
for p in "${tracked[@]}"; do mkdir -p "$BACKUP/$(dirname "$p")"; cp "$p" "$BACKUP/$p"; done
rollback(){
 echo 'ERROR: v0.36 validation failed. Restoring the 6 tracked files and deleting only 8 new source files.'
 for p in "${tracked[@]}"; do cp "$BACKUP/$p" "$p"; done
 for p in "${new[@]}"; do rm -f -- "$p"; done
}
trap rollback ERR
for p in "${new[@]}"; do mkdir -p "$(dirname "$p")"; cp "$PKG/$p" "$p"; done
.venv/bin/python scripts/patch_doctor_v36.py "$ROOT"
printf '=== Parse v0.36 animation CSS using deployed PostCSS ===\n'
(cd web && node -e "const fs=require('fs');const postcss=require('postcss'); postcss.parse(fs.readFileSync('app/doctor-journey-v36.css','utf8'),{from:'doctor-journey-v36.css'}); console.log('PASS: CSS parsed')")
printf '=== Full synthetic/privacy tests ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Historical private integrity verification, READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== TypeScript and Next.js production build ===\n'
(cd web && npm run lint && npm run build)
printf '=== Mandatory v0.34 + v0.35 + v0.36 desktop/mobile Chromium QA ===\n'
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR
echo 'SUCCESS: v0.36 live-descriptive Doctor journey installed and verified locally. No commit or push.'
echo "Source backup: $BACKUP"
