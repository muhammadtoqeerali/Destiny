#!/usr/bin/env bash
# v0.43 guarded local installation; no real model binary, private data, or Git push.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='96e3886254f9050d1ad035a954253abf6e7d0b2e'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.42 main required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Unexpected tracked edits; refusing overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Published baseline advanced';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/components/clinical-workspace.tsx web/app/layout.tsx )
added=( ml/artifact_acceptance_v43.py research/cases/synthetic_artifact_candidate_v43.json research/ARTIFACT_ACCEPTANCE_V43.md scripts/install_artifact_v43.sh scripts/patch_artifact_v43.py scripts/publish_artifact_v43.sh tests/test_artifact_v43.py tests/browser_artifact_v43.py web/app/api/inference/artifacts/route.ts web/app/components/artifact-acceptance-v43.tsx web/app/data/artifact-acceptance-v43.json web/app/artifact-v43.css )
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: Added file already exists $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing/symlinked package source $f";exit 1; }
done
BACKUP="$(mktemp -d /tmp/frailtyscope-v43-original-XXXXXXXX)"
for f in "${tracked[@]}";do
 [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Unsafe tracked source $f";exit 1; }
 mkdir -p "$BACKUP/$(dirname "$f")"; cp -p "$f" "$BACKUP/$f"
done
rollback(){
 local exitcode=$?
 trap - ERR INT TERM
 set +e
 echo 'ERROR: v0.43 validation failed; restoring only reviewed source paths.'
 local failed=0
 for f in "${tracked[@]}";do cp -p "$BACKUP/$f" "$f" || failed=1; done
 for f in "${added[@]}";do rm -f -- "$f" || failed=1; done
 [[ "$failed" == 0 ]] || echo "ERROR: Incomplete rollback; backup at $BACKUP"
 exit "${exitcode:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}";do mkdir -p "$(dirname "$f")"; cp "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_artifact_v43.py --root "$ROOT"
bash -n scripts/install_artifact_v43.sh
bash -n scripts/publish_artifact_v43.sh
PYTHONPATH=. .venv/bin/python -m ml.artifact_acceptance_v43 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/artifact-v43.css','utf8'));console.log('PASS CSS')")
echo '=== Full privacy and research source-regression suite ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Next.js strict types and production build ==='
(cd web && npm run lint && npm run build)
echo '=== Mandatory desktop/mobile browser acceptance through v0.43 ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: v0.43 fictional artifact acceptance dossier installed and validated LOCALLY. Clinical predictions blocked; no commit or push.'
echo "Tracked original backup: $BACKUP"
