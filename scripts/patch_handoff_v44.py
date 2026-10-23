#!/usr/bin/env python3
"""Exact-anchor, fail-before-write v0.44 source-only patch of published v0.43."""
from __future__ import annotations
import argparse
from pathlib import Path
PATCHES={
 '.github/workflows/ci.yml':[
    ('      - name: Verify v0.43 synthetic-only model-artifact manifest\n',
     '      - name: Verify v0.44 public-only study-team evidence handoff\n'
     '        run: PYTHONPATH=. python -m ml.study_handoff_v44 --check\n'
     '      - name: Validate v0.44 study-team handoff regressions\n'
     '        run: python -m pytest -q tests/test_handoff_v44.py\n'
     '      - name: Verify v0.43 synthetic-only model-artifact manifest\n'),
 ],
 'scripts/run_browser_qa_v34.sh':[
    ('FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_artifact_v43.py\n',
     'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_artifact_v43.py\n'
     'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_handoff_v44.py\n'),
 ],
 'web/app/components/clinical-workspace.tsx':[
     ("import {ArtifactAcceptanceV43} from './artifact-acceptance-v43';\n",
      "import {ArtifactAcceptanceV43} from './artifact-acceptance-v43';\n"
      "import {StudyHandoffV44} from './study-handoff-v44';\n"),
     ('     <ArtifactAcceptanceV43/>\n',
      '     <ArtifactAcceptanceV43/>\n     <StudyHandoffV44/>\n'),
 ],
 'web/app/layout.tsx':[
     ("import './artifact-v43.css';\n",
      "import './artifact-v43.css';\nimport './study-handoff-v44.css';\n"),
 ],
}

def transform(name,content):
    if name not in PATCHES:raise ValueError('Unapproved source path '+name)
    for old,new in PATCHES[name]:
        if content.count(old)!=1:raise ValueError('Missing or ambiguous exact v0.43 anchor: '+name)
        if new!=old and new in content:raise ValueError('Patch already applied '+name)
        content=content.replace(old,new,1)
    return content

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    args=p.parse_args()
    root=args.root.resolve()
    changed={}
    for name in PATCHES:
        f=root/name
        if not f.is_file() or f.is_symlink():raise ValueError('Unsafe tracked source '+name)
        changed[f]=transform(name,f.read_text(encoding='utf8'))
    for path,value in changed.items():
        path.write_text(value,encoding='utf8')
        print('PATCHED:',path.relative_to(root))
    print('PASS: v0.44 evidence-request handoff integrated; clinical inference unchanged')
if __name__=='__main__':main()
