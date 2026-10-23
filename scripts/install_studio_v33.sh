#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='399b9c100089d4eca5e6de60d2f31a1cfbe740d5'
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main'; exit 1; }
[[ "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected reviewed published v0.32 baseline'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Unreviewed tracked/staged changes; stop'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main has moved; review'; exit 1; }
(cd "$PKG" && sha256sum -c SHA256SUMS)
tracked=(
 .github/workflows/ci.yml
 tests/test_demo_studio_v32.py
 web/app/admin/login/page.tsx
 web/app/admin/page.tsx
 web/app/components/multi-outcome-admin.tsx
 web/app/layout.tsx
)
added=(
 web/app/components/engine-studio-v33.tsx
 web/app/engine-studio-v33.css
 scripts/patch_studio_v33.py
 scripts/install_studio_v33.sh
 scripts/publish_studio_v33.sh
 tests/test_engine_studio_v33.py
 research/ENGINE_STUDIO_V33.md
)
for p in "${tracked[@]}"; do [[ -f "$p" && ! -L "$p" ]] || { echo "ERROR: Missing/unsafe tracked file $p"; exit 1; }; done
for p in "${added[@]}"; do [[ ! -e "$p" && ! -L "$p" ]] || { echo "ERROR: Refusing to overwrite $p"; exit 1; }; done
BACKUP="$(mktemp -d /tmp/frailtyscope-v33-original-XXXXXXXX)"
for p in "${tracked[@]}"; do mkdir -p "$BACKUP/$(dirname "$p")"; cat "$p" > "$BACKUP/$p"; done
rollback(){
  echo 'ERROR: Installation validation failed. Restoring original tracked files and removing v0.33 new files.'
  for p in "${tracked[@]}"; do cat "$BACKUP/$p" > "$p"; done
  for p in "${added[@]}"; do rm -f -- "$p"; done
}
trap 'rollback' ERR
for p in "${added[@]}"; do mkdir -p "$(dirname "$p")"; cat "$PKG/$p" > "$p"; done
.venv/bin/python scripts/patch_studio_v33.py "$ROOT"
printf '=== Complete synthetic / privacy regression suite ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== v0.30 private integrity review, READ ONLY ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== TypeScript and production web build ===\n'
(cd web && npm run lint && npm run build)
git diff --check
trap - ERR
printf 'SUCCESS: v0.33 visual studio installed and verified locally. No commit or push.\n'
printf 'Original source backups: %s\n' "$BACKUP"
printf 'Inspect staged file allowlist in separate publisher before fresh YES.\n'
