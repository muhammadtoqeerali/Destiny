#!/usr/bin/env bash
# Exact allowlist, literal YES, no participant data; publishes final interview presentation.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='fd8b0999d03313873328968eb813424b521342b2'
AGG="${FRAILTYSCOPE_PUBLIC_MOBILITY_AGGREGATE:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU-restricted/nhanes_mobility_public/results/mobility_aggregate_v48.json}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Published v0.48 baseline required';exit 1; }
files=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/layout.tsx web/app/components/interview-focus-v47.tsx ml/interview_results_v49.py research/NTNU_INTERVIEW_FINAL_V49.md scripts/install_interview_results_v49.sh scripts/patch_interview_results_v49.py scripts/publish_interview_results_v49.sh tests/test_interview_results_v49.py tests/browser_interview_results_v49.py web/app/components/real-mobility-v49.tsx web/app/data/real-mobility-summary-v49.json web/app/interview-results-v49.css )
allowed(){ local f;for f in "${files[@]}";do [[ "$f" == "$1" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe reviewed file $f";exit 1; };done
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing staged changes not allowed';exit 1; }
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Nonallowlisted tracked edit $f";exit 1; };done < <(git diff --name-only)
PYTHONPATH=. .venv/bin/python -m ml.interview_results_v49 --check-public
PYTHONPATH=. .venv/bin/python -m ml.interview_results_v49 --verify-local "$AGG"
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/interview-results-v49.css','utf8'));console.log('PASS: v0.49 CSS parsed')")
bash -n scripts/install_interview_results_v49.sh scripts/publish_interview_results_v49.sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected exactly 14 reviewed source paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unexpected staged file $f";exit 1; };done
git diff --cached --check
echo '=== Only reviewed PUBLIC aggregate/source paths (14) ==='
git diff --cached --stat
git diff --cached --name-only
echo 'No NHANES participant data, local aggregate report, model binaries, private HUNT/NHATS files, PHI or unrelated interview brief files staged.'
read -r -p 'Publish Phase 3 FINAL NTNU interview presentation, public AGGREGATES ONLY? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; no push';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote advanced; stop';exit 1; }
git commit -m 'feat: complete NTNU interview with separate NHANES mobility evidence and fictional clinician examples'
git push origin main
echo 'SUCCESS: Phase 3 final interview presentation SOURCE PUBLISHED. Three-phase preparation implementation finished, pending hosted CI confirmation.'
