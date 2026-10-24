#!/usr/bin/env bash
# Fail-closed public source-only publisher. NEVER commit NHANES raw data or private reports.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BASE='2dc2e87ed15b2c0940e3c6a176bfda5a1c75a8c4'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact v0.47 published baseline required';exit 1; }
files=( .github/workflows/ci.yml ml/public_mobility_v48.py research/PHASE2_PUBLIC_MOBILITY_V48.md scripts/install_public_mobility_v48.sh scripts/patch_public_mobility_v48.py scripts/publish_public_mobility_v48.sh tests/test_public_mobility_v48.py )
allowed(){ local item;for item in "${files[@]}";do [[ "$1" == "$item" ]]&&return 0;done;return 1;}
for f in "${files[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Unsafe/missing source $f";exit 1; };done
[[ -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing staged edits';exit 1; }
while IFS= read -r name;do [[ -z "$name" ]] || allowed "$name" || { echo "ERROR: Unreviewed tracked change $name";exit 1; };done < <(git diff --name-only)
bash -n scripts/install_public_mobility_v48.sh scripts/publish_public_mobility_v48.sh
PYTHONPATH=. .venv/bin/python -m ml.public_mobility_v48 --contract
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
bash scripts/run_browser_qa_v34.sh
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq 7 ]] || { echo 'ERROR: Expected exactly seven reviewed public paths';exit 1; }
for f in "${staged[@]}";do allowed "$f" || { echo "ERROR: Unsafe staged source $f";exit 1; };done
git diff --cached --check
echo '=== REVIEW exactly 7 public source-only paths ==='
git diff --cached --stat
git diff --cached --name-only
echo 'No raw NHANES files, fitted model files, private/participant data, old NHANES mortality data or unrelated interview briefs staged.'
read -r -p 'Publish Phase 2 reproducible public NHANES mobility pipeline SOURCE ONLY? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Declined; nothing pushed';exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: Remote advanced; stop';exit 1; }
git commit -m 'feat: implement new public NHANES mobility ML benchmark for NTNU interview'
git push origin main
echo 'SUCCESS: v0.48 public ML pipeline source published; separate blocked historical case untouched.'
