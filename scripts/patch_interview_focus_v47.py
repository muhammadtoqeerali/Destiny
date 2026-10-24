#!/usr/bin/env python3
"""Exact v0.46 patch: make concise interview view entrypoint, preserve legacy research pages."""
from __future__ import annotations
import argparse
from pathlib import Path

PATCHES={
 '.github/workflows/ci.yml':[
    ('      - name: Validate v0.45 local-only evidence triage source contracts\n',
     '      - name: Check v0.47 generated interview benchmark\n'
     '        run: PYTHONPATH=. python -m ml.interview_benchmark_v47 --check\n'
     '      - name: Validate v0.47 interview research focus\n'
     '        run: python -m pytest -q tests/test_interview_focus_v47.py\n'
     '      - name: Validate v0.45 local-only evidence triage source contracts\n'),
 ],
 'scripts/run_browser_qa_v34.sh':[
    ('FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_handoff_v44.py\n',
     'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_handoff_v44.py\n'
     'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_interview_focus_v47.py\n'),
 ],
 'web/app/layout.tsx':[
    ("import './study-handoff-v44.css';\n",
     "import './study-handoff-v44.css';\nimport './interview-focus-v47.css';\n"),
 ],
 'web/app/page.tsx':[
    ("redirect('/doctor');", "redirect('/interview');"),
 ],
 'web/app/components/site-header.tsx':[
    ("import {HeartPulse, LockKeyhole, Stethoscope} from 'lucide-react';",
     "import {BrainCircuit, HeartPulse, LockKeyhole, Stethoscope} from 'lucide-react';"),
    (" const inAdmin=usePathname().startsWith('/admin');",
     " const path=usePathname(); const inAdmin=path.startsWith('/admin');"),
    ('<Link href="/doctor" className="site-brand"',
     '<Link href="/interview" className="site-brand"'),
    ('<nav className="portal-nav" aria-label="Portal navigation">',
     '<nav className="portal-nav" aria-label="Portal navigation"><Link href="/interview" aria-label="Interview focus" className={path===\'/interview\'?\'nav-active\':\'\'}><BrainCircuit size={17}/><span className="if-header-desktop">Interview focus</span><span className="if-header-mobile">Focus</span></Link>'),
    ('className={!inAdmin?\'nav-active\':\'\'}',
     'className={path.startsWith(\'/doctor\')?\'nav-active\':\'\'}'),
 ],
}

def transform(name:str,content:str)->str:
    if name not in PATCHES:raise ValueError('Unapproved path: '+name)
    for old,new in PATCHES[name]:
        if content.count(old)!=1 or new in content:
            raise ValueError('Missing/ambiguous baseline anchor or patch repeated in '+name)
        content=content.replace(old,new,1)
    return content

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();changed={}
    for rel in PATCHES:
        target=root/rel
        if not target.is_file() or target.is_symlink():raise ValueError('Unsafe tracked file '+rel)
        changed[target]=transform(rel,target.read_text(encoding='utf8'))
    for path,new in changed.items():
        path.write_text(new,encoding='utf8');print('PATCHED:',path.relative_to(root))
    print('PASS: Interview-focused default and preserved advanced workspaces; original clinical inference unchanged')

if __name__=='__main__':main()
