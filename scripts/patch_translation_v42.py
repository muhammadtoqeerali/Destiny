#!/usr/bin/env python3
"""Patch exactly four reviewed v0.41 source files; no research artifacts or patient data."""
import argparse
from pathlib import Path

PATCHES={
 '.github/workflows/ci.yml':[
    ('      - name: Verify v0.41 public research and invented holdback receipt\n',
     '      - name: Verify v0.42 public source-to-form crosswalk\n'
     '        run: PYTHONPATH=. python -m ml.model_translation_v42 --check\n'
     '      - name: Validate v0.42 source-to-form regression contracts\n'
     '        run: python -m pytest -q tests/test_translation_v42.py\n'
     '      - name: Verify v0.41 public research and invented holdback receipt\n'),
 ],
 'scripts/run_browser_qa_v34.sh':[
    ('FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_validation_v41.py\n',
     'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_validation_v41.py\n'
     'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_translation_v42.py\n'),
 ],
 'web/app/components/clinical-workspace.tsx':[
    ("import {ValidationGateV41} from './validation-gate-v41';\n",
     "import {ValidationGateV41} from './validation-gate-v41';\n"
     "import {ModelTranslationV42} from './model-translation-v42';\n"),
    ('     <ValidationGateV41/>\n',
     '     <ValidationGateV41/>\n     <ModelTranslationV42/>\n'),
 ],
 'web/app/layout.tsx':[
    ("import './validation-v41.css';\n",
     "import './validation-v41.css';\nimport './translation-v42.css';\n"),
 ],
}

def transform(name:str,source:str)->str:
    if name not in PATCHES:raise ValueError('Unexpected patch path: '+name)
    for old,new in PATCHES[name]:
        if source.count(old)!=1:raise ValueError(f'Expected unique anchor for {name}: {old[:75]!r}')
        if new!=old and source.count(new)>0:raise ValueError('Already patched: '+name)
        source=source.replace(old,new,1)
    return source

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True,type=Path)
    args=parser.parse_args()
    root=args.root.resolve()
    edits={}
    for name in PATCHES:
        p=root/name
        if not p.is_file() or p.is_symlink():raise ValueError('Missing or unsafe tracked source: '+name)
        edits[p]=transform(name,p.read_text(encoding='utf-8'))
    for p,content in edits.items():
        p.write_text(content,encoding='utf-8')
        print('PATCHED:',p.relative_to(root))
    print('PASS: v0.42 source-only crosswalk and approval-gate integration. No clinical inference enabled.')
if __name__=='__main__':main()
