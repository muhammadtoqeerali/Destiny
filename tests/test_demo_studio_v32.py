"""Static/privacy regressions for the public-only v0.32 engine demonstration."""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]

def txt(path):
    return (R/path).read_text(encoding='utf-8')

def test_public_demo_does_not_bypass_secure_admin_checks():
    auth = txt('web/app/lib/auth.ts')
    assert "input === 'admin123'" in auth
    assert 'PUBLIC_DEMO_COOKIE' in auth
    assert 'hasPublicDemoSession' in auth
    assert 'hasAdminSession() || await hasPublicDemoSession()' in auth
    assert 'if (!configured()) return false' in auth
    assert 'password().length >= 16' in auth
    assert 'secret().length >= 32' in auth
    assert 'PUBLIC_DEMO_COOKIE' in auth.split('export async function closeAdminSession()')[1]


def test_public_demo_not_advertised_as_secure_auth():
    login=txt('web/app/admin/login/page.tsx')
    admin=txt('web/app/admin/page.tsx')
    assert 'Public demo passcode:' in login
    assert 'not a secure administrator login' in login
    assert 'Public demonstration workspace' in admin
    assert 'not secure research administration' in admin
    assert 'canViewPublicDashboard()' in login
    assert 'canViewPublicDashboard()' in admin


def test_demo_login_flow_is_explicit_read_only():
    actions=txt('web/app/admin/actions.ts')
    assert 'isPublicDemoPasscode(password)' in actions
    assert 'openPublicDemoSession()' in actions
    assert 'matchesPassword(password)' in actions
    assert 'await openAdminSession()' in actions
    assert 'redirect(' in actions


def test_engine_tab_is_first_and_legacy_views_remain():
    hub=txt('web/app/components/multi-outcome-admin.tsx')
    assert "useState<Section>('Engine studio')" in hub
    assert "{tab==='Engine studio'&&<EngineStudioV32/>}" in hub
    for tab in ('Dataset','Preprocessing','Model training','Performance',
                'Interpretability','Benchmark','Deep analysis','Decision quality'):
        assert "'"+tab+"'" in hub
    assert '<ResearchBoundaryNotice/>' in hub


def test_studio_has_honest_training_boundaries_and_keyboard_controls():
    src=txt('web/app/components/engine-studio-v32.tsx')
    for word in ('BLOCKED_FOR_NEW_ANALYSIS','synthetic','fictional','not a new independent',
                 'role="tablist"','aria-selected','role="tabpanel"','v0.30',
                 'source-contract','previously inspected','Seed 1701'):
        assert word.lower() in src.lower()
    assert 'onClick={()=>setActive(i)}' in src
    assert 'onClick={()=>setShowProvenance(!showProvenance)}' in src
    assert 'participant' in src.lower()
    assert 'model.fit(' not in src
    assert 'predict_proba' not in src


def test_studio_reuses_only_historical_public_aggregates():
    src=txt('web/app/components/engine-studio-v32.tsx')
    assert "../../public/data/nhanes-aggregate.json" in src
    assert "../../public/data/nhanes-refinement.json" in src
    assert "../../public/data/nhanes-decision-quality-v12.json" in src
    assert 'data/processed' not in src and 'artifacts/' not in src
    study=json.loads(txt('web/public/data/nhanes-aggregate.json'))
    refine=json.loads(txt('web/public/data/nhanes-refinement.json'))
    quality=json.loads(txt('web/public/data/nhanes-decision-quality-v12.json'))
    assert study['counts']['total']==2422
    assert study['counts']['test']==refine['counts']['test']==quality['counts']['evaluation']==1257
    assert study['counts']['test_events']==refine['counts']['test_events']==quality['counts']['events']==246


def test_studio_receipt_matches_v30_published_synthetic_smoke():
    studio=txt('web/app/components/engine-studio-v32.tsx')
    assert '85a346ced199a6f00b53232aec01cc3f99720e6a467ee0ab4db58631a0e458a1' in studio
    assert 'deb79398b4f62c49801b127c7a0e0f8cd045cf9dc61f3a7d87b140b9e5dab4b7' in studio
    assert '72 invented rows' in studio
    assert '36 fictional people' in studio
    assert 'Six fictional fits' in studio
    assert '1701' in studio


def test_css_is_scoped_for_demo_and_in_layout():
    css=txt('web/app/engine-studio-v32.css')
    layout=txt('web/app/layout.tsx')
    assert "import './engine-studio-v32.css';" in layout
    for token in ('.v32-studio','.v32-hero','.v32-stage-tabs',
                  '.v32-demo-banner','prefers-reduced-motion','focus-visible'):
        assert token in css


def test_ci_has_studio_tests_and_keeps_privacy_gate():
    ci=txt('.github/workflows/ci.yml')
    assert 'tests/test_demo_studio_v32.py' in ci
    assert 'tests/test_web_reporting_v31.py' in ci
    assert 'Public payload validation' in ci
    assert 'nhanes-decision-quality-v12.json' in ci


def test_existing_private_research_execution_still_blocked():
    cfg=json.loads(txt('research/cases/nhanes_workflow_v29.json'))
    assert cfg['real_data_execution_permitted'] is False
    assert cfg['model_fitting_permitted'] is False
    assert cfg['public_export_permitted'] is False
    assert cfg['holdout_history']=='previously_inspected'
    assert cfg['prediction_index_status']=='provisional'
