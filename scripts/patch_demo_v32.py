#!/usr/bin/env python3
"""Strict one-shot v0.31 -> v0.32 website patch. Source-only, no research data."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()

def change(rel, old, new):
    p = root / rel
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{rel}: expected exactly one anchor; found {count}: {old[:110]!r}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')
    print('PATCHED:',p)

# The public demo's passcode is explicitly NOT a secure administrator credential.
# It grants access only to the existing public-aggregate dashboard. The securely
# configured admin auth path remains separate and fail-closed.
auth='web/app/lib/auth.ts'
change(auth, "const COOKIE = 'frailtyscope_admin_demo';", "const COOKIE = 'frailtyscope_admin_demo';\nconst PUBLIC_DEMO_COOKIE = 'frailtyscope_public_aggregate_demo_v32';\nconst PUBLIC_DEMO_VALUE = 'aggregate-view-only';")
change(auth,
       'export async function closeAdminSession() {\n  (await cookies()).delete(COOKIE);\n}',
       """/** This fixed passcode is intentionally public and MUST NEVER protect private
 * data, research workflows, APIs, administrative writes or private artifacts.
 * It only opens the static, published-aggregate demonstration dashboard.
 */
export function isPublicDemoPasscode(input: string): boolean {
  return input === 'admin123';
}

export async function openPublicDemoSession(): Promise<void> {
  (await cookies()).set(PUBLIC_DEMO_COOKIE, PUBLIC_DEMO_VALUE, {
    httpOnly: true, secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax', path: '/', maxAge: Math.ceil(TTL / 1000),
  });
}

export async function hasPublicDemoSession(): Promise<boolean> {
  // Intentionally NOT an authorization mechanism: cookie is forgeable by design.
  // Do not use this function for any access other than public aggregate views.
  return (await cookies()).get(PUBLIC_DEMO_COOKIE)?.value === PUBLIC_DEMO_VALUE;
}

export async function canViewPublicDashboard(): Promise<boolean> {
  return await hasAdminSession() || await hasPublicDemoSession();
}

export async function closeAdminSession() {
  const store = await cookies();
  store.delete(COOKIE);
  store.delete(PUBLIC_DEMO_COOKIE);
}""")

change('web/app/admin/actions.ts',
       "import { matchesPassword, openAdminSession, closeAdminSession } from '../lib/auth';",
       "import { matchesPassword, openAdminSession, closeAdminSession, isPublicDemoPasscode, openPublicDemoSession } from '../lib/auth';")
change('web/app/admin/actions.ts',
       "  if (typeof password !== 'string' || !matchesPassword(password)) {",
       """  if (typeof password === 'string' && isPublicDemoPasscode(password)) {
    await openPublicDemoSession();
    redirect('/admin');
  }
  if (typeof password !== 'string' || !matchesPassword(password)) {""")

change('web/app/admin/page.tsx',
       "import { hasAdminSession } from '../lib/auth';",
       "import { canViewPublicDashboard, hasPublicDemoSession } from '../lib/auth';")
change('web/app/admin/page.tsx',
       "  if (!(await hasAdminSession())) redirect('/admin/login');",
       "  if (!(await canViewPublicDashboard())) redirect('/admin/login');\n  const publicDemo = await hasPublicDemoSession();")
change('web/app/admin/page.tsx',
       '  return <div className="page-wrap admin-page">',
       """  return <div className="page-wrap admin-page">
    {publicDemo && <aside className="v32-demo-banner" role="note"><strong>Public demonstration workspace — not secure research administration</strong>Only historically published NHANES aggregates and documentary synthetic software status are visible. Passcode admin123 is a demo convenience, not authorization to access private participant data or run models.</aside>}""")

change('web/app/admin/login/page.tsx',
       "import { hasAdminSession } from '../../lib/auth';",
       "import { canViewPublicDashboard } from '../../lib/auth';")
change('web/app/admin/login/page.tsx',
       "  if(await hasAdminSession()) redirect('/admin');",
       "  if(await canViewPublicDashboard()) redirect('/admin');")
change('web/app/admin/login/page.tsx',
       'Enter the administrator password to access research and model analytics.',
       'View the read-only aggregate research demo, or sign in with separately configured administrator credentials.')
change('web/app/admin/login/page.tsx',
       '<form action={signIn} className="login-form">',
       '<div className="v32-demo-credential" role="note">Public demo passcode: <code>admin123</code>. This is not a secure administrator login.</div><form action={signIn} className="login-form">')
change('web/app/admin/login/page.tsx',
       'Admin password</label>',
       'Passcode or administrator password</label>')

change('web/app/components/multi-outcome-admin.tsx',
       "import { ResearchBoundaryNotice } from './research-boundary-notice';",
       "import { ResearchBoundaryNotice } from './research-boundary-notice';\nimport { EngineStudioV32 } from './engine-studio-v32';")
change('web/app/components/multi-outcome-admin.tsx',
       "type Section = 'Dataset'",
       "type Section = 'Engine studio' | 'Dataset'")
change('web/app/components/multi-outcome-admin.tsx',
       "const steps:Section[]=['Dataset'",
       "const steps:Section[]=['Engine studio','Dataset'")
change('web/app/components/multi-outcome-admin.tsx',
       "const [tab,setTab]=useState<Section>('Dataset');",
       "const [tab,setTab]=useState<Section>('Engine studio');")
change('web/app/components/multi-outcome-admin.tsx',
       "   <ResearchBoundaryNotice/>",
       "   <ResearchBoundaryNotice/>\n   {tab==='Engine studio'&&<EngineStudioV32/>}")
change('web/app/layout.tsx',
       "import './nhanes-v12.css';",
       "import './nhanes-v12.css';\nimport './engine-studio-v32.css';")
change('tests/test_web_reporting_v31.py',
       'def test_no_demo_authentication_fallback():',
       'def test_public_demo_login_keeps_strict_admin_authentication_fail_closed():')
change('tests/test_web_reporting_v31.py',
       "    assert 'admin123' not in code",
       """    assert "input === 'admin123'" in code
    assert 'PUBLIC_DEMO_COOKIE' in code
    assert 'hasPublicDemoSession' in code
    assert "process.env.ADMIN_PORTAL_PASSWORD || ''" in code""")

change('.github/workflows/ci.yml',
       'tests/test_web_reporting_v31.py',
       'tests/test_web_reporting_v31.py tests/test_demo_studio_v32.py')
print('PASS: v0.32 source-only patch. No data/ artifacts/ web/public/data/ touched.')
