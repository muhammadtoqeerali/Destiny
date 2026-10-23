#!/usr/bin/env python3
"""Exact, fail-closed source patch against reviewed v0.37; never touches data artifacts."""
import argparse
import subprocess
from pathlib import Path

BASE='79698cf9874814a2f8d9154b26bc68d51bf3bae8'
EXPECTED={
  '.github/workflows/ci.yml':'76a97707f3b42de9e63c956f2ee1401508f06065',
  'web/app/components/clinical-workspace.tsx':'4eb61f678f49a91427a1c8172ee403230111d66c',
  'web/app/layout.tsx':'ce535c122b487e04c0947801ed6f98742f269861',
  'scripts/run_browser_qa_v34.sh':'310d6fddbd24db74e2f71d0f100bb249c3d9146f',
  'tests/browser_doctor_v35.py':'5baded6a85fe7340bf5e103c0ec3eb3582fa5194',
  'tests/browser_doctor_v36.py':'d8e766ace27bd32909f026812f14534e9ec40bee',
  'tests/browser_inference_v37.py':'ffaf39a00c7a84c75881fdf7438e690115bda637',
  'tests/test_demo_qa_v34.py':'c2c14eb305db086af7e9ea45a71e359e82381b60',
  'tests/test_doctor_v35.py':'76034d39c8701cd8288c58427594ac691cb8c8ec',
}

def patch(text,needle,replacement,path):
    count=text.count(needle)
    if count!=1:raise ValueError(f'Expected 1 exact anchor in {path}, observed {count}: {needle!r}')
    return text.replace(needle,replacement,1)

def transform(path,text):
    # Explicitly reject a second patch even when an original replacement anchor remains.
    sentinel={
      'web/app/components/clinical-workspace.tsx':'ClinicalOutcomeRegistryV38',
      'web/app/layout.tsx':"import './inference-v38.css';",
      'scripts/run_browser_qa_v34.sh':'tests/browser_platform_v38.py',
      '.github/workflows/ci.yml':'tests/test_platform_v38.py',
      'tests/browser_doctor_v35.py':'FRAILTYSCOPE_QA_CHROMIUM',
      'tests/browser_doctor_v36.py':'FRAILTYSCOPE_QA_CHROMIUM',
      'tests/browser_inference_v37.py':'FRAILTYSCOPE_QA_CHROMIUM',
      'tests/test_demo_qa_v34.py':"'FRAILTYSCOPE_QA_CHROMIUM'",
      'tests/test_doctor_v35.py':"'FRAILTYSCOPE_QA_CHROMIUM'",
    }[path]
    if sentinel in text:raise ValueError('v0.38 has already been applied to '+path)
    if path=='web/app/components/clinical-workspace.tsx':
        text=patch(text,"import {InferenceReadinessV37, FictionalScoringLabV37} from './inference-readiness-v37';",
           "import {InferenceReadinessV37, FictionalScoringLabV37} from './inference-readiness-v37';\nimport {ClinicalOutcomeRegistryV38, FictionalMultiOutcomeLabV38} from './multioutcome-lab-v38';",path)
        text=patch(text,"   <InferenceReadinessV37 profile={profile} onExplore={()=>setPage('Model evidence')}/>",
          "   <InferenceReadinessV37 profile={profile} onExplore={()=>setPage('Model evidence')}/>\n   <ClinicalOutcomeRegistryV38/>",path)
        text=patch(text,"     <FictionalScoringLabV37/>",
          "     <FictionalScoringLabV37/>\n     <FictionalMultiOutcomeLabV38/>",path)
    elif path=='web/app/layout.tsx':
        text=patch(text,"import './inference-v37.css';","import './inference-v37.css';\nimport './inference-v38.css';",path)
    elif path=='scripts/run_browser_qa_v34.sh':
        line='FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_inference_v37.py'
        text=patch(text,line,line+'\nFRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_platform_v38.py',path)
    elif path=='.github/workflows/ci.yml':
        # Avoid the Playwright CDN failure: the GitHub-hosted Ubuntu image ships Google Chrome.
        text=patch(text,'      - run: python -m playwright install chromium',
             '      - name: Verify preinstalled GitHub runner Chrome\n        run: test -x /usr/bin/google-chrome && /usr/bin/google-chrome --version',path)
        text=patch(text,'          FRAILTYSCOPE_QA_PYTHON: python',
             '          FRAILTYSCOPE_QA_PYTHON: python\n          FRAILTYSCOPE_QA_CHROMIUM: /usr/bin/google-chrome',path)
        text=patch(text,'tests/test_runtime_gate_v37.py',
             'tests/test_runtime_gate_v37.py tests/test_platform_v38.py',path)
    elif path.startswith('tests/browser_'):
        if path.endswith('v35.py'): name='pw'
        elif path.endswith('v36.py'): name='p'
        else: name='playwright'
        before=f'browser={name}.chromium.launch(headless=True)'
        after=f"browser={name}.chromium.launch(headless=True,executable_path=os.environ.get('FRAILTYSCOPE_QA_CHROMIUM') or None)"
        text=patch(text,before,after,path)
    elif path=='tests/test_demo_qa_v34.py':
        text=patch(text,"'python -m playwright install chromium'","'FRAILTYSCOPE_QA_CHROMIUM'",path)
    elif path=='tests/test_doctor_v35.py':
        text=patch(text,"assert 'python -m playwright install chromium' in ci", "assert 'FRAILTYSCOPE_QA_CHROMIUM' in ci",path)
        text=patch(text,'assert "\'python -m playwright install chromium\'" in prior_regression',
             'assert "\'FRAILTYSCOPE_QA_CHROMIUM\'" in prior_regression',path)
    else:raise ValueError('Unapproved path '+path)
    return text

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--fixture',action='store_true',help='Test only: accept source snippets, never used by installer')
    args=parser.parse_args()
    root=Path(args.root).resolve()
    if not args.fixture:
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        if head!=BASE:raise SystemExit(f'ERROR: Expected exact v0.37 HEAD {BASE}, received {head}')
    rewritten={}
    for relative,digest in EXPECTED.items():
        dest=root/relative
        if not dest.is_file() or dest.is_symlink():raise SystemExit('ERROR: Missing/unsafe source '+relative)
        if not args.fixture:
            actual=subprocess.check_output(['git','hash-object',relative],cwd=root,text=True).strip()
            if actual!=digest:raise SystemExit(f'ERROR: Source SHA differs from reviewed GitHub v0.37: {relative}, {actual}')
        original=dest.read_text(encoding='utf-8')
        rewritten[dest]=transform(relative,original)
    for path,contents in rewritten.items():
        path.write_text(contents,encoding='utf-8')
        print('PATCHED:',path.relative_to(root))
    print('PASS: exact v0.38 browser, synthetic model UI and CI patch. No research artifacts changed.')

if __name__=='__main__':main()
