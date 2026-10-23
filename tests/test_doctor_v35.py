"""Source contracts: v0.35 Norwegian-inspired Doctor Portal, no private-data use."""
from pathlib import Path
import json

R=Path(__file__).resolve().parents[1]

def source(path): return (R/path).read_text(encoding='utf-8')

def test_dedicated_design_scoped_to_doctor_portal():
    ui=source('web/app/components/clinical-workspace.tsx')
    css=source('web/app/doctor-v35.css')
    layout=source('web/app/layout.tsx')
    assert 'v7-portal v35-doctor' in ui
    assert "import './doctor-v35.css';" in layout
    assert '.v35-doctor' in css and '.v35-hero' in css
    assert '@media(max-width:480px)' in css
    assert 'focus-visible' in css and 'prefers-reduced-motion' in css
    assert 'Helsenorge' not in css and 'NTNU logo' not in css
    # Prevent the exact malformed declaration that broke the v0.35.1 Next.js build.
    assert 'transition:background .15s,color .15s;white-space:normal' in css
    assert 'transition:background .15s;color .15s' not in css

def test_doctor_hero_is_based_on_existing_public_aggregates():
    ui=source('web/app/components/doctor-visuals-v35.tsx')
    payload=json.loads(source('web/public/data/nhanes-aggregate.json'))
    assert 'nhanes-aggregate.json' in ui and 'study.counts.total' in ui
    assert 'study.counts.development' in ui and 'study.counts.test_events' in ui
    assert 'onNavigate' in ui and 'Review health profiles' in ui and 'Open assessment' in ui
    assert 'was previously inspected' in ui
    assert payload['counts']['total']==payload['counts']['development']+payload['counts']['test']==2422
    assert payload['counts']['test_events']==246
    assert 'fetch(' not in ui and 'predict_proba(' not in ui

def test_doctor_navigation_and_scope_are_accessible_and_honest():
    ui=source('web/app/components/clinical-workspace.tsx')
    assert 'aria-label="Doctor workspace"' in ui
    assert 'aria-label={t}' in ui and 'aria-current={page===t?' in ui
    assert 'role="region" aria-label={page}' in ui
    assert '<ResearchBoundaryNotice/>' in ui
    assert '<summary>Research scope and limitations</summary>' in ui
    assert 'not a clinical prediction service' in ui
    assert 'onNavigate={destination=>setPage(destination)}' in ui

def test_assessment_and_temporary_visits_are_not_weakened():
    ui=source('web/app/components/clinical-workspace.tsx')
    assert 'role="progressbar" aria-label="Valid assessment fields"' in ui
    for key in ('age','bmi','phq9_score'):
        assert 'aria-invalid={profile.'+key in ui
    for string in ('Not asked (structural skip)','Does not do activity','Refused',"Don\'t know"):
        assert string in ui
    assert 'Data are cleared when the page reloads.' in ui
    assert 'do not establish individual prognosis' in ui
    assert 'Number.isInteger(p)' in ui

def test_doctor_browser_suite_is_mandatory_on_local_runner():
    runner=source('scripts/run_browser_qa_v34.sh')
    assert 'tests/browser_qa_v34.py' in runner
    assert 'tests/browser_doctor_v35.py' in runner
    ci=source('.github/workflows/ci.yml')
    assert 'python -m playwright install chromium' in ci
    assert 'tests/test_doctor_v35.py' in ci
    prior_regression=source('tests/test_demo_qa_v34.py')
    assert "'python -m playwright install chromium'" in prior_regression
    assert 'http://127.0.0.1:$PORT' in runner
    browser=source('tests/browser_doctor_v35.py')
    assert '127\\.0\\.0\\.1' in browser
    assert 'Visit history' in browser and 'Health profiles' in browser
    assert 'mobile' in browser and 'desktop' in browser

def test_study_protocol_is_still_closed_to_new_analysis():
    data=json.loads(source('research/cases/nhanes_workflow_v29.json'))
    assert data['real_data_execution_permitted'] is False
    assert data['model_fitting_permitted'] is False
    assert data['public_export_permitted'] is False
    assert data['holdout_history']=='previously_inspected'


def test_original_browser_suite_disambiguates_hero_actions_and_doctor_nav():
    browser=source('tests/browser_qa_v34.py')
    nav="page.get_by_role('navigation',name='Doctor workspace')"
    for label in ('Health profiles','Patient assessment','Visit history','Model evidence'):
        assert f"{nav}.get_by_role('button',name='{label}',exact=True).click()" in browser
        assert f"page.get_by_role('button',name='{label}').click()" not in browser
    assert 'Review health profiles' in source('web/app/components/doctor-visuals-v35.tsx')
