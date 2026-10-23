#!/usr/bin/env bash
# Source-only local installation on exactly published v0.43; never opens private research data.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='04a857c769552ee477f859b3b616f70c592da36c'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.43 main baseline required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Tracked changes exist; refusing overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote advanced; do not apply package';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/components/clinical-workspace.tsx web/app/layout.tsx )
added=( ml/study_handoff_v44.py research/STUDY_TEAM_HANDOFF_V44.md research/templates/STUDY_TEAM_EVIDENCE_REQUEST_V44.csv scripts/install_handoff_v44.sh scripts/patch_handoff_v44.py scripts/publish_handoff_v44.sh tests/browser_handoff_v44.py tests/test_handoff_v44.py web/app/api/inference/handoff/route.ts web/app/components/study-handoff-v44.tsx web/app/data/study-handoff-v44.json web/app/study-handoff-v44.css )
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: v0.44 target already exists: $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Package missing/unsafe file: $f";exit 1; }
done
BACKUP="$(mktemp -d /tmp/frailtyscope-v44-original-XXXXXXXX)"
for f in "${tracked[@]}";do
 [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Unsafe tracked source: $f";exit 1; }
 mkdir -p "$BACKUP/$(dirname "$f")";cp -p -- "$f" "$BACKUP/$f"
done
rollback(){
 local result=$?
 trap - ERR INT TERM
 set +e
 echo 'ERROR: v0.44 validation failed; restoring only exact reviewed v0.44 paths.'
 local failed=0
 for f in "${tracked[@]}";do cp -p -- "$BACKUP/$f" "$f" || failed=1;done
 for f in "${added[@]}";do rm -f -- "$f" || failed=1;done
 [[ "$failed" == 0 ]] || echo "ERROR: Incomplete restore, source backup remains: $BACKUP"
 exit "${result:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_handoff_v44.py --root "$ROOT"
bash -n scripts/install_handoff_v44.sh
bash -n scripts/publish_handoff_v44.sh
PYTHONPATH=. .venv/bin/python -m ml.study_handoff_v44 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/study-handoff-v44.css','utf8'));console.log('PASS: v0.44 CSS parsed')")
echo '=== Entire source/privacy research regression suite ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
echo '=== Read-only immutable v0.30 historical integrity ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Next.js strict lint and production build ==='
(cd web && npm run lint && npm run build)
echo '=== Mandatory desktop/mobile browser suites v0.34-v0.44 ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: v0.44 public study-team handoff installed and validated LOCALLY. No clinical scoring, commit or push.'
echo "Original tracked source backup: $BACKUP"
