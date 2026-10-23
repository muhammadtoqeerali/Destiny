#!/usr/bin/env python3
"""Exact reviewed source-only v0.39 -> v0.40 patch; no real data use."""
import argparse
import subprocess
from pathlib import Path

BASE='bbef3c6aac5565a8e31b395238b60ae4be59805a'
EXPECTED={
 '.github/workflows/ci.yml':'26077e20e6327b0ce3bde0b09824f7c489bace04',
 'scripts/run_browser_qa_v34.sh':'194080b61b971685b49c2e2028709953b3282752',
 'web/app/components/clinical-workspace.tsx':'ce36224b6c807485438051e6db927dabb727fbf9',
 'web/app/layout.tsx':'a288c2eb8ba531a0a91e7ec0428760ba02f6b1bb',
 'tests/browser_inference_v37.py':'9bad905a096f37d060a07b5e4e07b5ceb1b24fa0',
}

def once(source,old,new,path):
    count=source.count(old)
    if count!=1:raise ValueError(f'Source anchor mismatch in {path}: expected 1, got {count}: {old[:90]!r}')
    return source.replace(old,new,1)

def transform(path,source):
    sentinel={
      '.github/workflows/ci.yml':'tests/test_serving_v40.py',
      'scripts/run_browser_qa_v34.sh':'tests/browser_serving_v40.py',
      'web/app/components/clinical-workspace.tsx':'<SyntheticServerV40/>',
      'web/app/layout.tsx':"import './inference-serving-v40.css';",
      'tests/browser_inference_v37.py':'# v0.40 legacy contract: GET-only fictional fixture allowed',
    }[path]
    if sentinel in source:raise ValueError('Already applied v0.40: '+path)
    if path=='.github/workflows/ci.yml':
        return once(source,'tests/test_inference_readiness_v39.py',
            'tests/test_inference_readiness_v39.py tests/test_serving_v40.py',path)
    if path=='scripts/run_browser_qa_v34.sh':
        marker='FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_readiness_v39.py'
        return once(source,marker,marker+'\nFRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_serving_v40.py',path)
    if path=='web/app/components/clinical-workspace.tsx':
        source=once(source,"import {ReadinessEvidenceV39} from './inference-evidence-v39';",
           "import {ReadinessEvidenceV39} from './inference-evidence-v39';\nimport {SyntheticServerV40} from './synthetic-server-v40';",path)
        return once(source,'     <FictionalMultiOutcomeLabV38/>',
           '     <FictionalMultiOutcomeLabV38/>\n     <SyntheticServerV40/>',path)
    if path=='web/app/layout.tsx':
        return once(source,"import './inference-v39.css';",
              "import './inference-v39.css';\nimport './inference-serving-v40.css';",path)
    if path=='tests/browser_inference_v37.py':
        return once(source,
            "                assert not any(path.endswith('/api/predict') or '/api/inference' in path for _,path in requests)",
            "                # v0.40 legacy contract: GET-only fictional fixture allowed.\n                # Keep the v0.37 api/predict denial while allowing precisely one fixed synthetic GET.\n                assert not any(url.endswith('/api/predict') for _,url in requests),(label,requests)\n                synthetic_reference=BASE+'/api/inference/synthetic?fixture=fictional_reference'\n                assert all(method=='GET' and url==synthetic_reference\n                           for method,url in requests if '/api/inference' in url),(label,requests)",path)
    raise ValueError('Unapproved source path')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',required=True)
    ap.add_argument('--fixture',action='store_true')
    a=ap.parse_args();root=Path(a.root).resolve()
    if not a.fixture:
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        if head!=BASE:raise SystemExit('ERROR: Exact published v0.39 main required')
    changed={}
    for p,expected in EXPECTED.items():
        f=root/p
        if not f.is_file() or f.is_symlink():raise SystemExit('ERROR: Missing/unsafe file '+p)
        if not a.fixture:
            sha=subprocess.check_output(['git','hash-object',p],cwd=root,text=True).strip()
            if sha!=expected:raise SystemExit(f'ERROR: Unexpected reviewed source blob {p}: {sha}')
        changed[f]=transform(p,f.read_text(encoding='utf-8'))
    for f,new in changed.items():
        f.write_text(new,encoding='utf-8');print('PATCHED:',f.relative_to(root))
    print('PASS: v0.40 restricted synthetic serving patch, no clinical data or model artifacts modified.')
if __name__=='__main__':main()
