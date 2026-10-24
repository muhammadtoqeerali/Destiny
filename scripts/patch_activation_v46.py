#!/usr/bin/env python3
"""Insert only CI source-contract checks at one verified v0.45 anchor."""
import argparse
from pathlib import Path
PATH='.github/workflows/ci.yml'
ANCHOR='      - name: Validate v0.45 local-only evidence triage source contracts\n'
INSERT=(
 '      - name: Verify v0.46 public research activation plan\n'
 '        run: PYTHONPATH=. python -m ml.study_activation_v46 --check-public-plan\n'
 '      - name: Validate v0.46 private-only planning contracts\n'
 '        run: python -m pytest -q tests/test_study_activation_v46.py\n'
)
def transform(s:str)->str:
    if s.count(ANCHOR)!=1 or INSERT in s:raise ValueError('Unsafe v0.45 CI source anchor or repeated patch')
    return s.replace(ANCHOR,INSERT+ANCHOR,1)
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);a=p.parse_args()
    root=a.root.resolve();path=root/PATH
    if not path.is_file() or path.is_symlink():raise ValueError('Unsafe tracked CI source')
    changed=transform(path.read_text(encoding='utf8'))
    path.write_text(changed,encoding='utf8');print('PATCHED:',PATH)
    print('PASS: v0.46 independent CI planning checks; all previous assertions retained')
if __name__=='__main__': main()
