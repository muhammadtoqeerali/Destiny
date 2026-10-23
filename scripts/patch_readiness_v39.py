#!/usr/bin/env python3
"""Strict reviewed v0.38 -> v0.39 source-only patch. No data or artifact modification."""
import argparse
import subprocess
from pathlib import Path

BASE='5b77d2ebab4f742926981a55ca2473f422f1fbc9'
EXPECTED={
 '.github/workflows/ci.yml':'acb46132c9e746127ab143975062f3089902b46a',
 'scripts/run_browser_qa_v34.sh':'ed24741a7cb890c674547f57d07add2ed2e86e99',
 'web/app/components/clinical-workspace.tsx':'f89fb4737df68427e32d2958e61d0e61e71b78a3',
 'web/app/layout.tsx':'b159e46cececbc981d8e5a15fadce688422530e7',
}

def once(text,original,new,path):
    n=text.count(original)
    if n!=1:raise ValueError(f'Expected one exact anchor in {path}: found {n}; {original[:140]!r}')
    return text.replace(original,new,1)

def transform(path,text):
    sentinels={
      '.github/workflows/ci.yml':'tests/test_inference_readiness_v39.py',
      'scripts/run_browser_qa_v34.sh':'tests/browser_readiness_v39.py',
      'web/app/components/clinical-workspace.tsx':'<ReadinessEvidenceV39/>',
      'web/app/layout.tsx':"import './inference-v39.css';",
    }
    if sentinels[path] in text:raise ValueError('Already applied v0.39: '+path)
    if path=='.github/workflows/ci.yml':
        text=once(text,'tests/test_platform_v38.py',
          'tests/test_platform_v38.py tests/test_inference_readiness_v39.py',path)
        text=once(text,'      - name: Public payload validation',
          '      - name: Verify documentary inference readiness\n        run: PYTHONPATH=. python -m ml.inference_readiness_v39 --check\n      - name: Public payload validation',path)
    elif path=='scripts/run_browser_qa_v34.sh':
        text=once(text,'ROOT="${FRAILTYSCOPE_ROOT:-/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU}"',
          'ROOT="${FRAILTYSCOPE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"',path)
        line='FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_platform_v38.py'
        text=once(text,line,line+'\nFRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_readiness_v39.py',path)
    elif path=='web/app/components/clinical-workspace.tsx':
        text=once(text,"import {ClinicalOutcomeRegistryV38, FictionalMultiOutcomeLabV38} from './multioutcome-lab-v38';",
          "import {ClinicalOutcomeRegistryV38, FictionalMultiOutcomeLabV38} from './multioutcome-lab-v38';\nimport {ReadinessEvidenceV39} from './inference-evidence-v39';",path)
        text=once(text,'   <ClinicalOutcomeRegistryV38/>',
          '   <ClinicalOutcomeRegistryV38/>\n   <ReadinessEvidenceV39/>',path)
    elif path=='web/app/layout.tsx':
        text=once(text,"import './inference-v38.css';",
          "import './inference-v38.css';\nimport './inference-v39.css';",path)
    else:raise ValueError('Unexpected patch path: '+path)
    return text

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--root',required=True)
    a.add_argument('--fixture',action='store_true',help='Fixture-only mock source check')
    args=a.parse_args()
    root=Path(args.root).resolve()
    if not args.fixture:
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        if sha!=BASE:raise SystemExit('ERROR: Incorrect reviewed v0.38 baseline')
    changed={}
    for relative,expected in EXPECTED.items():
        path=root/relative
        if not path.is_file() or path.is_symlink():raise SystemExit('Missing/unsafe approved source: '+relative)
        if not args.fixture:
            blob=subprocess.check_output(['git','hash-object',relative],cwd=root,text=True).strip()
            if blob!=expected:raise SystemExit(f'ERROR: Reviewed source blob mismatch: {relative} {blob}')
        changed[path]=transform(relative,path.read_text(encoding='utf-8'))
    for path,new in changed.items():
        path.write_text(new,encoding='utf-8')
        print('PATCHED:',path.relative_to(root))
    print('PASS: v0.39 documentary evidence and GitHub CI root patch. No participant data touched.')
if __name__=='__main__':main()
