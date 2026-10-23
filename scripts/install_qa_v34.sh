#!/usr/bin/env bash
# v0.34 source-only install. Browser suite runs separately before publication.
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='c2bfe9d8e9116ff6441bf304e4574946d3dabf82'
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: main branch required'; exit 1; }
[[ "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected reviewed v0.33 commit'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'ERROR: Unexpected tracked/staged edits'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main moved; review source again'; exit 1; }
(cd "$PKG" && sha256sum -c SHA256SUMS)
tracked=(.github/workflows/ci.yml web/app/components/engine-studio-v33.tsx web/app/layout.tsx)
expected=(0a3abe9ea2d6ceabec1c17ffab2795e812c9b3c2 5483a4c1c637caa4dd55a93a4f7e7aed5f73b51f 0db9f61a7f7ea064ee8588e2a576ad49a2a6e6f7)
new=(web/app/api/status/route.ts web/app/components/release-status-v34.tsx web/app/engine-studio-v34.css scripts/run_browser_qa_v34.sh tests/browser_qa_v34.py tests/test_demo_qa_v34.py scripts/install_qa_v34.sh scripts/publish_qa_v34.sh scripts/patch_qa_v34.py research/DEMO_QA_V34.md)
for i in "${!tracked[@]}"; do
 p="${tracked[$i]}"
 [[ -f "$p" && ! -L "$p" ]] || { echo "ERROR: Missing/unsafe source $p"; exit 1; }
 [[ "$(git hash-object "$p")" == "${expected[$i]}" ]] || { echo "ERROR: Baseline content differs: $p"; exit 1; }
done
for p in "${new[@]}"; do [[ ! -e "$p" && ! -L "$p" ]] || { echo "ERROR: Will not overwrite $p"; exit 1; }; done
BACKUP="$(mktemp -d /tmp/frailtyscope-v34-original-XXXXXXXX)"
for p in "${tracked[@]}"; do mkdir -p "$BACKUP/$(dirname "$p")"; cp "$p" "$BACKUP/$p"; done
rollback(){
 echo 'ERROR: v0.34 installation validation failed. Restoring tracked files and removing only v0.34 additions.'
 for p in "${tracked[@]}"; do cp "$BACKUP/$p" "$p"; done
 for p in "${new[@]}"; do rm -f -- "$p"; done
}
trap rollback ERR
for p in "${new[@]}"; do mkdir -p "$(dirname "$p")"; cp "$PKG/$p" "$p"; done
.venv/bin/python scripts/patch_qa_v34.py "$ROOT"
printf '=== Full synthetic/privacy regression suite ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Read-only private integrity verification ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
printf '=== Next.js TypeScript and production build ===\n'
(cd web && npm run lint && npm run build)
git diff --check
trap - ERR
printf 'SUCCESS: v0.34 source installed, Python and Next.js passed. No push.\n'
printf 'Original tracked source backups: %s\n' "$BACKUP"
printf 'NEXT: Install isolated Playwright browser QA dependency, run scripts/run_browser_qa_v34.sh, then review publication.\n'
