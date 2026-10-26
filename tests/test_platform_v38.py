"""Synthetic model reproducibility, immutable clinical boundaries and CI release rules."""
import json
import math
import sys
from pathlib import Path
from subprocess import run

ROOT=Path(__file__).resolve().parents[1]
def src(path):return (ROOT/path).read_text(encoding='utf-8')

def test_synthetic_fitted_registry_is_reproducible():
    result=run([sys.executable,'scripts/build_fictional_models_v38.py','--check'],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0, result.stdout+result.stderr
    reg=json.loads(src('web/app/data/fictional-model-registry-v38.json'))
    assert reg['schema']=='FRAILTYSCOPE_FICTIONAL_MULTI_OUTCOME_V38'
    assert reg['provenance']=='SYNTHETIC_GENERATED_ONLY'
    assert reg['training']['generated_records']==1200
    assert not reg['training']['any_real_participants']
    assert reg['clinical_use_permitted'] is False
    assert reg['independent_clinical_validation'] is False
    assert len(reg['models'])==3
    for model in reg['models']:
        assert not model['outcome_is_real'] and not model['clinical_use_permitted']
        assert model['trained_on']=='generated_fictional_examples'
        assert set(model['weights'])==set(reg['features'])
        assert all(math.isfinite(v) for v in model['weights'].values())
        assert math.isfinite(model['intercept'])

def test_real_historical_case_stays_disabled_and_no_artifact_serving():
    c=json.loads(src('research/cases/nhanes_workflow_v29.json'))
    for field in ('clinical_use_permitted','model_fitting_permitted','holdout_scoring_permitted',
      'predictions_exported','models_saved','independent_validation','real_data_execution_permitted'):
        assert c[field] is False
    api=src('web/app/api/inference/route.ts')
    for literal in ('BLOCKED_FOR_NEW_ANALYSIS','clinical_inference:false','registered_clinical_models:0',
         'status:403','no-store','export async function POST','export async function GET'):
        assert literal in api
    for unsafe in ('request.json(', 'request.text(', 'predict_proba(', 'fs.', 'MODEL_PATH',
       'process.env.', 'console.log(', 'cookies(', 'headers('): assert unsafe not in api

def test_browser_does_not_send_personal_profile_to_synthetic_lab():
    page=src('web/app/components/clinical-workspace.tsx')
    lab=src('web/app/components/multioutcome-lab-v38.tsx')
    assert '<ClinicalOutcomeRegistryV38/>' in page
    assert '<FictionalMultiOutcomeLabV38/>' in page
    assert 'FictionalMultiOutcomeLabV38 profile=' not in page
    assert 'FictionalMultiOutcomeLabV38(){' in lab
    for marker in ('trained_on','registry.models.map','contribution:signals[key]*model.weights[key]',
       'sigmoid(logit)','Reset fictional example','Invented outcome','NOT PATIENT PREDICTIONS',
       'not SHAP','never receives Patient Assessment state'):
        assert marker in (lab+src('web/app/data/fictional-model-registry-v38.json'))
    for unsafe in ('fetch(', 'localStorage', 'sessionStorage', 'XMLHttpRequest', '/api/inference',
       'profile:', 'patientId', 'patient_id','nhanes-aggregate.json'):
        assert unsafe not in lab

def test_ci_uses_installed_chrome_without_network_browser_download():
    ci=src('.github/workflows/ci.yml')
    assert 'FRAILTYSCOPE_QA_CHROMIUM: /usr/bin/google-chrome' in ci
    assert 'test -x /usr/bin/google-chrome' in ci
    assert 'python -m playwright install chromium' not in ci
    assert 'tests/test_platform_v38.py' in ci
    assert 'tests/browser_platform_v38.py' in src('scripts/run_browser_qa_v34.sh')
    for fn in ('browser_doctor_v35.py','browser_doctor_v36.py','browser_inference_v37.py'):
        assert 'FRAILTYSCOPE_QA_CHROMIUM' in src('tests/'+fn)
    assert "'FRAILTYSCOPE_QA_CHROMIUM'" in src('tests/test_demo_qa_v34.py')
    assert "'FRAILTYSCOPE_QA_CHROMIUM'" in src('tests/test_doctor_v35.py')

def test_all_existing_doctor_sections_preserved():
    page=src('web/app/components/clinical-workspace.tsx')
    for term in ('Patient assessment','Visit history','Health profiles','Population overview',
       'Model evidence','Use assessment measurements','<InferenceReadinessV37',
       '<FictionalScoringLabV37','<DoctorJourneyV36','Data are cleared when the page reloads.'):
        assert term in page
    assert "import '../inference-v38.css';" in src('web/app/archive/layout.tsx')
    css=src('web/app/inference-v38.css')
    assert 'prefers-reduced-motion' in css and 'focus-visible' in css
