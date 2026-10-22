#!/usr/bin/env bash
set -euo pipefail
ROOT=/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Use main branch'; exit 1; }
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from ml.case_ablation_v14 import sha_json,SCHEMA
cfg=json.loads(Path('research/cases/nhanes_ablation_v14.json').read_text())
p=Path('artifacts/cases')/cfg['case_id']/'ablation_v14'/sha_json(cfg)[:12]/'development_ablation.json'
assert p.is_file(), 'Run workstation development ablation before publishing source'
r=json.loads(p.read_text())
assert r['schema']==SCHEMA and r['dataset_sha256'] and r['n_evaluation_predictions_generated']==0
assert r['selection_or_model_replacement_performed'] is False
assert len(r['comparison'])==len(cfg['variants'])
assert [x['variant'] for x in r['comparison']]==[v['name'] for v in cfg['variants']]
print('PASS: Development-only local ablation finished; no model replacement or evaluation cohort')
PY
files=(.github/workflows/ci.yml ml/case_ablation_v14.py research/cases/nhanes_ablation_v14.json research/cases/ABLATION_TEMPLATE_V14.json research/DEVELOPMENT_ABLATIONS_V14.md scripts/install_ablation_v14.sh scripts/publish_ablation_v14.sh tests/test_case_ablation_v14.py)
# Reject any pre-staged files not explicitly approved.
mapfile -t existing < <(git diff --cached --name-only)
for staged in "${existing[@]}"; do
  approved=false
  for path in "${files[@]}"; do [[ "$staged" == "$path" ]] && approved=true; done
  "$approved" || { echo "ERROR: Unapproved staged file: $staged"; exit 1; }
done
git add -- "${files[@]}"
mapfile -t staged < <(git diff --cached --name-only)
for entry in "${staged[@]}"; do
  approved=false
  for path in "${files[@]}"; do [[ "$entry" == "$path" ]] && approved=true; done
  "$approved" || { echo "ERROR: Unapproved staged file: $entry"; exit 1; }
done
[[ ${#staged[@]} -eq ${#files[@]} ]] || { echo 'ERROR: Incomplete staged source allowlist'; exit 1; }
git diff --cached --check
git diff --cached --stat
printf 'SOURCE ONLY. No participant data, fitted models, local reports, or public JSON.\n'
read -r -p 'Publish v0.14 development-ablation source? Type uppercase YES: ' answer
[[ "$answer" == 'YES' ]] || { echo 'Publication declined'; exit 1; }
git fetch origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo 'ERROR: GitHub main has moved'; exit 1; }
git commit -m 'feat: development-only missingness and feature ablation contract'
git push origin main
printf 'SUCCESS: v0.14 source-only release pushed. Local evaluation never published.\n'
