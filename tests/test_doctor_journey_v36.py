"""v0.36 tests: proof of descriptive-only frontend, privacy and explanation boundaries."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def src(p):return (ROOT/p).read_text(encoding='utf-8')

def test_assessment_has_live_display_and_reuses_only_valid_local_measurements():
    page=src('web/app/components/clinical-workspace.tsx')
    for marker in ('<DoctorJourneyV36 profile={profile} visits={visits}',
       'Use assessment measurements','setVisitBmi(isValidAssessment','setVisitPhq(isValidAssessment',
       '<FollowUpSummaryV36 visits={visits}/>','<PredictionStoryV36 profile={profile}/>'):
        assert marker in page
    assert 'Data are cleared when the page reloads.' in page
    assert 'No records are fetched from a database' in page

def test_new_component_is_observational_and_cannot_claim_predicted_probabilities():
    ui=src('web/app/components/doctor-journey-v36.tsx')
    for required in ('Browser session only','No model is fitted, loaded or queried',
                     'Individual inference not enabled','No patient prediction is calculated',
                     'not an actual explanation of a patient-specific prediction',
                     'Not enough visits','Two dated measurements','Nonparticipation',
                     'animation', 'Pause motion','Resume motion', 'aria-current',
                     'prefers-reduced-motion'):
        # reduced motion appears in stylesheet, not component
        assert required in (ui+src('web/app/doctor-journey-v36.css'))
    for forbidden in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage',
                      'predict_proba(', 'model.fit(', 'submit(', '/api/predict',
                      'model.joblib', 'patient_id', 'local_examples'):
        assert forbidden not in ui

def test_doctor_model_details_replaced_with_clear_animated_workflow():
    page=src('web/app/components/clinical-workspace.tsx')
    assert 'Understand the model evidence' not in page
    assert 'How an assessment becomes an explanation' in page
    assert 'Predicted versus observed frequencies' not in page
    assert 'Understanding the classification counts' not in page
    assert 'Individual inference is still disabled' not in page or 'Individual inference not enabled' in src('web/app/components/doctor-journey-v36.tsx')

def test_browser_contracts_and_accessibility_controls():
    old=src('tests/browser_doctor_v35.py')
    original=src('tests/browser_qa_v34.py')
    runner=src('scripts/run_browser_qa_v34.sh')
    for x in (old,original): assert 'How an assessment becomes an explanation' in x
    assert 'tests/browser_doctor_v36.py' in runner
    browser=src('tests/browser_doctor_v36.py')
    for x in ('desktop','mobile','Pause motion','Next step','Use assessment measurements',
              'How an assessment becomes an explanation','reload','Browser session only'):
        assert x in browser
    css=src('web/app/doctor-journey-v36.css')
    assert '@media(prefers-reduced-motion:reduce)' in css and 'focus-visible' in css
    assert "import '../doctor-journey-v36.css';" in src('web/app/archive/layout.tsx')
    assert 'tests/test_doctor_journey_v36.py' in src('.github/workflows/ci.yml')

def test_original_case_has_no_approval_for_new_inference():
    c=json.loads(src('research/cases/nhanes_workflow_v29.json'))
    assert c['real_data_execution_permitted'] is False
    assert c['model_fitting_permitted'] is False
    assert c['public_export_permitted'] is False
