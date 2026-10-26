"""No clinical inference or data network path added to the public Doctor Portal."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
def src(path):return (ROOT/path).read_text(encoding='utf-8')

def test_original_clinical_case_is_still_blocked():
    c=json.loads(src('research/cases/nhanes_workflow_v29.json'))
    assert c['clinical_use_permitted'] is False
    assert c['model_fitting_permitted'] is False
    assert c['public_export_permitted'] is False
    assert c['independent_validation'] is False
    assert c['predictions_exported'] is False
    assert c['models_saved'] is False

def test_real_assessment_cannot_be_scored():
    ui=src('web/app/components/inference-readiness-v37.tsx')
    for mark in ('Clinical inference blocked','patient predictions generated',
                 'BLOCKED_FOR_NEW_ANALYSIS','No entered values are transmitted',
                 'No approved, calibrated','11 of 14',
                 'Invented teaching label'.lower()):
        assert mark.lower() in ui.lower(),mark
    assert '<strong>0</strong><span>patient predictions generated</span>' in ui
    assert 'onExplore:()=>void' in ui
    for unsafe in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage',
                   'predict_proba(', 'model.fit(', '/api/predict', '/api/inference',
                   'nhanes-aggregate.json', 'nhanes-refinement.json', 'SEQN',
                   'ADMIN_PORTAL_PASSWORD', 'process.env.'):
        assert unsafe not in ui,unsafe

def test_synthetic_math_and_actual_formula_explanation():
    ui=src('web/app/components/inference-readiness-v37.tsx')
    for mark in ('Math.exp(-z)','useMemo(','exampleMath(',
                 'BASE=-0.55','(age-75)*0.035','(bmi-26)*0.08',
                 'SYNTHETIC / NOT CLINICAL','not death, disease, frailty',
                 'not a medical probability','aria-valuenow={score}',
                 'Reset fictional example','not SHAP', 'fictional inputs are separate'):
        assert mark.lower() in ui.lower(),mark
    assert 'profile={profile}' not in ui

def test_source_integration_and_browser_contracts():
    page=src('web/app/components/clinical-workspace.tsx')
    assert '<InferenceReadinessV37 profile={profile}' in page
    assert '<FictionalScoringLabV37/>' in page
    assert page.count('<PredictionStoryV36 profile={profile}/>')==1
    assert 'Use assessment measurements' in page
    assert "import './inference-v37.css';" in src('web/app/layout.tsx')
    browser=src('tests/browser_inference_v37.py')
    for mark in ('desktop','mobile','Fictional age','Reset fictional example',
                 'Clinical inference blocked','api/predict', '127\\.0\\.0\\.1'):
        assert mark in browser
    assert 'tests/browser_inference_v37.py' in src('scripts/run_browser_qa_v34.sh')
    assert 'tests/test_runtime_gate_v37.py' in src('.github/workflows/ci.yml')

def test_no_private_training_material_published():
    assert src('web/app/components/inference-readiness-v37.tsx').count('predict_proba(')==0
    assert src('web/app/components/inference-readiness-v37.tsx').count('patient_id')==0
    doc=src('research/INFERENCE_READINESS_V37.md')
    assert 'no clinical inference' in doc.lower()
    assert 'synthetic' in doc.lower()
