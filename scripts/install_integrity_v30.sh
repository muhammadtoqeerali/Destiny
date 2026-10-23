#!/usr/bin/env bash
set -euo pipefail
ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_SHA='28d3fafa03a8151ff71f498ffbfe3d10b6c0f252'
cd "$ROOT"
[[ "$(git branch --show-current)" == main ]] || { echo 'ERROR: Expected main branch'; exit 1; }
[[ "$(git rev-parse HEAD)" == "$BASE_SHA" ]] || { echo 'ERROR: Source base changed; do not install an out-of-date patch'; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo 'ERROR: Tracked local changes exist; inspect before installation'; exit 1; }
git fetch origin main
[[ "$(git rev-parse origin/main)" == "$BASE_SHA" ]] || { echo 'ERROR: Remote main changed'; exit 1; }
(cd "$PKG" && sha256sum -c SHA256SUMS)
[[ "$(git hash-object web/app/components/decision-quality-v12.tsx)" == '333eb06de5b5a72c054290fc203e682f930de4a4' ]] || {
 echo 'ERROR: Decision-quality source differs from verified GitHub version; do not modify it'; exit 1; }
[[ "$(git hash-object .github/workflows/ci.yml)" == 'adac9a0f8833f69c50af06e2fe7661c4dba8b5d2' ]] || {
 echo 'ERROR: CI source differs from verified GitHub version'; exit 1; }
files=(ml/case_integrity_v30.py research/WORKFLOW_INTEGRITY_V30.md \
 research/cases/WORKFLOW_INTEGRITY_TEMPLATE_V30.json research/cases/nhanes_integrity_v30.json \
 scripts/install_integrity_v30.sh scripts/publish_integrity_v30.sh \
 tests/test_case_integrity_v30.py web/app/components/threshold-sensitivity-chart.tsx)
for file in "${files[@]}"; do
 [[ ! -e "$file" ]] || { echo "ERROR: Existing file; refusing to overwrite: $file"; exit 1; }
done
backup="$(mktemp -d /tmp/frailtyscope-v30-original-XXXXXXXX)"
cp .github/workflows/ci.yml "$backup/ci.yml"
cp web/app/components/decision-quality-v12.tsx "$backup/decision-quality-v12.tsx"
rollback() {
 echo 'ERROR: v0.30 install validation failed; restoring prior tracked source files'
 cp "$backup/ci.yml" .github/workflows/ci.yml
 cp "$backup/decision-quality-v12.tsx" web/app/components/decision-quality-v12.tsx
 for file in "${files[@]}"; do rm -f -- "$file"; done
}
trap rollback ERR
for file in "${files[@]}"; do
 mkdir -p "$(dirname "$file")"
 cp "$PKG/$file" "$file"
done
PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
p=Path('web/app/components/decision-quality-v12.tsx')
s=p.read_text()
needle="import research from '../../public/data/nhanes-decision-quality-v12.json';"
assert s.count(needle)==1, 'Unexpected decision-quality imports'
s=s.replace(needle,needle+"\nimport { ThresholdSensitivityChart } from './threshold-sensitivity-chart';")
start='    <div className="v11-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={report.thresholds}>'
end='</LineChart></ResponsiveContainer></div>'
assert s.count(start)==1, 'Missing legacy threshold chart'
a=s.index(start);b=s.index(end,a)+len(end)
s=s[:a]+'''    <div className="v11-chart" style={{height:'auto',minHeight:280}}>
      <ThresholdSensitivityChart data={report.thresholds} selected={threshold.threshold} mode={mode}/>
    </div>'''+s[b:]
old_import="import {CartesianGrid,Legend,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis,Bar,BarChart} from 'recharts';"
new_import="import {CartesianGrid,Legend,ResponsiveContainer,Tooltip,XAxis,YAxis,Bar,BarChart} from 'recharts';"
assert s.count(old_import)==1, 'Unexpected Recharts imports'
s=s.replace(old_import,new_import)
p.write_text(s)
ci=Path('.github/workflows/ci.yml')
x=ci.read_text();old='tests/test_case_workflow_v29.py';new=old+' tests/test_case_integrity_v30.py'
assert x.count(old)==1 and 'tests/test_case_integrity_v30.py' not in x,'Unexpected CI test list'
ci.write_text(x.replace(old,new))
PY
printf '=== Syntax and fixture/privacy regression ===\n'
bash -n scripts/install_integrity_v30.sh
bash -n scripts/publish_integrity_v30.sh
PYTHONPATH=. .venv/bin/python -m py_compile ml/case_integrity_v30.py tests/test_case_integrity_v30.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests
printf '=== Source-only v0.30 plan and fully invented synthetic smoke test ===\n'
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --plan
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --smoke
printf '=== Web TypeScript and production build ===\n'
if [[ ! -x web/node_modules/.bin/tsc ]]; then (cd web && npm ci); fi
(cd web && npm run lint && npm run build)
git diff --check
trap - ERR
printf 'SUCCESS: v0.30 source installed and synthetic checks passed. No real-data files or private model artifacts accessed.\n'
printf 'Original source backups: %s\n' "$backup"
printf 'NEXT: run v0.30 --audit exactly once, then share audit log before source-only publication.\n'
