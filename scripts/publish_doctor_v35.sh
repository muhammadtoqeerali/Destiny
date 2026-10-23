#!/usr/bin/env bash
# Reviewed v0.35 source-only publication. Never stage private data/other untracked files.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='d8c43e380d0b3296440c3eeb3ce5e7331e59ac97'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected reviewed v0.34 main baseline'; exit 1; }
files=(
 .github/workflows/ci.yml
 tests/test_demo_qa_v34.py
 tests/browser_qa_v34.py
 research/DOCTOR_PORTAL_V35.md
 scripts/install_doctor_v35.sh
 scripts/patch_doctor_v35.py
 scripts/publish_doctor_v35.sh
 scripts/run_browser_qa_v34.sh
 tests/browser_doctor_v35.py
 tests/test_doctor_v35.py
 web/app/components/clinical-workspace.tsx
 web/app/components/doctor-visuals-v35.tsx
 web/app/doctor-v35.css
 web/app/layout.tsx
)
allowed(){ local p; for p in "${files[@]}"; do [[ "$1" == "$p" ]] && return 0; done; return 1; }
for p in "${files[@]}"; do [[ -f "$p" && ! -L "$p" ]] || { echo "ERROR: Missing/unsafe approved path: $p"; exit 1; }; done
while IFS= read -r p; do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unexpected tracked change: $p"; exit 1; }; done < <(git diff --name-only)
while IFS= read -r p; do [[ -z "$p" ]] || allowed "$p" || { echo "ERROR: Unexpected staged change: $p"; exit 1; }; done < <(git diff --cached --name-only)
printf '=== Parse Doctor CSS with the Next.js PostCSS dependency ===\n'
(cd web && node -e "const fs=require('fs'); const postcss=require('postcss'); const css=fs.readFileSync('app/doctor-v35.css','utf8'); postcss.parse(css,{from:'app/doctor-v35.css'}); console.log('PASS: Doctor Portal CSS parses successfully')")
printf '=== Full source/fixture/privacy regression ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Immutable private v0.30 review, READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== Next.js production build and types ===\n'
(cd web && npm run lint && npm run build)
printf '=== Mandatory desktop/mobile Chromium QA ===\n'
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected 14 exact approved source paths'; exit 1; }
for p in "${staged[@]}"; do allowed "$p" || { echo "ERROR: Unsafe staged path: $p"; exit 1; }; done
git diff --cached --check
printf '=== Review exactly these source changes ===\n'
git diff --cached --stat
git diff --cached --name-only
printf 'No participant data, historical public aggregates, immutable private audits, models or interview-brief files staged.\n'
read -r -p 'Publish v0.35 Norwegian-inspired Doctor Portal redesign? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; nothing pushed'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote moved; fresh review required'; exit 1; }
git commit -m 'feat: accessible Nordic-inspired Doctor Portal research design'
git push origin main
printf 'SUCCESS: v0.35 approved source-only Doctor Portal release published. Research datasets unchanged.\n'
