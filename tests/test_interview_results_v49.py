"""Source-only release regression and fully invented aggregate fixtures; no NHANES rows."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from ml.interview_results_v49 import ROOT, SUMMARY, CASE, Refused, check_public, compare, read_public,verify_local
from scripts.patch_interview_results_v49 import PATCHES, transform

P=read_public(ROOT)

def synthetic_aggregate():
    """Construct aggregate-only invented report shape, never load a public participant table."""
    return {'schema':'FRAILTYSCOPE_PUBLIC_NHANES_MOBILITY_V48','case_id':CASE,
        'clinical_prediction_permitted':False,
        'task':'CROSS_SECTIONAL_CURRENT_MOBILITY_LIMITATION_NOT_FUTURE',
        'cohorts':{k:{**v,'phq9_valid_complete_n':P['phq9_complete'][k]} for k,v in P['cohorts'].items()},
        'experiment':{'later_cycle_prior_exposure':'V48_PREVIOUSLY_INSPECTED_NOT_FRESH',
         'selected_model':P['selected_model'],
         'feature_availability_contract':{'included_predictors':P['predictors'],'excluded_predictors':[]},
         'split':P['split'],
         'model_comparison_development_only':[{'model':m['name'],'cv_brier':m['cv_brier'],
            'validation':{'roc_auc':m['validation_auc'],'brier':m['validation_brier']},
            'hyperparameters':m['hyperparameters']} for m in P['models']],
         'selected_model_later_cycle_test':P['evaluation'],
         'test_calibration_bands_min_n_50':P['calibration'],
         'validation_permutation_importance_delta_brier':[
            {'feature':x['feature'],'brier_increase':x['delta_brier'],'std':x['std']}
            for x in P['permutation_importance']],
         'test_naive_row_bootstrap_95pct_not_survey_design_CI':P['naive_row_bootstrap_95pct'],
         'test_survey_weighted_brier_exploratory':{
            'n_positive_weights':P['survey_weighted_brier_exploratory']['n_positive_weights'],
            'brier_exploratory_only':P['survey_weighted_brier_exploratory']['brier'],
            'survey_design_variance_not_estimated':True},
       }}

def test_public_summary_is_only_aggregates_and_locked():
    check_public(P)
    assert P['cohorts']['2015-2016']['questionnaire_respondents']==985
    assert P['cohorts']['2017-2018']['target_events']==278
    assert P['evaluation']['roc_auc']==.73201
    assert P['selection_metric']=='LOWEST_VALIDATION_BRIER'
    assert P['unshown_calibration_n']==43
    assert P['basis'].startswith('USER_SUPPLIED_AGGREGATE_EXCERPT')
    for prohibited in ('SEQN','patient_id','source_sha256','raw_predictions','person_record',
                       'participant_row','date_of_birth'):
        assert prohibited not in (ROOT/SUMMARY).read_text()

def test_local_aggregate_comparison_complete_and_strict():
    fake=synthetic_aggregate()
    compare(P,fake)
    with TemporaryDirectory(prefix='v49-public-aggregate-') as d:
        path=Path(d)/'aggregate.json'
        path.write_text(json.dumps(fake))
        verify_local(ROOT,path)
    variations=[('wrong outcome',lambda x:x.update(task='PROSPECTIVE_FRAILTY')),
      ('winner',lambda x:x['experiment'].update(selected_model='Random forest')),
      ('wrong AUC',lambda x:x['experiment']['selected_model_later_cycle_test'].update(roc_auc=.90)),
      ('wrong PHQ count',lambda x:x['cohorts']['2015-2016'].update(phq9_valid_complete_n=3)),
      ('wrong validation',lambda x:x['experiment']['model_comparison_development_only'][0]['validation'].update(brier=.10)),
      ('wrong weights',lambda x:x['experiment']['test_survey_weighted_brier_exploratory'].update(brier_exploratory_only=.1)),
      ('erased prior exposure',lambda x:x['experiment'].update(later_cycle_prior_exposure='FRESH_UNTOUCHED'))]
    for label,mutator in variations:
        m=deepcopy(fake)
        mutator(m)
        with pytest.raises(Refused):compare(P,m)

def test_reject_future_claim_or_survey_design_claim():
    for k,v in [('future_frailty_prediction',True),('clinical_prediction',True),
                ('survey_design_variance_estimated',True),('later_cycle_previously_inspected',False)]:
        x=deepcopy(P);x['boundaries'][k]=v
        with pytest.raises(Refused):check_public(x)

def test_reject_private_fields_and_small_calibration_bins():
    for mutation in ('person','small','missing','wrong selected'):
        x=deepcopy(P)
        if mutation=='person':x['patient_id']='unknown'
        if mutation=='small':x['calibration'][0]['n']=6
        if mutation=='missing':x['phq9_complete']['2017-2018']=0
        if mutation=='wrong selected':x['selected_model']='Random forest'
        with pytest.raises(Refused):check_public(x)

def test_private_aggregate_inside_repo_is_rejected():
    with pytest.raises(Refused,match='outside'):
        verify_local(ROOT,ROOT/SUMMARY)

def test_published_baseline_patch_anchors():
    original=(ROOT/'web/app/components/interview-focus-v47.tsx').read_text()
    for expected in ('<RealMobilityDoctorV49/>',"dataset==='mobility'&&<RealMobilityAdminV49/>",
                     "dataset==='synthetic'", "dataset==='nhanes'", "dataset==='nhats'",
                     "dataset==='share'", "dataset==='hunt'", 'No data entry or patient registration'):
        assert expected in original
    for source,pairs in PATCHES.items():
        content=(ROOT/source).read_text()
        for _,new in pairs: assert new in content,source
    ui=(ROOT/'web/app/components/real-mobility-v49.tsx').read_text()
    for word in ('RealMobilityDoctorV49','RealMobilityAdminV49','2017–2018','not an untouched independent test',
                 'Permutation importance','current walking difficulty'):
        assert word.lower() in ui.lower(),word
    assert 'clinical_prediction' in (ROOT/SUMMARY).read_text()
    for word in ('fetch(','localStorage','sessionStorage','patient_id','SEQN','POST', 'predict_proba('):
        assert word not in ui
    # The new real-data snapshot must not change the index of the existing
    # two fictional profile cards expected by the unmodified v0.47 browser QA.
    assert 'className="v49-doctor-evidence"' in ui
    assert 'className="if-card v49-doctor-evidence"' not in ui
    styles=(ROOT/'web/app/interview-results-v49.css').read_text()
    assert '.v49-doctor-evidence{border:1px' in styles
    assert "import './interview-results-v49.css';" in (ROOT/'web/app/layout.tsx').read_text()
    assert 'tests/browser_interview_results_v49.py' in (ROOT/'scripts/run_browser_qa_v34.sh').read_text()
    assert 'tests/test_public_mobility_v48.py' in (ROOT/'.github/workflows/ci.yml').read_text()
    assert 'tests/test_interview_results_v49.py' in (ROOT/'.github/workflows/ci.yml').read_text()
    assert 'status:403' in (ROOT/'web/app/api/inference/route.ts').read_text()


def test_installer_preflight_uses_explicit_bundled_source_before_installation():
    install=(ROOT/'scripts/install_interview_results_v49.sh').read_text()
    assert '.venv/bin/python "$BUNDLE/ml/interview_results_v49.py" --root "$BUNDLE" --check-public' in install
    assert '.venv/bin/python "$BUNDLE/ml/interview_results_v49.py" --root "$BUNDLE" --verify-local "$AGG"' in install
    assert 'PYTHONPATH="$BUNDLE" .venv/bin/python -m ml.interview_results_v49' not in install


def test_browser_login_server_action_finishes_before_admin_navigation():
    qa=(ROOT/'tests/browser_interview_results_v49.py').read_text()
    submit="page.get_by_role('button',name=re.compile('Open research workspace')).click()"
    redirect="expect(page).to_have_url(re.compile(r'/admin/?(?:\\?.*)?$'),timeout=15000)"
    destination="page.goto(BASE+'/admin/interview',wait_until='domcontentloaded')"
    assert qa.count(submit)==1 and qa.count(redirect)==1 and qa.count(destination)==2
    # The login action redirects first to /admin; an early goto loses the session.
    assert qa.index(submit)<qa.index(redirect)<qa.rindex(destination)
    assert "expect(page).to_have_url(re.compile(r'/admin/interview/?$'))" in qa
    assert "name='Real NHANES mobility experiment results'" in qa
