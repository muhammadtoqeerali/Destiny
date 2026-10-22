#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Use main branch'; exit 1; }
[[ -f ml/case_preprocess_selection_v15.py ]] || { echo 'ERROR: Install v0.15 first'; exit 1; }
printf '=== Source regression tests; no NHANES fitting ===\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Verify sealed local development report; NEVER publish it ===\n'
PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
import json, math
from ml.case_preprocess_selection_v15 import SCHEMA,canonical_sha
root=Path('.')
config=json.loads((root/'research/cases/nhanes_preprocess_selection_v15.json').read_text())
name=config['case_id']
path=root/'artifacts'/'cases'/name/'preprocess_selection_v15'/canonical_sha(config)[:12]/'nested_development.json'
assert path.is_file(), 'Run workstation-only nested study first; result is missing'
r=json.loads(path.read_text())
assert r['schema']==SCHEMA and r['report_type']=='LOCAL_EXPLORATORY_NESTED_DEVELOPMENT_ONLY'
assert r['v15_protocol_sha256']==canonical_sha(config)
assert r['n_evaluation_predictions_generated']==0
assert r['model_replaced'] is False and r['public_export'] is False
assert len(r['repeated_nested'])==len(config['outer_seeds'])
assert len(r['fold_selection_details'])==len(config['outer_seeds'])*config['outer_folds']
assert set(r['fold_selection_counts']).issubset(config['variants'])
for rec in r['repeated_nested']:
    assert math.isfinite(rec['reference_loss']) and math.isfinite(rec['selected_loss'])
print('PASS: v0.15 nested evidence exists locally and is development-only')
PY
files=(
  .github/workflows/ci.yml
  ml/case_preprocess_selection_v15.py
  research/cases/nhanes_preprocess_selection_v15.json
  research/cases/PREPROCESS_SELECTION_TEMPLATE_V15.json
  research/NESTED_PREPROCESS_SELECTION_V15.md
  scripts/install_preprocess_v15.sh
  scripts/publish_preprocess_v15.sh
  tests/test_preprocess_selection_v15.py
)
mapfile -t existing < <(git diff --cached --name-only)
for p in "${existing[@]}"; do
  ok=false
  for allowed in "${files[@]}"; do [[ "$p" == "$allowed" ]] && ok=true; done
  "$ok" || { echo "ERROR: Unapproved staged path $p"; exit 1; }
done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
[[ "${#staged[@]}" -eq "${#files[@]}" ]] || { echo 'ERROR: Staging manifest incomplete'; exit 1; }
for p in "${staged[@]}"; do
  ok=false
  for allowed in "${files[@]}"; do [[ "$p" == "$allowed" ]] && ok=true; done
  "$ok" || { echo "ERROR: Unapproved staged path $p"; exit 1; }
done
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No models, respondent data, predictions, or local evaluation reports.\n'
read -r -p 'Push v0.15 source-only to GitHub main? Type uppercase YES: ' answer
[[ "$answer" == YES ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: origin/main moved'; exit 1; }
git commit -m 'feat: nested preprocessing selection with development-only validation'
git push origin main
printf 'SUCCESS: v0.15 source-only released; local evidence remains private.\n'
