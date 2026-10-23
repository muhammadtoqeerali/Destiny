#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='19e3b1f0db79695894464ec1685c68734cb08a80'
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Publishing requires exact reviewed v0.31 base'; exit 1; }
files=(
 .github/workflows/ci.yml
 tests/test_web_reporting_v31.py
 web/app/admin/actions.ts
 web/app/admin/page.tsx
 web/app/admin/login/page.tsx
 web/app/lib/auth.ts
 web/app/components/multi-outcome-admin.tsx
 web/app/layout.tsx
 web/app/components/engine-studio-v32.tsx
 web/app/engine-studio-v32.css
 scripts/patch_demo_v32.py
 scripts/install_demo_v32.sh
 scripts/publish_demo_v32.sh
 scripts/check_live_demo_v32.sh
 tests/test_demo_studio_v32.py
 research/DEMO_ENGINE_STUDIO_V32.md
)
allowed(){ for path in "${files[@]}"; do [[ "$1" == "$path" ]] && return 0; done; return 1; }
for p in "${files[@]}"; do [[ -f "$p" ]] || { echo "ERROR: Missing approved source: $p"; exit 1; }; done
while IFS= read -r p; do [[ -z "$p" ]] && continue; allowed "$p" || { echo "ERROR: Tracked modification outside allowlist: $p"; exit 1; }; done < <(git diff --name-only)
while IFS= read -r p; do [[ -z "$p" ]] && continue; allowed "$p" || { echo "ERROR: Pre-staged path outside allowlist: $p"; exit 1; }; done < <(git diff --cached --name-only)
printf '=== Full fixture and privacy regression ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Immutable v0.30 evidence: READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== Next.js production build ===\n'
(cd web && npm run lint && npm run build)
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Unexpected staged count'; exit 1; }
for p in "${staged[@]}"; do allowed "$p" || { echo "ERROR: Unsafe staged path $p"; exit 1; }; done
git diff --cached --check
printf '=== Proposed source-only changes; manually inspect before consent ===\n'
git diff --cached --stat
printf '=== Exact source paths ===\n'
git diff --cached --name-only
printf 'PUBLIC-DEMO ONLY: no participant data, private audits, trained models, outputs or public aggregate JSON staged.\n'
read -r -p 'Publish v0.32 public aggregate demo access and synthetic Engine Studio? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; no commit/push'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote main moved; review required'; exit 1; }
git commit -m 'feat: public aggregate demo access and guided synthetic ML engine studio'
git push origin main
printf 'SUCCESS: v0.32 reviewed source-only demonstration published. Private research remains local.\n'
