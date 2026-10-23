#!/usr/bin/env bash
# v0.43 guarded publication; synthetic/public source only; no clinical scoring permission.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='96e3886254f9050d1ad035a954253abf6e7d0b2e'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Required published v0.42 baseline';exit 1; }
files=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/components/clinical-workspace.tsx web/app/layout.tsx ml/artifact_acceptance_v43.py research/cases/synthetic_artifact_candidate_v43.json research/ARTIFACT_ACCEPTANCE_V43.md scripts/install_artifact_v43.sh scripts/patch_artifact_v43.py scripts/publish_artifact_v43.sh tests/test_artifact_v43.py tests/browser_artifact_v43.py web/app/api/inference/artifacts/route.ts web/app/components/artifact-acceptance-v43.tsx web/app/data/artifact-acceptance-v43.json web/app/artifact-v43.css )
allowed(){ local item; for item in "${files[@]}";do [[ "$1" == "$item" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Unsafe/missing approved file $f";exit 1; };done
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing staged edits; refuse';exit 1; }
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unreviewed tracked edit $f";exit 1; };done < <(git diff --name-only)
bash -n scripts/install_artifact_v43.sh
bash -n scripts/publish_artifact_v43.sh
PYTHONPATH=. .venv/bin/python -m ml.artifact_acceptance_v43 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/artifact-v43.css','utf8'));console.log('PASS CSS')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected exactly 16 source-only files';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unexpected staged file $f";exit 1; };done
git diff --cached --check
echo '=== Exact 16 source-only publication paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'NO real model files, participant rows, private NHANES/HUNT, historical aggregate exports or unrelated interview briefs staged.'
read -r -p 'Publish v0.43 synthetic artifact metadata and denied clinical promotion? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; nothing pushed.';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: GitHub main advanced; review required';exit 1; }
git commit -m 'feat: add fail-closed synthetic artifact acceptance and model provenance gates'
git push origin main
echo 'SUCCESS: v0.43 synthetic artifact acceptance published. No patient inference.'
