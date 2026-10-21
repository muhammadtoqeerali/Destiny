"""Idempotent exact-structure patch for v0.11 Admin / CSS / CI."""
from pathlib import Path
import argparse


def replace_once(s,a,b):
    if s.count(a)!=1:raise ValueError('Expected unique source anchor not found: '+a[:80])
    return s.replace(a,b)


def admin(s):
    if 'DecisionQualityV12' in s:return s
    s=replace_once(s,"import { EvidenceWorkbenchV11 } from './evidence-workbench-v11';",
        "import { EvidenceWorkbenchV11 } from './evidence-workbench-v11';\nimport { DecisionQualityV12 } from './decision-quality-v12';")
    s=replace_once(s,"| 'Benchmark' | 'Deep analysis';","| 'Benchmark' | 'Deep analysis' | 'Decision quality';")
    s=replace_once(s,"'Benchmark','Deep analysis'];","'Benchmark','Deep analysis','Decision quality'];")
    s=replace_once(s,"{tab==='Deep analysis'&&<EvidenceWorkbenchV11/>}",
        "{tab==='Deep analysis'&&<EvidenceWorkbenchV11/>}\n   {tab==='Decision quality'&&<DecisionQualityV12/>}")
    return s


def layout(s):
    if "import './nhanes-v12.css';" in s:return s
    return replace_once(s,"import './nhanes-v11.css';",
        "import './nhanes-v11.css';\nimport './nhanes-v12.css';")


def ci(s):
    if 'tests/test_decision_quality_v12.py' in s:return s
    s=replace_once(s,'tests/test_clean_model_reload_v112.py',
       'tests/test_clean_model_reload_v112.py tests/test_decision_quality_v12.py')
    s=replace_once(s,"'nhanes-case-audit-v11.json'}","'nhanes-case-audit-v11.json','nhanes-decision-quality-v12.json'}")
    before="              else:\n                  assert obj['counts']['total']>=2000"
    after="""              elif fname=='nhanes-decision-quality-v12.json':
                  assert obj['schema']=='FRAILTYSCOPE_PUBLIC_DECISION_QUALITY_V12'
                  assert obj['counts']=={'validation':292,'evaluation':1257,'events':246}
                  assert len(obj['thresholds'])==14
                  assert all(x['n']>=100 and min(x['events'],x['n']-x['events'])>=20 for x in obj['subgroups'])
                  assert all(x['n']>=50 and min(x['events'],x['n']-x['events'])>=10 for x in obj['calibration_bands'])
              else:
                  assert obj['counts']['total']>=2000"""
    return replace_once(s,before,after)


def patch_project(root:Path):
    paths={root/'web/app/components/multi-outcome-admin.tsx':admin,
           root/'web/app/layout.tsx':layout,root/'.github/workflows/ci.yml':ci}
    for path,fn in paths.items():
        orig=path.read_text();new=fn(orig)
        if new!=orig:path.write_text(new)
        print('PASS:',path.relative_to(root),'v0.12 patch')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',default='.');a=p.parse_args()
    patch_project(Path(a.project).resolve())
