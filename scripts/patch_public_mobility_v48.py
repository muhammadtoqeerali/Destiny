#!/usr/bin/env python3
"""One allowlisted CI step addition; all v0.47 and prior source-contract anchors remain intact."""
from __future__ import annotations
import argparse
from pathlib import Path
PATH='.github/workflows/ci.yml'
ANCHOR='      - name: Check v0.47 generated interview benchmark\n'
INSERT=('      - name: Verify Phase 2 public mobility benchmark contract (no real downloads)\n'
        '        run: PYTHONPATH=. python -m ml.public_mobility_v48 --contract\n'
        '      - name: Test Phase 2 source recodes, leakage control and synthetic fixtures\n'
        '        run: python -m pytest -q tests/test_public_mobility_v48.py\n')
def transform(s):
    if s.count(ANCHOR)!=1 or INSERT in s:raise ValueError('Unsafe v0.47 CI anchor or patch already applied')
    return s.replace(ANCHOR,INSERT+ANCHOR,1)
def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True)
    p=a.parse_args().root/PATH
    if not p.is_file() or p.is_symlink():raise ValueError('Unsafe source path')
    p.write_text(transform(p.read_text(encoding='utf8')),encoding='utf8')
    print('PASS: v0.48 public mobility source-contract CI enabled; old tests unchanged')
if __name__=='__main__':main()
