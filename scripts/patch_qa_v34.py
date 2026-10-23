"""Strict, deterministic source-only v0.34 edits. No participant/model/public JSON IO."""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()

def update(path, old, new):
    p=root/path
    s=p.read_text(encoding='utf-8')
    if s.count(old)!=1:
        raise ValueError(f'{path}: expected one patch anchor, found {s.count(old)} for {old[:85]!r}')
    p.write_text(s.replace(old,new),encoding='utf-8')
    print(f'PATCHED: {path}')

update('web/app/components/engine-studio-v33.tsx',
    "import general from '../../public/data/nhanes-decision-quality-v12.json';",
    "import general from '../../public/data/nhanes-decision-quality-v12.json';\nimport { ReleaseStatusV34 } from './release-status-v34';")
update('web/app/components/engine-studio-v33.tsx',
    '   <nav className="v33-nav" aria-label="Engine Studio views">',
    '   <ReleaseStatusV34/>\n   <nav className="v33-nav" aria-label="Engine Studio views">')
update('web/app/components/engine-studio-v33.tsx',
    '<span>Regression suite at v0.32</span><strong>708</strong><small>Passed · 1 skipped (workstation log)</small>',
    '<span>Synthetic repeatability</span><strong>2</strong><small>Matching v0.30 aggregate runs · seed 1701</small>')
update('web/app/layout.tsx',
    "import './engine-studio-v33.css';",
    "import './engine-studio-v33.css';\nimport './engine-studio-v34.css';")
ci=root/'.github/workflows/ci.yml'
s=ci.read_text(encoding='utf-8')
anchor='tests/test_engine_studio_v33.py'
if s.count(anchor)!=1:raise ValueError('Unexpected v0.33 CI pytest anchor')
s=s.replace(anchor,anchor+' tests/test_demo_qa_v34.py')
anchor='      - run: npm audit --omit=dev --audit-level=high\n        working-directory: web'
if s.count(anchor)!=1:raise ValueError('Unexpected npm audit CI anchor')
s=s.replace(anchor,anchor+'''
      # Actual Chromium browser checks against a freshly built local Next.js server.
      # This is independent of the synthetic/privacy Python regression suite.
      - run: python -m pip install 'playwright==1.56.0'
      - run: python -m playwright install --with-deps chromium
      - run: bash scripts/run_browser_qa_v34.sh
        env:
          FRAILTYSCOPE_QA_PYTHON: python''')
ci.write_text(s,encoding='utf-8')
print('PATCHED: .github/workflows/ci.yml')
