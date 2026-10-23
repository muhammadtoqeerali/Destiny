#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='19e3b1f0db79695894464ec1685c68734cb08a80'
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Require main branch'; exit 1; }
[[ "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected published v0.31 HEAD; review instead of overwriting'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Tracked modifications or pre-staged changes; review first'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main moved; do not overwrite'; exit 1; }
(cd "$PKG" && sha256sum -c SHA256SUMS)
tracked=(
 .github/workflows/ci.yml
 tests/test_web_reporting_v31.py
 web/app/admin/actions.ts
 web/app/admin/page.tsx
 web/app/admin/login/page.tsx
 web/app/lib/auth.ts
 web/app/components/multi-outcome-admin.tsx
 web/app/layout.tsx
)
added=(
 web/app/components/engine-studio-v32.tsx
 web/app/engine-studio-v32.css
 scripts/patch_demo_v32.py
 scripts/install_demo_v32.sh
 scripts/publish_demo_v32.sh
 scripts/check_live_demo_v32.sh
 tests/test_demo_studio_v32.py
 research/DEMO_ENGINE_STUDIO_V32.md
)
for p in "${added[@]}"; do [[ ! -e "$p" ]] || { echo "ERROR: Refusing to replace existing $p"; exit 1; }; done
for p in "${tracked[@]}"; do [[ -f "$p" ]] || { echo "ERROR: Missing tracked source $p"; exit 1; }; done
BACKUP="$(mktemp -d /tmp/frailtyscope-v32-original-XXXXXXXX)"
for p in "${tracked[@]}"; do mkdir -p "$BACKUP/$(dirname "$p")"; cat "$p" > "$BACKUP/$p"; done
rollback(){
  echo 'ERROR: v0.32 installation failed. Restoring tracked files and deleting only new approved source paths.'
  for p in "${tracked[@]}"; do cat "$BACKUP/$p" > "$p"; done
  for p in "${added[@]}"; do rm -f -- "$p"; done
}
trap rollback ERR
for p in "${added[@]}"; do
 mkdir -p "$(dirname "$p")"
 cat "$PKG/$p" > "$p"
done
.venv/bin/python scripts/patch_demo_v32.py "$ROOT"
printf '=== Full source-only fixture and privacy suite ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify v0.30 immutable PRIVATE integrity review, read-only ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== Next.js TypeScript and production build ===\n'
(cd web && npm run lint && npm run build)
git diff --check
trap - ERR
printf 'SUCCESS: v0.32 public-demo access and Engine Studio installed locally; no push or research-data use.\n'
printf 'Original tracked source backup: %s\n' "$BACKUP"
printf 'NEXT: Review installer results, then review publisher allowlist before fresh YES.\n'
