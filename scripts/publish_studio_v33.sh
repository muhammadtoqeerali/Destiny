#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='399b9c100089d4eca5e6de60d2f31a1cfbe740d5'
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main'; exit 1; }
[[ "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected reviewed v0.32 baseline'; exit 1; }
files=(
 .github/workflows/ci.yml
 tests/test_demo_studio_v32.py
 web/app/admin/login/page.tsx
 web/app/admin/page.tsx
 web/app/components/multi-outcome-admin.tsx
 web/app/layout.tsx
 web/app/components/engine-studio-v33.tsx
 web/app/engine-studio-v33.css
 scripts/patch_studio_v33.py
 scripts/install_studio_v33.sh
 scripts/publish_studio_v33.sh
 tests/test_engine_studio_v33.py
 research/ENGINE_STUDIO_V33.md
)
allowed(){ for x in "${files[@]}"; do [[ "$1" == "$x" ]] && return 0; done; return 1; }
for p in "${files[@]}"; do [[ -f "$p" && ! -L "$p" ]] || { echo "ERROR: Missing/unsafe approved file: $p"; exit 1; }; done
while IFS= read -r p; do [[ -z "$p" ]] && continue; allowed "$p" || { echo "ERROR: Unexpected modified path $p"; exit 1; }; done < <(git diff --name-only)
while IFS= read -r p; do [[ -z "$p" ]] && continue; allowed "$p" || { echo "ERROR: Unexpected staged path $p"; exit 1; }; done < <(git diff --cached --name-only)
printf '=== Full synthetic/privacy regressions ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Private integrity review READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== Web TypeScript & production build ===\n'
(cd web && npm run lint && npm run build)
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected 13 approved staged source paths'; exit 1; }
for p in "${staged[@]}"; do allowed "$p" || { echo "ERROR: Unsafe staged path $p"; exit 1; }; done
git diff --cached --check
printf '=== Reviewed source-only proposal ===\n'
git diff --cached --stat
printf '=== Exact staged file list ===\n'
git diff --cached --name-only
printf 'NO research data, public aggregate JSON, private reviews, participant records or model binaries staged.\n'
read -r -p 'Publish v0.33 Engine Studio redesign and remove on-screen passcode text? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; no commit/push'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote branch changed; review required'; exit 1; }
git commit -m 'feat: redesigned interactive research engine studio and discreet demo sign-in'
git push origin main
printf 'SUCCESS: v0.33 reviewed website source published; private evidence remains local.\n'
