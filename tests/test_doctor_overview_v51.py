"""Source-only guardrails: one honest new Doctor summary without altering original datasets."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def source(p):return (ROOT/p).read_text(encoding='utf8')

def test_fictional_summary_is_separate_from_real_aggregate():
    demo=json.loads(source('web/app/data/interview-benchmark-v47.json'))
    real=json.loads(source('web/app/data/real-mobility-summary-v49.json'))
    assert demo['person_level_real_data_used'] is False and demo['clinical_prediction'] is False
    assert len(demo['fictional_examples'])==8
    assert sum(p['adl_limitations']>0 for p in demo['fictional_examples'])==3
    assert sum(p['adl_limitations']>=2 for p in demo['fictional_examples'])==1
    assert real['cohorts']['2015-2016']['questionnaire_respondents']==985
    assert real['cohorts']['2017-2018']['questionnaire_respondents']==1032
    assert real['evaluation']['roc_auc']==.73201
    assert real['boundaries']['future_frailty_prediction'] is False

def test_doctor_main_prioritizes_generated_examples_and_real_aggregate_boundary():
    ui=source('web/app/components/doctor-overview-v51.tsx')
    assert 'interview-benchmark-v47.json' in ui
    assert 'real-mobility-summary-v49.json' in ui
    for label in ('SIMULATED DATA','REAL PUBLIC SURVEY','clinical alerts','No earlier visits',
                  'previously inspected','artificial','unweighted','No HUNT'):
        assert label.lower() in ui.lower(),label
    for forbidden in ('localStorage','sessionStorage','/api/inference', 'patient_id', 'SEQN',
                      'fetch(', 'method: \'POST\''):
        assert forbidden not in ui
    assert 'DoctorOverviewV51' in source('web/app/doctor/page.tsx')
    assert 'ClinicalWorkspace' in source('web/app/doctor/workspace/page.tsx')
    assert 'AdminResearchHub' in source('web/app/admin/page.tsx')
    assert "redirect('/doctor')" in source('web/app/page.tsx')
    assert "redirect('/doctor')" in source('web/app/interview/page.tsx')
    nav=source('web/app/components/site-header.tsx')
    assert 'href="/doctor"' in nav and 'href="/admin"' in nav
    assert 'Interview focus' not in nav
    assert 'doctor-overview-v51.css' in source('web/app/layout.tsx')
    css=source('web/app/doctor-overview-v51.css')
    assert 'prefers-reduced-motion' in css and 'focus-visible' in css


def test_polished_doctor_view_uses_only_existing_examples_and_neutral_indicators():
    ui=source('web/app/components/doctor-overview-v51.tsx')
    header=source('web/app/components/site-header.tsx')
    css=source('web/app/doctor-overview-v51.css')
    for term in ('nWithOneADL','nWithoutADL','d51-ring','d51-score-dial',
                 'd51-filter-bar',"filter==='none'",'No earlier visits',
                 'Research interpretation and limitations','PUBLIC AGGREGATES'):
        assert term in ui,term
    for unwanted in ('Explore more, without clutter.',
                     'The original technical Doctor workspace remains',
                     'you asked', 'as requested', 'ChatGPT', 'Claude'):
        assert unwanted.lower() not in ui.lower(),unwanted
    assert 'RESEARCH DEMO' not in header
    assert 'Interview focus' not in header
    assert 'prefers-reduced-motion' in css and 'focus-visible' in css
    assert 'ClinicalWorkspace' in source('web/app/doctor/workspace/page.tsx')
    assert 'AdminResearchHub' in source('web/app/admin/page.tsx')
    assert 'No HUNT' in ui and 'unweighted' in ui
