#!/usr/bin/env bash
# Exact eight-path source-only publication, explicit affirmative human approval.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='d4d8f0084908f5b757d42bdcd9777be9baab92be'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact v0.45 main baseline required';exit 1; }
files=(
 .github/workflows/ci.yml
 ml/study_activation_v46.py
 research/cases/study_activation_workplan_v46.json
 research/RESEARCH_ACTIVATION_V46.md
 scripts/install_activation_v46.sh
 scripts/patch_activation_v46.py
 scripts/publish_activation_v46.sh
 tests/test_study_activation_v46.py
)
allowed(){ local path;for path in "${files[@]}";do [[ "$1" == "$path" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Unsafe/missing allowlisted path: $f";exit 1; };done
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing staged edits';exit 1; }
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unapproved tracked change: $f";exit 1; };done < <(git diff --name-only)
bash -n scripts/install_activation_v46.sh
bash -n scripts/publish_activation_v46.sh
PYTHONPATH=. .venv/bin/python -m ml.study_evidence_triage_v45 --check-template
PYTHONPATH=. .venv/bin/python -m ml.study_activation_v46 --check-public-plan
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq 8 ]] || { echo 'ERROR: Expected exactly eight public-only paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unexpected staged path: $f";exit 1; };done
git diff --cached --check
echo '=== Exact eight reviewed public/source-only paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'No completed reviews, ticket IDs, patient data, real model binaries, research private files, credentials or unrelated interview scripts staged.'
read -r -p 'Publish v0.46 public/redacted study activation planning source only, with ALL clinical approvals denied? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; nothing pushed';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: GitHub main advanced; manual review required';exit 1; }
git commit -m 'feat: generate redacted study activation plan and review dependencies'
git push origin main
echo 'SUCCESS: v0.46 action planning published. No private evidence or clinical scoring enabled.'
