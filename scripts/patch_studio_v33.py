#!/usr/bin/env python3
"""Strict source-only v0.32 -> v0.33 patch. Does not access datasets or artifacts."""
from pathlib import Path
import sys
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd().resolve()

def patch(path, old, new):
    p = ROOT / path
    value=p.read_text(encoding='utf-8')
    count=value.count(old)
    if count != 1:
        raise RuntimeError(f'{path}: unexpected patch context ({count} matches): {old[:92]!r}')
    p.write_text(value.replace(old,new,1),encoding='utf-8')
    print('PATCHED:',path)

login='web/app/admin/login/page.tsx'
patch(login,
    '<div className="v32-demo-credential" role="note">Public demo passcode: <code>admin123</code>. This is not a secure administrator login.</div>',
    '')
patch(login,
    'View the read-only aggregate research demo, or sign in with separately configured administrator credentials.',
    'Explore reproducible ML workflows and historical research analytics.')
patch(login,'Passcode or administrator password</label>','Access password</label>')

admin='web/app/admin/page.tsx'
patch(admin,
    "import { canViewPublicDashboard, hasPublicDemoSession } from '../lib/auth';",
    "import { canViewPublicDashboard } from '../lib/auth';")
patch(admin,
    '  const publicDemo = await hasPublicDemoSession();\n',
    '')
patch(admin,
    '    {publicDemo && <aside className="v32-demo-banner" role="note"><strong>Public demonstration workspace — not secure research administration</strong>Only historically published NHANES aggregates and documentary synthetic software status are visible. Passcode admin123 is a demo convenience, not authorization to access private participant data or run models.</aside>}\n',
    '')
patch(admin,'Research administration</span>','Research studio</span>')

hub='web/app/components/multi-outcome-admin.tsx'
patch(hub,
    "import { EngineStudioV32 } from './engine-studio-v32';",
    "import { EngineStudioV33 } from './engine-studio-v33';")
patch(hub,
    "{tab==='Engine studio'&&<EngineStudioV32/>}",
    "{tab==='Engine studio'&&<EngineStudioV33/>}")
patch('web/app/layout.tsx',
    "import './engine-studio-v32.css';",
    "import './engine-studio-v32.css';\nimport './engine-studio-v33.css';")

legacy='tests/test_demo_studio_v32.py'
patch(legacy,"    assert 'Public demo passcode:' in login", "    assert 'Public demo passcode:' not in login\n    assert 'admin123' not in login")
patch(legacy,"    assert 'not a secure administrator login' in login", "    assert 'not a secure administrator login' not in login")
patch(legacy,"    assert 'Public demonstration workspace' in admin", "    assert 'Public demonstration workspace' not in admin\n    assert 'admin123' not in admin")
patch(legacy,"    assert 'not secure research administration' in admin", "    assert 'not secure research administration' not in admin")
patch(legacy,"    assert \"{tab==='Engine studio'&&<EngineStudioV32/>}\" in hub", "    assert \"{tab==='Engine studio'&&<EngineStudioV33/>}\" in hub")
patch('.github/workflows/ci.yml',
    'tests/test_demo_studio_v32.py',
    'tests/test_demo_studio_v32.py tests/test_engine_studio_v33.py')
print('PASS: v0.33 patch applied. Existing demo authentication path unchanged.')
