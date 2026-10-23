#!/usr/bin/env bash
# Reviewed source-only publisher, explicit uppercase YES required; no patient data or private model access.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='04a857c769552ee477f859b3b616f70c592da36c'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Published v0.43 baseline required';exit 1; }
files=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/components/clinical-workspace.tsx web/app/layout.tsx ml/study_handoff_v44.py research/STUDY_TEAM_HANDOFF_V44.md research/templates/STUDY_TEAM_EVIDENCE_REQUEST_V44.csv scripts/install_handoff_v44.sh scripts/patch_handoff_v44.py scripts/publish_handoff_v44.sh tests/browser_handoff_v44.py tests/test_handoff_v44.py web/app/api/inference/handoff/route.ts web/app/components/study-handoff-v44.tsx web/app/data/study-handoff-v44.json web/app/study-handoff-v44.css )
allowed(){ local item; for item in "${files[@]}";do [[ "$1" == "$item" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Unsafe/missing source: $f";exit 1; };done
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Staged edits exist; aborting';exit 1; }
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unreviewed tracked change: $f";exit 1; };done < <(git diff --name-only)
bash -n scripts/install_handoff_v44.sh
bash -n scripts/publish_handoff_v44.sh
PYTHONPATH=. .venv/bin/python -m ml.study_handoff_v44 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/study-handoff-v44.css','utf8'));console.log('PASS: v0.44 CSS parsed')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected exactly 16 allowlisted paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unsafe staged path $f";exit 1; };done
git diff --cached --check
echo '=== Review exact 16 source-only paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'No NHANES/HUNT participant records, private reviews, clinical model binaries, historical aggregate exports, completed approval documents or unrelated interview-brief files staged.'
read -r -p 'Publish v0.44 blank study-team evidence handoff and deny-by-default research readiness? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; no push performed.';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote advanced; manual review required';exit 1; }
git commit -m 'feat: add reproducible study-team evidence handoff and approval-request matrix'
git push origin main
echo 'SUCCESS: v0.44 public study-team request packet published. No approvals inferred or patient inference enabled.'
