"""Source contracts for the redesigned Doctor / Research frontend.

Checks the product boundaries that must survive any future UI work: two primary destinations, no
"Interview" in the visible product, real and fictional evidence kept apart, no private-data or
inference paths from the browser, numbers read from the verified aggregate JSON, and authentication intact.
No browser or private data is needed.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'web/app'


def src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf8')


def visible_source_files():
    files = [*APP.glob('ui/*.tsx'), APP / 'doctor/page.tsx', APP / 'admin/page.tsx', APP / 'admin/login/page.tsx',
             APP / 'layout.tsx', APP / 'components/site-header.tsx', APP / 'archive/page.tsx']
    return files


def test_no_interview_wording_in_visible_product_source():
    for f in visible_source_files():
        for line in f.read_text(encoding='utf8').splitlines():
            if line.lstrip().startswith('import '):
                continue  # the generated fixture's file name is unchanged; it is never displayed
            assert 'interview' not in line.lower(), (f.name, line.strip()[:100])
    # Legacy workspaces under /archive must not show it either.
    assert 'interview' not in src('web/app/components/engine-studio-v32.tsx').lower()
    css = src('web/app/ui/fs.css')
    assert 'interview' not in css.lower()


def test_exactly_two_primary_destinations_and_old_paths_only_redirect():
    header = src('web/app/components/site-header.tsx')
    hrefs = re.findall(r"href: '([^']+)'", header)
    assert hrefs == ['/doctor', '/admin']
    assert '/interview' not in header
    assert "redirect('/doctor')" in src('web/app/page.tsx')
    assert "redirect('/doctor')" in src('web/app/interview/page.tsx')
    legacy_admin = src('web/app/admin/interview/page.tsx')
    assert "redirect('/admin')" in legacy_admin and 'AdminResearchHub' not in legacy_admin
    # nothing in the redesigned sources links to the old paths
    for f in visible_source_files():
        text = f.read_text(encoding='utf8')
        assert 'href="/interview"' not in text and 'href="/admin/interview"' not in text, f.name


def test_authentication_and_inference_gate_are_unchanged():
    admin = src('web/app/admin/page.tsx')
    assert 'canViewPublicDashboard()' in admin and "redirect('/admin/login')" in admin
    login = src('web/app/admin/login/page.tsx')
    assert 'canViewPublicDashboard()' in login and 'signIn' in login and 'name="password"' in login
    assert 'admin123' not in login and 'admin123' not in admin
    archive_admin = src('web/app/archive/admin/page.tsx')
    assert 'canViewPublicDashboard()' in archive_admin and "redirect('/admin/login')" in archive_admin
    assert 'status:403' in src('web/app/api/inference/route.ts')
    actions = src('web/app/admin/actions.ts')
    assert 'isPublicDemoPasscode(password)' in actions and 'matchesPassword(password)' in actions


def test_real_and_fictional_evidence_stay_in_separate_modules():
    real_only = ['web/app/ui/population.tsx']
    for rel in real_only:
        assert 'interview-benchmark' not in src(rel), rel  # the fictional fixture
    explorer = src('web/app/ui/profile-explorer.tsx')
    assert 'real-mobility-summary' not in explorer  # no real metric next to a fictional score
    assert "from '../data/interview-benchmark-v47.json'" in explorer
    assert 'Fictional example, not a patient' in explorer
    assert 'Synthetic demo model' in explorer


def test_numbers_come_from_verified_aggregate_json_not_literals():
    summary = json.loads(src('web/app/data/real-mobility-summary-v49.json'))
    ui = ''.join(src(f'web/app/ui/{n}.tsx') for n in ('population', 'research-dashboard', 'charts'))
    assert "real-mobility-summary-v49.json'" in ui
    literals = ['0.73201', '0.17354', '0.15070', '0.1507', '0.78089', '0.17675', '0.16627', '0.014712', '0.248731',
                '0.26938', '0.1217', '0.3525', '985', '1032', '1,032', '788', '197']
    for lit in literals:
        assert lit not in ui, f'hard-coded result {lit}'
    assert summary['cohorts']['2017-2018']['questionnaire_respondents'] == 1032  # source file unchanged


def test_ui_has_no_network_storage_or_patient_input_paths():
    for f in [*APP.glob('ui/*.tsx'), APP / 'doctor/page.tsx']:
        text = f.read_text(encoding='utf8')
        for banned in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'api/inference', '<form',
                       '<input', '<textarea', 'SEQN', 'patient_id', 'method:'):
            assert banned not in text, (f.name, banned)


def test_motion_and_accessibility_contracts_in_design_system():
    css = src('web/app/ui/fs.css')
    assert 'prefers-reduced-motion:reduce' in css and ':focus-visible' in css
    assert '.fs-skip' in css and 'role="tooltip"' in css
    layout = src('web/app/layout.tsx')
    assert 'href="#main"' in layout and "import './ui/fs.css';" in layout
    for rel in ('doctor/page.tsx', 'admin/page.tsx', 'admin/login/page.tsx'):
        assert 'id="main"' in src('web/app/' + rel)
    dash = src('web/app/ui/research-dashboard.tsx')
    assert 'role="tablist"' in dash and 'role="tabpanel"' in dash and "aria-label=\"Experiment stages\"" in dash
    assert 'role="radiogroup"' in src('web/app/ui/profile-explorer.tsx')
    assert 'inert={!open}' in src('web/app/ui/disclosure.tsx')


def test_legacy_styles_are_isolated_under_archive():
    root = src('web/app/layout.tsx')
    assert not re.search(r"import '\./(globals|nhanes|engine-studio|doctor-|inference|validation|translation|artifact|study-handoff)", root)
    archive = src('web/app/archive/layout.tsx')
    assert archive.count("import '../") == 17
    assert (APP / 'archive/doctor/page.tsx').is_file() and (APP / 'archive/admin/page.tsx').is_file()


def test_dependency_change_is_limited_to_the_self_hosted_font():
    pkg = json.loads(src('web/package.json'))
    assert pkg['dependencies']['@fontsource-variable/instrument-sans'] == '5.3.0'
    assert set(pkg['dependencies']) == {'next', 'react', 'react-dom', 'lucide-react', 'recharts', '@fontsource-variable/instrument-sans'}
    lock = json.loads(src('web/package-lock.json'))
    assert 'node_modules/@fontsource-variable/instrument-sans' in lock['packages']


def test_browser_suite_and_ci_run_the_redesign_checks():
    qa = src('scripts/run_browser_qa_v34.sh')
    assert 'tests/browser_frailtyscope_redesign.py' in qa
    assert 'browser_interview' not in qa
    ci = src('.github/workflows/ci.yml')
    assert 'tests/test_frailtyscope_redesign.py' in ci
