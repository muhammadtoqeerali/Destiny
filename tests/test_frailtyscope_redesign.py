"""Focused visual frontend source contracts; preserves the original scientific boundaries."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def read(p):return (ROOT/p).read_text(encoding='utf-8')

def test_two_clear_navigation_choices_and_old_links_redirect():
    header=read('web/app/components/site-header.tsx')
    assert 'href="/doctor"' in header and 'href="/admin"' in header
    assert 'href="/interview"' not in header
    assert 'Interview focus' not in header
    assert "redirect('/doctor')" in read('web/app/page.tsx')
    assert "redirect('/doctor')" in read('web/app/interview/page.tsx')
    assert "redirect('/admin')" in read('web/app/admin/interview/page.tsx')
    assert (ROOT/'web/app/archive/doctor/page.tsx').is_file()
    assert (ROOT/'web/app/archive/admin/page.tsx').is_file()
    assert 'ClinicalWorkspace' in read('web/app/archive/doctor/page.tsx')
    assert 'AdminResearchHub' in read('web/app/archive/admin/page.tsx')

def test_doctor_is_concise_but_has_real_context_and_fictional_journey():
    ui=read('web/app/components/doctor-focus-v50.tsx')
    for required in ('Real NHANES data','Fictional examples only','Health history available',
                     'Current fictional snapshot','Illustrative future outcome',
                     'Earlier dated visit records:','not available in this demonstrator',
                     'Not a clinical risk estimate','not a patient','aria-pressed',
                     'aria-expanded','synthetic model','observed_demo_outcome'):
        assert required.lower() in ui.lower(),required
    assert 'real-mobility-summary-v49.json' in ui
    assert 'interview-benchmark-v47.json' in ui
    assert 'threshold' not in ui.lower() or 'medical categories' in ui.lower()
    assert 'future frailty prediction' not in ui.lower()
    assert 'reported difficulty' in ui.lower()
    for forbidden in ('fetch(', 'localStorage', 'sessionStorage', 'patient_id', 'SEQN', 'method:'):
        assert forbidden not in ui

def test_research_presents_fair_metric_switching_without_new_models():
    ui=read('web/app/components/research-focus-v50.tsx')
    for word in ('validation_brier','cv_brier','validation_auc','CatBoost','Logistic regression',
                 'permutation_importance','calibration','later cycle','not untouched',
                 'No longitudinal future frailty prediction', 'not medical causes'):
        assert word.lower() in ui.lower(),word
    assert 'real-mobility-summary-v49.json' in ui
    assert 'interview-benchmark-v47.json' not in ui
    for forbidden in ('fetch(', 'localStorage','sessionStorage','patient_id','SEQN','predict_proba('):
        assert forbidden not in ui

def test_data_are_reused_not_rewritten_and_auth_unchanged():
    data=json.loads(read('web/app/data/real-mobility-summary-v49.json'))
    assert data['selected_model']=='CatBoost'
    assert data['evaluation']['roc_auc']==.73201
    assert data['cohorts']['2017-2018']['questionnaire_respondents']==1032
    assert 'canViewPublicDashboard()' in read('web/app/admin/page.tsx')
    assert "redirect('/admin/login')" in read('web/app/admin/page.tsx')
    assert 'canViewPublicDashboard()' in read('web/app/archive/admin/page.tsx')
    assert 'status:403' in read('web/app/api/inference/route.ts')

def test_design_has_mobile_and_reduced_motion_and_legacy_isolated():
    css=read('web/app/focus-v50.css')
    for token in ('@media(max-width:570px)','@media(max-width:800px)',
                  'prefers-reduced-motion:reduce','focus-visible','.focus-ring',
                  '.focus-case-layout','.focus-research-panel'):
        assert token in css
    layout=read('web/app/layout.tsx')
    assert "import './focus-v50.css';" in layout
    assert 'href="#main"' in layout
    assert "import './doctor-v35.css';" not in layout
    legacy=read('web/app/archive/layout.tsx')
    assert "import '../doctor-v35.css';" in legacy
    assert "import '../study-handoff-v44.css';" in legacy
    qa=read('scripts/run_browser_qa_v34.sh')
    assert 'tests/browser_frailtyscope_redesign.py' in qa
    assert 'tests/browser_doctor_v35.py' in qa
