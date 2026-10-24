#!/usr/bin/env bash
# Guarded source-only installer; does not download public data or read old/private models.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='2dc2e87ed15b2c0940e3c6a176bfda5a1c75a8c4'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.47 main is required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Tracked edits; refusing overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote advanced; stop';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml )
added=( ml/public_mobility_v48.py research/PHASE2_PUBLIC_MOBILITY_V48.md scripts/install_public_mobility_v48.sh scripts/patch_public_mobility_v48.py scripts/publish_public_mobility_v48.sh tests/test_public_mobility_v48.py )
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: Existing target $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing/unsafe bundle path $f";exit 1; }
done
[[ -f .github/workflows/ci.yml && ! -L .github/workflows/ci.yml ]] || { echo 'ERROR: Unsafe tracked CI'; exit 1; }
BACKUP="$(mktemp -d /tmp/frailtyscope-v48-original-XXXXXXXX)"
mkdir -p "$BACKUP/.github/workflows"
cp -p -- .github/workflows/ci.yml "$BACKUP/.github/workflows/ci.yml"
rollback(){
 local code=$?
 trap - ERR INT TERM
 set +e
 echo 'ERROR: v0.48 source validation failed; restoring only reviewed paths'
 local failed=0
 cp -p -- "$BACKUP/.github/workflows/ci.yml" .github/workflows/ci.yml || failed=1
 for f in "${added[@]}";do rm -f -- "$f" || failed=1;done
 [[ "$failed" == 0 ]] || echo "ERROR: Incomplete rollback; CI source backup at $BACKUP"
 exit "${code:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_public_mobility_v48.py --root "$ROOT"
bash -n scripts/install_public_mobility_v48.sh scripts/publish_public_mobility_v48.sh
PYTHONPATH=. .venv/bin/python -m ml.public_mobility_v48 --contract
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_public_mobility_v48.py
echo '=== Original full privacy/science/source-contract suite ==='
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests
echo '=== Read-only historical immutable v0.30 source integrity ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Next.js type checks + production build, no UI changes ==='
(cd web && npm run lint && npm run build)
echo '=== Original mandatory desktop/mobile browser suite v0.34-v0.47 ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: Phase 2 source-only public-mobility ML pipeline installed locally. NO datasets downloaded by installer; NO commit/push.'
echo "Backed-up original CI source: $BACKUP"
