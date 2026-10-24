#!/usr/bin/env bash
# Guarded local install. Does not open private research datasets or clinical model binaries.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='6e8bc71db55e169b75646f1c3953e1fe5c4bba82'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.46 main required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing tracked changes; refusing overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote advanced; do not apply';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/layout.tsx web/app/page.tsx web/app/components/site-header.tsx )
added=( ml/interview_benchmark_v47.py research/NTNU_INTERVIEW_REFOCUS_V47.md scripts/patch_interview_focus_v47.py scripts/install_interview_focus_v47.sh scripts/publish_interview_focus_v47.sh tests/test_interview_focus_v47.py tests/browser_interview_focus_v47.py web/app/components/interview-focus-v47.tsx web/app/data/interview-benchmark-v47.json web/app/interview/page.tsx web/app/admin/interview/page.tsx web/app/interview-focus-v47.css )
for f in "${tracked[@]}";do [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Missing/unsafe tracked $f";exit 1; };done
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: Existing untracked target $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing/unsafe package path $f";exit 1; }
done
BACKUP="$(mktemp -d /tmp/frailtyscope-interview-v47-original-XXXXXXXX)"
for f in "${tracked[@]}";do mkdir -p "$BACKUP/$(dirname "$f")";cp -p -- "$f" "$BACKUP/$f";done
rollback(){
 local status=$?
 trap - ERR INT TERM
 set +e
 echo 'ERROR: Interview reset validation failed; reverting ONLY the reviewed source paths.'
 local failed=0
 for f in "${tracked[@]}";do cp -p -- "$BACKUP/$f" "$f" || failed=1;done
 for f in "${added[@]}";do rm -f -- "$f" || failed=1;done
 [[ "$failed" -eq 0 ]] || echo "ERROR: Incomplete rollback; backup at $BACKUP"
 exit "${status:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_interview_focus_v47.py --root "$ROOT"
bash -n scripts/install_interview_focus_v47.sh
bash -n scripts/publish_interview_focus_v47.sh
PYTHONPATH=. .venv/bin/python -m ml.interview_benchmark_v47 --check
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/interview-focus-v47.css','utf8'));console.log('PASS: Interview CSS parsed')")
echo '=== All source/fixture and historical privacy regressions ==='
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests
echo '=== Historical immutable v0.30 review, READ-ONLY ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Production TypeScript and Next.js build ==='
(cd web && npm run lint && npm run build)
echo '=== Complete desktop/mobile browser QA including interview view ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: Interview-focused dataset/ML/doctor presentation installed LOCALLY; no commit or push, no real prediction enabled.'
echo "Original tracked source backup: $BACKUP"
