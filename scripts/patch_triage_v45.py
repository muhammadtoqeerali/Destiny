#!/usr/bin/env python3
"""One exact source anchor in public CI; fail-before-write and reject reapplication."""
from __future__ import annotations
import argparse
from pathlib import Path

PATH = '.github/workflows/ci.yml'
ANCHOR = '      - name: Verify v0.44 public-only study-team evidence handoff\n'
INSERT = (
    '      - name: Validate v0.45 local-only evidence triage source contracts\n'
    '        run: python -m pytest -q tests/test_study_evidence_triage_v45.py\n'
    '      - name: Verify v0.45 unmodified blank study-team template\n'
    '        run: PYTHONPATH=. python -m ml.study_evidence_triage_v45 --check-template\n'
)


def transform(content: str) -> str:
    if content.count(ANCHOR) != 1 or INSERT in content:
        raise ValueError('Unsafe v0.44 CI anchor or patch already applied')
    return content.replace(ANCHOR, INSERT+ANCHOR, 1)


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    args=p.parse_args()
    root=args.root.resolve()
    path=root/PATH
    if not path.is_file() or path.is_symlink():
        raise ValueError('Unsafe public CI source')
    original=path.read_text(encoding='utf8')
    result=transform(original)
    path.write_text(result,encoding='utf8')
    print('PATCHED:',PATH)
    print('PASS: Legacy v0.44 CI anchor preserved, new local-only review tests added')


if __name__=='__main__': main()
