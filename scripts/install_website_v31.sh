#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='a50bc58b4a36dd7e441e2b29ffba6ed992ac34b4'
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: main branch required'; exit 1; }
[[ "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected published v0.30 HEAD; inspect repository before continuing'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Dirty tracked tree or pre-staged changes; review manually'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main has moved; do not overwrite'; exit 1; }
(cd "$PKG" && sha256sum -c SHA256SUMS)
tracked=(
 .github/workflows/ci.yml
 web/app/components/clinical-workspace.tsx
 web/app/components/decision-quality-v12.tsx
 web/app/components/evidence-workbench-v11.tsx
 web/app/components/multi-outcome-admin.tsx
 web/app/components/site-header.tsx
 web/app/globals.css
 web/app/lib/auth.ts
)
new=(
 web/app/components/research-boundary-notice.tsx
 scripts/patch_website_v31.py
 scripts/install_website_v31.sh
 scripts/publish_website_v31.sh
 tests/test_web_reporting_v31.py
 research/WEBSITE_REPORTING_SAFETY_V31.md
)
for p in "${new[@]}"; do [[ ! -e "$p" ]] || { echo "ERROR: Refusing overwrite of pre-existing $p"; exit 1; }; done
BACKUP="$(mktemp -d /tmp/frailtyscope-v31-original-XXXXXXXX)"
for p in "${tracked[@]}"; do mkdir -p "$BACKUP/$(dirname "$p")"; cat "$p" > "$BACKUP/$p"; done
rollback() {
  echo 'ERROR: v0.31 install failed. Restoring pre-install tracked sources; no publication made.'
  for p in "${tracked[@]}"; do cat "$BACKUP/$p" > "$p"; done
  for p in "${new[@]}"; do rm -f -- "$p"; done
}
trap rollback ERR
for p in "${new[@]}"; do
  mkdir -p "$(dirname "$p")"
  cat "$PKG/$p" > "$p"
done
.venv/bin/python scripts/patch_website_v31.py "$ROOT"
printf '=== Complete fixture/privacy and source-only website reporting regressions ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Immutable v0.30 integrity review: READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== Next.js TypeScript and production build ===\n'
(cd web && npm run lint && npm run build)
git diff --check
trap - ERR
printf 'SUCCESS: v0.31 source corrections installed and validated. Nothing committed or pushed.\n'
printf 'Original source backups: %s\n' "$BACKUP"
printf 'NEXT: Set strong Vercel auth environment variables, verify the publisher allowlist, then publish with fresh YES.\n'
