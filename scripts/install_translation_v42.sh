#!/usr/bin/env bash
# Source-only, backup-protected v0.42 installer. Does NOT stage, commit, push or score patients.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='990748baa5de15c09a6153de62d7846003d21168'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Expected published v0.41 main baseline'; exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing tracked changes; refusing overwrite'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote main advanced; review new baseline'; exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/components/clinical-workspace.tsx web/app/layout.tsx )
added=(
 ml/model_translation_v42.py
 research/TRANSLATION_AND_PROMOTION_V42.md
 scripts/install_translation_v42.sh
 scripts/patch_translation_v42.py
 scripts/publish_translation_v42.sh
 tests/test_translation_v42.py
 tests/browser_translation_v42.py
 web/app/api/inference/translation/route.ts
 web/app/components/model-translation-v42.tsx
 web/app/data/model-translation-v42.json
 web/app/translation-v42.css
)
for f in "${added[@]}"; do
  [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: Already exists: $f"; exit 1; }
  [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing or unsafe package file: $f"; exit 1; }
done
BACKUP="$(mktemp -d /tmp/frailtyscope-v42-original-XXXXXXXX)"
for f in "${tracked[@]}"; do
  [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe tracked source: $f";exit 1; }
  mkdir -p "$BACKUP/$(dirname "$f")"
  cp -p -- "$f" "$BACKUP/$f"
done
rollback(){
  local code=$?
  trap - ERR INT TERM
  set +e
  echo 'ERROR: v0.42 verification failed. Restoring exact source allowlist.'
  local restore_fail=0
  for f in "${tracked[@]}"; do
    cp -p -- "$BACKUP/$f" "$f" || { echo "ERROR: Could not restore tracked path: $f"; restore_fail=1; }
  done
  for f in "${added[@]}"; do
    rm -f -- "$f" || { echo "ERROR: Could not remove created source: $f"; restore_fail=1; }
  done
  if [[ "$restore_fail" -ne 0 ]]; then echo "ERROR: Incomplete rollback; source backup at $BACKUP"; fi
  exit "${code:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}"; do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f"; done
.venv/bin/python scripts/patch_translation_v42.py --root "$ROOT"
bash -n scripts/install_translation_v42.sh
bash -n scripts/publish_translation_v42.sh
PYTHONPATH=. .venv/bin/python -m ml.model_translation_v42 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/translation-v42.css','utf8'));console.log('PASS: v0.42 CSS parsed')")
echo '=== All Python privacy, scientific and source-contract tests ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
echo '=== Immutable historical integrity READ ONLY ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Next.js types + production build ==='
(cd web && npm run lint && npm run build)
echo '=== Mandatory original and v0.42 Chromium QA, desktop/mobile ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: v0.42 public candidate crosswalk installed and validated locally; clinical predictions blocked. No commit or push.'
echo "Original tracked sources backup: $BACKUP"
