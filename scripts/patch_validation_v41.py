#!/usr/bin/env python3
"""v0.41 exact, source-only patch: never accesses research data or model binaries."""
import argparse
from pathlib import Path

PATCHES={
 '.github/workflows/ci.yml':[
    ('tests/test_serving_v40.py\n', 'tests/test_serving_v40.py tests/test_validation_v41.py\n'),
    ('      - name: Public payload validation\n',
     '      - name: Verify v0.41 public research and invented holdback receipt\n'
     '        run: PYTHONPATH=. python -m ml.research_validation_v41 --check\n'
     '      - name: Public payload validation\n'),
 ],
 'scripts/run_browser_qa_v34.sh':[
    ('FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_serving_v40.py\n',
     'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_serving_v40.py\n'
     'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_validation_v41.py\n'),
 ],
 'web/app/components/clinical-workspace.tsx':[
    ("import {SyntheticServerV40} from './synthetic-server-v40';\n",
     "import {SyntheticServerV40} from './synthetic-server-v40';\n"
     "import {ValidationGateV41} from './validation-gate-v41';\n"),
    ('     <SyntheticServerV40/>\n',
     '     <SyntheticServerV40/>\n     <ValidationGateV41/>\n'),
 ],
 'web/app/layout.tsx':[
    ("import './inference-serving-v40.css';\n",
     "import './inference-serving-v40.css';\nimport './validation-v41.css';\n"),
 ],
}

def transform(name:str, source:str)->str:
    if name not in PATCHES:raise ValueError('Unexpected patch target: '+name)
    for old,new in PATCHES[name]:
        if source.count(old)!=1:raise ValueError(f'Exact anchor not found once: {name}, {old[:70]!r}')
        if new!=old and source.count(new)>0:raise ValueError('Already patched: '+name)
        source=source.replace(old,new,1)
    return source

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',required=True,type=Path)
    args=p.parse_args();root=args.root.resolve()
    changes={}
    for rel in PATCHES:
        target=root/rel
        if not target.is_file() or target.is_symlink():raise ValueError('Unsafe/missing tracked target: '+rel)
        changes[target]=transform(rel,target.read_text(encoding='utf-8'))
    for target,content in changes.items():
        target.write_text(content,encoding='utf-8')
        print('PATCHED:',target.relative_to(root))
    print('PASS: v0.41 public science and synthetic validation integration; clinical endpoint unchanged')
if __name__=='__main__':main()
