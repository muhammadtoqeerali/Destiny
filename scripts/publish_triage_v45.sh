#!/usr/bin/env bash
# Only public source; explicit uppercase YES needed; never stages completed reviews.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='d2389b44f365b7cbfa5511ee0a02944e5b185b50'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.44 baseline required';exit 1; }
files=( .github/workflows/ci.yml ml/study_evidence_triage_v45.py research/STUDY_EVIDENCE_TRIAGE_V45.md scripts/install_triage_v45.sh scripts/patch_triage_v45.py scripts/publish_triage_v45.sh tests/test_study_evidence_triage_v45.py )
allowed(){ local p; for p in "${files[@]}";do [[ "$1" == "$p" ]] && return 0;done;return 1; }
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Unsafe/missing reviewed path $f";exit 1; };done
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing staged edits';exit 1; }
while IFS= read -r f;do [[ -z "$f" ]] || allowed "$f" || { echo "ERROR: Unreviewed tracked changes $f";exit 1; };done < <(git diff --name-only)
bash -n scripts/install_triage_v45.sh
bash -n scripts/publish_triage_v45.sh
PYTHONPATH=. .venv/bin/python -m ml.study_evidence_triage_v45 --check-template
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq 7 ]] || { echo 'ERROR: Expected exactly seven reviewed source paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unexpected staged path $f";exit 1; };done
git diff --cached --check
echo '=== Exactly seven public/source-only paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'Never stage filled study-team responses, private evidence documents, participant tables, model binaries, credentials, aggregates or unrelated interview files.'
read -r -p 'Publish v0.45 source-only private evidence-response TRIAGE (no approvals or clinical scoring)? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined; nothing pushed';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote advanced; stop';exit 1; }
git commit -m 'feat: add offline-only study evidence response triage without clinical promotion'
git push origin main
echo 'SUCCESS: v0.45 public triage SOURCE published. No filled responses, approvals or patient scoring.'
