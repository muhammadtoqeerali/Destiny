"""Source and aggregate-only validation of the demo dashboard. No research data is read."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def content(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def test_public_pages_never_print_passcode():
    for path in ('web/app/admin/login/page.tsx','web/app/admin/page.tsx',
                 'web/app/components/engine-studio-v33.tsx'):
        src=content(path)
        assert 'admin123' not in src
        assert 'Public demo passcode:' not in src
        assert 'Passcode admin123' not in src
    assert 'v32-demo-banner' not in content('web/app/admin/page.tsx')
    assert 'v32-demo-credential' not in content('web/app/admin/login/page.tsx')


def test_public_demo_login_keeps_isolated_safety_boundary():
    auth=content('web/app/lib/auth.ts')
    actions=content('web/app/admin/actions.ts')
    assert "input === 'admin123'" in auth
    assert 'hasAdminSession() || await hasPublicDemoSession()' in auth
    assert 'isPublicDemoPasscode(password)' in actions
    assert 'process.env.ADMIN_PORTAL_PASSWORD' in auth
    assert 'password().length >= 16' in auth
    assert 'secret().length >= 32' in auth


def test_original_tabs_and_new_interactive_studio_are_connected():
    hub=content('web/app/components/multi-outcome-admin.tsx')
    assert "useState<Section>('Engine studio')" in hub
    assert "{tab==='Engine studio'&&<EngineStudioV33/>}" in hub
    assert 'EngineStudioV32' not in hub
    for name in ('Dataset','Preprocessing','Model training','Performance',
                 'Interpretability','Benchmark','Deep analysis','Decision quality'):
        assert f"'{name}'" in hub
    assert '<ResearchBoundaryNotice/>' in hub


def test_workflow_comes_from_traced_synthetic_implementation_not_browser_training():
    src=content('web/app/components/engine-studio-v33.tsx')
    for text in ('v0.22–v0.24','v0.25','v0.26','v0.28','v0.29','v0.30',
                 'dummy_prior','logistic','synthetic','fictional','BLOCKED_FOR_NEW_ANALYSIS',
                 '1701','onClick={()=>setView','onClick={()=>setActive',
                 'aria-current','aria-pressed','onClick={()=>setMeasure'):
        assert text in src
    assert 'model.fit(' not in src and 'predict_proba(' not in src
    assert 'fetch(' not in src and 'artifacts/' not in src
    assert '<strong>Not authorized</strong>' in src
    assert 'fresh external-validation claims' in src.lower()
    assert 'new independent validation' not in src.lower()


def test_historical_inputs_and_receipts_are_unchanged():
    src=content('web/app/components/engine-studio-v33.tsx')
    assert '85a346ced199a6f00b53232aec01cc3f99720e6a467ee0ab4db58631a0e458a1' in src
    assert 'deb79398b4f62c49801b127c7a0e0f8cd045cf9dc61f3a7d87b140b9e5dab4b7' in src
    d=json.loads(content('web/public/data/nhanes-aggregate.json'))
    r=json.loads(content('web/public/data/nhanes-refinement.json'))
    q=json.loads(content('web/public/data/nhanes-decision-quality-v12.json'))
    assert (d['counts']['development'],d['counts']['test'],d['counts']['test_events'])==(1165,1257,246)
    assert r['counts']['test']==q['counts']['evaluation']==1257
    assert q['counts']['events']==246
    for item in (d['testAtF2'],r['test'],q['evaluation']):
        c=item['confusion']
        assert c['tp']+c['fn']==246
        assert c['tn']+c['fp']==1011


def test_responsive_css_and_accessible_controls():
    css=content('web/app/engine-studio-v33.css')
    jsx=content('web/app/components/engine-studio-v33.tsx')
    layout=content('web/app/archive/layout.tsx')
    assert "import '../engine-studio-v33.css';" in layout
    for marker in ('.v33-hero','.v33-nav','.v33-workspace','.v33-model-layout',
                   '.v33-assurance-grid','@media(max-width:860px)','@media(max-width:560px)',
                   'prefers-reduced-motion','focus-visible'):
        assert marker in css
    for marker in ('type="button"','aria-label=','aria-pressed=','aria-current=',
                   'disabled={active===0}','disabled={active===6}'):
        assert marker in jsx


def test_ci_and_research_data_boundary():
    ci=content('.github/workflows/ci.yml')
    assert 'tests/test_engine_studio_v33.py' in ci
    assert 'Public payload validation' in ci
    cfg=json.loads(content('research/cases/nhanes_workflow_v29.json'))
    assert cfg['real_data_execution_permitted'] is False
    assert cfg['holdout_history']=='previously_inspected'
    assert cfg['prediction_index_status']=='provisional'
