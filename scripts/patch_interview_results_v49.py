#!/usr/bin/env python3
"""Exact-anchor patch of published v0.48; preserve all historical research/QA code."""
from __future__ import annotations
import argparse
from pathlib import Path

PATCHES={
 '.github/workflows/ci.yml':[
  ('      - name: Check v0.47 generated interview benchmark\n',
   '      - name: Check v0.49 aggregate presentation privacy and consistency\n'
   '        run: PYTHONPATH=. python -m ml.interview_results_v49 --check-public\n'
   '      - name: Validate final NTNU interview presentation contracts\n'
   '        run: python -m pytest -q tests/test_interview_results_v49.py\n'
   '      - name: Check v0.47 generated interview benchmark\n'),
 ],
 'scripts/run_browser_qa_v34.sh':[
  ('FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_interview_focus_v47.py\n',
   'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_interview_focus_v47.py\n'
   'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_interview_results_v49.py\n'),
 ],
 'web/app/layout.tsx':[
  ("import './interview-focus-v47.css';\n",
   "import './interview-focus-v47.css';\nimport './interview-results-v49.css';\n"),
 ],
 'web/app/components/interview-focus-v47.tsx':[
  ("import historical from '../../public/data/nhanes-refinement.json';\n",
   "import historical from '../../public/data/nhanes-refinement.json';\n"
   "import {RealMobilityDoctorV49,RealMobilityAdminV49} from './real-mobility-v49';\n"),
  ('  <div className="if-mini-stats"><div><span>Generated cohort</span>',
   '  <RealMobilityDoctorV49/>\n  <div className="if-mini-stats"><div><span>Generated cohort</span>'),
  ("type Cohort='synthetic'|'nhanes'|'nhats'|'share'|'hunt';",
   "type Cohort='mobility'|'synthetic'|'nhanes'|'nhats'|'share'|'hunt';"),
  ("const datasets:[Cohort,string,string][]=[['synthetic'",
   "const datasets:[Cohort,string,string][]=[['mobility','NHANES 2015–2018 mobility','Real public data'],['synthetic'"),
  ("const [dataset,setDataset]=useState<Cohort>('synthetic');",
   "const [dataset,setDataset]=useState<Cohort>('mobility');"),
  ("  {dataset==='synthetic'&&",
   "  {dataset==='mobility'&&<RealMobilityAdminV49/>}\n  {dataset==='synthetic'&&"),
 ],
}

def transform(path:str,content:str)->str:
    if path not in PATCHES:raise ValueError('Unallowlisted patch path '+path)
    for old,new in PATCHES[path]:
        if content.count(old)!=1 or (new!=old and new in content):
            raise ValueError('Missing/ambiguous v0.48 anchor or double application: '+path)
        content=content.replace(old,new,1)
    return content

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    root=p.parse_args().root.resolve()
    changes={}
    for path in PATCHES:
        f=root/path
        if not f.is_file() or f.is_symlink():raise ValueError('Missing/unsafe tracked file '+path)
        changes[f]=transform(path,f.read_text(encoding='utf8'))
    for path,new in changes.items():
        path.write_text(new,encoding='utf8')
        print('PATCHED:',path.relative_to(root))
    print('PASS: Final interview research display added; historic models and patient gate unchanged')
if __name__=='__main__':main()
