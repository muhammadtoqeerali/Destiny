#!/usr/bin/env bash
# Guarded, source-only publication; require explicit uppercase YES.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='6e8bc71db55e169b75646f1c3953e1fe5c4bba82'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.46 baseline required';exit 1; }
files=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/layout.tsx web/app/page.tsx web/app/components/site-header.tsx ml/interview_benchmark_v47.py research/NTNU_INTERVIEW_REFOCUS_V47.md scripts/patch_interview_focus_v47.py scripts/install_interview_focus_v47.sh scripts/publish_interview_focus_v47.sh tests/test_interview_focus_v47.py tests/browser_interview_focus_v47.py web/app/components/interview-focus-v47.tsx web/app/data/interview-benchmark-v47.json web/app/interview/page.tsx web/app/admin/interview/page.tsx web/app/interview-focus-v47.css )
allowed(){ local item;for item in "${files[@]}";do [[ "$1" == "$item" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe source $f";exit 1; };done
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Unexpected staged paths';exit 1; }
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unreviewed tracked change $f";exit 1; };done < <(git diff --name-only)
bash -n scripts/install_interview_focus_v47.sh
bash -n scripts/publish_interview_focus_v47.sh
PYTHONPATH=. .venv/bin/python -m ml.interview_benchmark_v47 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/interview-focus-v47.css','utf8'));console.log('PASS: Interview CSS parsed')")
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Expected exact 17 source paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Disallowed staged file $f";exit 1; };done
git diff --cached --check
echo '=== Exact reviewed interview-focused source paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'Only GENERATED fictional per-person examples and existing separately labeled historical aggregates appear. No HUNT/NHATS/SHARE participant rows or clinical model binaries.'
read -r -p 'Publish interview-focused research demonstration, preserving legacy work and blocked clinical inference? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; no push';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote changed; stop';exit 1; }
git commit -m 'feat: refocus FrailtyScope on NTNU interview, isolated dataset benchmarks and clear clinician story'
git push origin main
echo 'SUCCESS: Interview-focused Phase I published; historical real-data and patient inference remain blocked.'
