#!/usr/bin/env bash
# FrailtyScope v0.46: atomic local-only source release, no private evidence or clinical inference.
set -Eeuo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE='d4d8f0084908f5b757d42bdcd9777be9baab92be'
cd "$ROOT"
[[ "$(git branch --show-current)" == main && "$(git rev-parse HEAD)" == "$BASE" ]] || { echo 'ERROR: Exact published v0.45 main required';exit 1; }
[[ -z "$(git diff --name-only)" && -z "$(git diff --cached --name-only)" ]] || { echo 'ERROR: Existing tracked edits; no overwrite';exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE" ]] || { echo 'ERROR: Remote baseline advanced; stop';exit 1; }
(cd "$BUNDLE" && sha256sum -c SHA256SUMS)
tracked=( .github/workflows/ci.yml )
added=(
 ml/study_activation_v46.py
 research/cases/study_activation_workplan_v46.json
 research/RESEARCH_ACTIVATION_V46.md
 scripts/install_activation_v46.sh
 scripts/patch_activation_v46.py
 scripts/publish_activation_v46.sh
 tests/test_study_activation_v46.py
)
for f in "${added[@]}";do
 [[ ! -e "$f" && ! -L "$f" ]] || { echo "ERROR: v0.46 target already exists: $f";exit 1; }
 [[ -f "$BUNDLE/$f" && ! -L "$BUNDLE/$f" ]] || { echo "ERROR: Missing/unsafe packaged source $f";exit 1; }
done
[[ -f .github/workflows/ci.yml && ! -L .github/workflows/ci.yml ]] || { echo 'ERROR: Unsafe existing CI source';exit 1; }
BACKUP="$(mktemp -d /tmp/frailtyscope-v46-original-XXXXXXXX)"
mkdir -p "$BACKUP/.github/workflows"
cp -p -- .github/workflows/ci.yml "$BACKUP/.github/workflows/ci.yml"
rollback(){
 local code=$?
 trap - ERR INT TERM
 set +e
 echo 'ERROR: v0.46 validation failed. Reverting only the reviewed eight paths.'
 local failed=0
 cp -p -- "$BACKUP/.github/workflows/ci.yml" .github/workflows/ci.yml || failed=1
 for f in "${added[@]}";do rm -f -- "$f" || failed=1;done
 [[ "$failed" == 0 ]] || echo "ERROR: Incomplete rollback; source backup: $BACKUP"
 exit "${code:-1}"
}
trap rollback ERR
trap 'false' INT TERM
for f in "${added[@]}";do mkdir -p "$(dirname "$f")";cp -- "$BUNDLE/$f" "$f";done
.venv/bin/python scripts/patch_activation_v46.py --root "$ROOT"
bash -n scripts/install_activation_v46.sh
bash -n scripts/publish_activation_v46.sh
PYTHONPATH=. .venv/bin/python -m ml.study_evidence_triage_v45 --check-template
PYTHONPATH=. .venv/bin/python -m ml.study_activation_v46 --check-public-plan
echo '=== Compatibility checks v0.41–v0.46, public/synthetic fixtures only ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q \
 tests/test_study_activation_v46.py tests/test_study_evidence_triage_v45.py \
 tests/test_handoff_v44.py tests/test_artifact_v43.py tests/test_translation_v42.py tests/test_validation_v41.py
echo '=== Full research/privacy source regression ==='
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
echo '=== Immutable historical review READ ONLY ==='
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
echo '=== Strict types and production build ==='
(cd web && npm run lint && npm run build)
echo '=== Unchanged mandatory desktop/mobile browser suite ==='
bash scripts/run_browser_qa_v34.sh
git diff --check
trap - ERR INT TERM
echo 'SUCCESS: v0.46 redacted research action plan installed and validated LOCALLY. No commit, push or clinical approval.'
echo "Verified original CI source backup: $BACKUP"
