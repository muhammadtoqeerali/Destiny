#!/usr/bin/env bash
# Source-only, fail-closed v0.45 installer; private evidence files are never read.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='d2389b44f365b7cbfa5511ee0a02944e5b185b50'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Published v0.44 main is required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing tracked changes; refuse overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote advanced; re-review required';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml )
added=( ml/study_evidence_triage_v45.py research/STUDY_EVIDENCE_TRIAGE_V45.md scripts/install_triage_v45.sh scripts/patch_triage_v45.py scripts/publish_triage_v45.sh tests/test_study_evidence_triage_v45.py )
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: New v0.45 source already exists: $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing/unsafe bundled source $f";exit 1; }
done
[[ -f .github/workflows/ci.yml && ! -L .github/workflows/ci.yml ]] || { echo 'ERROR: Unsafe CI source';exit 1; }
BACKUP="$(mktemp -d /tmp/frailtyscope-v45-original-XXXXXXXX)"
mkdir -p "$BACKUP/.github/workflows"
cp -p -- .github/workflows/ci.yml "$BACKUP/.github/workflows/ci.yml"
rollback(){
 local code=$?
 trap - ERR INT TERM
 set +e
 echo 'ERROR: v0.45 validation failed. Reverting only reviewed v0.45 source paths.'
 local failed=0
 cp -p -- "$BACKUP/.github/workflows/ci.yml" .github/workflows/ci.yml || failed=1
 for f in "${added[@]}";do rm -f -- "$f" || failed=1;done
 [[ "$failed" -eq 0 ]] || echo "ERROR: Rollback incomplete; backed-up CI source at $BACKUP"
 exit "${code:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}";do mkdir -p "$(dirname "$f")"; cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_triage_v45.py --root "$ROOT"
bash -n scripts/install_triage_v45.sh
bash -n scripts/publish_triage_v45.sh
PYTHONPATH=. .venv/bin/python -m ml.study_evidence_triage_v45 --check-template
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_study_evidence_triage_v45.py
echo '=== Full prior source/privacy fixture regression ==='
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests
echo '=== Read-only historical v0.30 integrity ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Next.js strict types and production build ==='
(cd web && npm run lint && npm run build)
echo '=== Unchanged mandatory desktop/mobile browser suite (v0.34–v0.44) ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: v0.45 private evidence triage installed and fully validated LOCALLY. No commit or push, no approvals inferred.'
echo "Tracked CI source backup: $BACKUP"
