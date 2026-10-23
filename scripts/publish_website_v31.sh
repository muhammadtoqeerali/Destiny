#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='a50bc58b4a36dd7e441e2b29ffba6ed992ac34b4'
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Must publish from the exact reviewed v0.30 base'; exit 1; }
files=(
 .github/workflows/ci.yml
 web/app/components/clinical-workspace.tsx
 web/app/components/decision-quality-v12.tsx
 web/app/components/evidence-workbench-v11.tsx
 web/app/components/multi-outcome-admin.tsx
 web/app/components/research-boundary-notice.tsx
 web/app/components/site-header.tsx
 web/app/globals.css
 web/app/lib/auth.ts
 scripts/patch_website_v31.py
 scripts/install_website_v31.sh
 scripts/publish_website_v31.sh
 tests/test_web_reporting_v31.py
 research/WEBSITE_REPORTING_SAFETY_V31.md
)
allowed() { for path in "${files[@]}"; do [[ "$1" == "$path" ]] && return 0; done; return 1; }
for p in "${files[@]}"; do [[ -f "$p" ]] || { echo "ERROR: Missing approved path $p"; exit 1; }; done
while IFS= read -r p; do [[ -z "$p" ]] && continue; allowed "$p" || { echo "ERROR: Modified tracked path outside allowlist: $p"; exit 1; }; done < <(git diff --name-only)
while IFS= read -r p; do [[ -z "$p" ]] && continue; allowed "$p" || { echo "ERROR: Pre-staged path outside allowlist: $p"; exit 1; }; done < <(git diff --cached --name-only)
printf '=== Synthetic/privacy/source-only regression ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify prior PRIVATE v0.30 immutable audit, read-only ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== Web TypeScript and production build ===\n'
(cd web && npm run lint && npm run build)
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Unexpected number of staged paths'; exit 1; }
for p in "${staged[@]}"; do allowed "$p" || { echo "ERROR: Unsafe staged path: $p"; exit 1; }; done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. Historical public aggregate JSON unchanged; no participant tables, models, predictions or private audits staged.\n'
read -r -p 'Publish v0.31 historical reporting and admin auth safety corrections? Type uppercase YES: ' response
[[ "$response" == YES ]] || { echo 'Publication declined. NO commit or push.'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main moved; review changes before push'; exit 1; }
git commit -m 'fix: clarify historical NHANES reporting and fail-closed admin authentication'
git push origin main
printf 'SUCCESS: v0.31 source-only website reporting corrections published. No research data altered.\n'
