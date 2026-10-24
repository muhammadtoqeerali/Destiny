"""Interview-only synthetic data, separated datasets and front end. No private data access."""
from pathlib import Path
import json
import numpy as np
from ml.interview_benchmark_v47 import (FEATURES,NAMES,OUTPUT,generated,split,pipeline,models,
     metrics,report,serialized,check_fixture)

ROOT=Path(__file__).resolve().parents[1]
def src(p):return (ROOT/p).read_text(encoding='utf8')

def test_synthetic_replay_is_exact_and_contains_no_real_data():
    a=report();b=report()
    assert a==b
    check_fixture(json.loads(src(OUTPUT)),a)
    assert a['clinical_prediction'] is False
    assert a['person_level_real_data_used'] is False
    assert a['source']=='GENERATED_FICTIONAL_AGEING_COHORT_NOT_HUNT_NHATS_OR_NHANES'
    assert a['configuration']['generation_n']==1800
    assert [m['name'] for m in a['models']]==NAMES
    assert len(a['fictional_examples'])==8
    assert all(len(x['illustrative_factors'])==4 for x in a['fictional_examples'])
    assert all(x['id'].startswith('FICTIONAL-') and 0<=x['fictional_model_probability']<=1
               and type(x['current_conditions']) is list for x in a['fictional_examples'])

def test_training_validation_testing_have_no_group_overlap():
    df=generated();tr,va,te=split(df)
    ids=[set(df['fictional_id'].iloc[ix]) for ix in (tr,va,te)]
    assert all(not ids[i].intersection(ids[j]) for i in range(3) for j in range(i+1,3))
    assert [len(x) for x in (tr,va,te)]==[1080,360,360]
    assert 'future_adl_decline_demo' not in FEATURES and 'fictional_id' not in FEATURES

def test_models_are_fitted_on_training_subset_only():
    df=generated();tr,va,te=split(df)
    learner=pipeline(models()[1]); y=df['future_adl_decline_demo'].to_numpy()
    learner.fit(df.iloc[tr][FEATURES],y[tr]);p=learner.predict_proba(df.iloc[va][FEATURES])[:,1]
    assert p.shape==(360,) and np.all(np.isfinite(p))
    scores=metrics(y[va],p)
    assert 0<=scores['brier']<=1
    assert 'transform' in learner.named_steps and 'model' in learner.named_steps
    assert len(te)==360

def test_selects_only_on_validation_not_test():
    d=report()
    selected=min(d['models'],key=lambda m:(m['validation']['brier'],NAMES.index(m['name'])))
    assert d['selected_model']==selected['name']
    assert d['selected_validation']==selected['validation']
    assert d['synthetic_test']!=d['selected_validation']
    assert sum(b['count'] for b in d['calibration'])==d['configuration']['test_n']

def test_web_views_are_simple_separate_and_protected():
    ui=src('web/app/components/interview-focus-v47.tsx')
    assert 'InterviewDoctorV47' in ui and 'InterviewAdminV47' in ui
    assert "dataset==='nhanes'" in ui and "dataset==='synthetic'" in ui
    assert "dataset==='nhats'" in ui and "dataset==='share'" in ui
    assert "dataset==='hunt'" in ui
    assert 'future ADL' in ui or 'ADL decline' in ui
    assert 'Fictional' in ui or 'fictional' in ui
    assert "from '../data/interview-benchmark-v47.json'" in ui
    assert 'No data entry or patient registration' in ui
    assert 'SHAP or causal claims' not in ui
    for forbidden in ('localStorage','sessionStorage',"method:'POST'",'request.json(',
                      'patient_id','SEQN','fetch('):assert forbidden not in ui
    page=src('web/app/admin/interview/page.tsx')
    assert 'canViewPublicDashboard' in page and "redirect('/admin/login')" in page
    assert 'status:403' in src('web/app/api/inference/route.ts')
    css=src('web/app/interview-focus-v47.css')
    assert 'prefers-reduced-motion' in css and 'focus-visible' in css

def test_published_source_connectivity_preserves_legacy():
    header=src('web/app/components/site-header.tsx')
    assert 'href="/interview"' in header
    assert 'href="/doctor"' in header and 'href="/admin"' in header
    assert "redirect('/interview')" in src('web/app/page.tsx')
    assert "import './interview-focus-v47.css';" in src('web/app/layout.tsx')
    assert 'tests/browser_interview_focus_v47.py' in src('scripts/run_browser_qa_v34.sh')
    ci=src('.github/workflows/ci.yml')
    assert 'tests/test_interview_focus_v47.py' in ci
    assert 'python -m ml.interview_benchmark_v47 --check' in ci
    assert 'tests/test_study_activation_v46.py' in ci
    # Protect published old v0.37-v0.46 source contracts.
    from scripts.patch_handoff_v44 import PATCHES
    for path,pairs in PATCHES.items():
        original=src(path)
        for _,insert in pairs:assert insert in original
    from scripts.patch_validation_v41 import PATCHES as V41
    for path,pairs in V41.items():
        original=src(path)
        for _,insert in pairs:assert insert in original

def test_no_real_person_records_or_data_files_in_package():
    body=src(OUTPUT)
    for token in ('patient_id','SEQN','date_of_birth','HUNT_RESTRICTED_RECORD',
                  'clinical_prediction": true','person_level_real_data_used": true'):
        assert token not in body
    assert not (ROOT/'web/public/data/interview-patient-records.json').exists()
