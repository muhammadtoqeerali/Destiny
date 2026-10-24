#!/usr/bin/env bash
# Last interview phase: public aggregate-only data + screen clarity; no raw NHANES/HUNT records.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='fd8b0999d03313873328968eb813424b521342b2'
AGG="${FRAILTYSCOPE_PUBLIC_MOBILITY_AGGREGATE:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU-restricted/nhanes_mobility_public/results/mobility_aggregate_v48.json}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.48 main required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Uncommitted tracked modifications present';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote advanced, re-review baseline';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml scripts/run_browser_qa_v34.sh web/app/layout.tsx web/app/components/interview-focus-v47.tsx )
added=( ml/interview_results_v49.py research/NTNU_INTERVIEW_FINAL_V49.md scripts/install_interview_results_v49.sh scripts/patch_interview_results_v49.py scripts/publish_interview_results_v49.sh tests/test_interview_results_v49.py tests/browser_interview_results_v49.py web/app/components/real-mobility-v49.tsx web/app/data/real-mobility-summary-v49.json web/app/interview-results-v49.css )
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: New v0.49 path already exists $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing/unsafe source in ZIP $f";exit 1; }
done
for f in "${tracked[@]}";do
 [[ -f "$f" && ! -L "$f" ]] || { echo "ERROR: Unsafe tracked source: $f";exit 1; }
done
# Preflight MUST execute bundled source BY PATH. The existing repository's `ml`
# package would otherwise hide the not-yet-installed module. No tracked edits yet.
.venv/bin/python "$BUNDLE/ml/interview_results_v49.py" --root "$BUNDLE" --check-public
.venv/bin/python "$BUNDLE/ml/interview_results_v49.py" --root "$BUNDLE" --verify-local "$AGG"
BACKUP="$(mktemp -d /tmp/frailtyscope-v49-original-XXXXXXXX)"
for f in "${tracked[@]}";do mkdir -p "$BACKUP/$(dirname "$f")";cp -- "$f" "$BACKUP/$f";done
rollback(){
 local code=$?
 trap - ERR INT TERM
 set +e
 echo 'ERROR: v0.49 regression failed; restore only the 14 reviewed source paths'
 local fail=0
 for f in "${tracked[@]}";do cp -- "$BACKUP/$f" "$f" || fail=1;done
 for f in "${added[@]}";do rm -f -- "$f" || fail=1;done
 [[ "$fail" -eq 0 ]] || echo "ERROR: Restore incomplete; backup remains $BACKUP"
 exit "${code:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_interview_results_v49.py --root "$ROOT"
bash -n scripts/install_interview_results_v49.sh scripts/publish_interview_results_v49.sh
PYTHONPATH=. .venv/bin/python -m ml.interview_results_v49 --check-public
PYTHONPATH=. .venv/bin/python -m ml.interview_results_v49 --verify-local "$AGG"
(cd web && node -e "require('postcss').parse(require('fs').readFileSync('app/interview-results-v49.css','utf8'));console.log('PASS: v0.49 CSS parsed')")
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
echo '=== Immutable historical source integrity (verify ONLY) ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
(cd web && npm run lint && npm run build)
echo '=== Complete desktop/mobile production browser QA ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: Final NTNU interview presentation INSTALLED AND VERIFIED LOCALLY; no commit/push, no patient records or fitted clinical models.'
echo "Original tracked source backup: $BACKUP"
