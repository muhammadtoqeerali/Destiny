"""v0.23: metadata-only, synthetic fixtures; no real source rows or model fitting."""
import copy
import json
from pathlib import Path

import pytest

from ml.case_dictionary_timing_v23 import (
    SCHEMA,AVAILABILITY,DANGEROUS_SOURCE_COLUMNS,local_path,evidence_ref,
    validate_protocol,make_plan,digest,verify_prior_ledger
)


def fixture():
    m={'case_id':'synthetic_case','id_column':'ID','target':'event_5yr',
       'features':{'numeric':['age','bmi'],'categorical':['sex']}}
    p={'case_id':'synthetic_case','holdout_history':'previously_inspected',
       'prior_exploration':True}
    base={'kind':'numeric','source_file':'DEMO_G.XPT','source_variables':['RIDAGEYR'],
          'units':'years','measurement_phase':'household_interview',
          'availability_status':'pending_index_review',
          'source_timing_verified_by_study_team':False,
          'transformation':'Age is numeric; no post-index transformations.',
          'missing_semantics':'All not-reported codes require review.',
          'timing_rationale':'Prediction time and extraction chronology not yet verified.',
          'evidence':['https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/DEMO_G.htm']}
    cfg={'schema':SCHEMA,'case_id':'synthetic_case',
         'case_manifest':'research/cases/synthetic_case.json',
         'related_v22_protocol':'research/cases/synthetic_v22.json',
         'related_private_v22_ledger':'artifacts/cases/example/ledger.json',
         'holdout_history':'previously_inspected','prior_exploration':True,
         'allow_model_fitting':False,'allow_heldout_scoring':False,
         'allow_clinical_inference':False,
         'prediction_index':{'event':'Completion of the baseline examination',
              'population':'Older adults with examination','definition_status':'provisional',
              'approved_by_study_team':False,'evidence':['research/FEATURE_AVAILABILITY_V23.md']},
         'predictors':{key:copy.deepcopy(base) for key in ('age','bmi','sex')}}
    return cfg,m,p


def test_fixture_blocks_all_unverified_features():
    c,m,p=fixture(); validate_protocol(c,m,p)
    z=make_plan(c)
    assert z['features_total']==3 and len(z['unresolved_predictors'])==3
    assert z['availability_counts']['pending_index_review']==3
    assert z['route']=='BLOCKED_FOR_PREDICTION_PROTOCOL_REVIEW'
    assert z['no_data_rows_opened'] is True and z['no_models_fitted'] is True
    assert z['no_holdout_targets_accessed'] is True


@pytest.mark.parametrize('field,bad',[
 ('allow_model_fitting',True),('allow_heldout_scoring',True),('allow_clinical_inference',True),
 ('holdout_history','locked_new'),('prior_exploration',False),
 ('schema','other'),('case_id','different')])
def test_blocked_protocol_claims(field,bad):
    c,m,p=fixture();c[field]=bad
    with pytest.raises(ValueError):validate_protocol(c,m,p)


def test_omitting_predictor_blocked():
    c,m,p=fixture(); del c['predictors']['age']
    with pytest.raises(ValueError,match='EXACTLY'):validate_protocol(c,m,p)


def test_extra_target_as_predictor_blocked():
    c,m,p=fixture();c['predictors']['event_5yr']=copy.deepcopy(c['predictors']['age'])
    with pytest.raises(ValueError):validate_protocol(c,m,p)


@pytest.mark.parametrize('var',sorted(DANGEROUS_SOURCE_COLUMNS))
def test_leakage_source_variables_blocked(var):
    c,m,p=fixture(); c['predictors']['age']['source_variables']=[var]
    with pytest.raises(ValueError,match='Outcome'):validate_protocol(c,m,p)


@pytest.mark.parametrize('field,bad',[('measurement_phase','future_mec'),
 ('availability_status','safe_by_guess'),('kind','magical'),('units',''),
 ('source_variables',[]),('source_file','../../file.csv'),
 ('missing_semantics','guess'),('timing_rationale','no'),('evidence',[])])
def test_bad_dictionary_item_blocked(field,bad):
    c,m,p=fixture();c['predictors']['bmi'][field]=bad
    with pytest.raises(ValueError):validate_protocol(c,m,p)


def test_cannot_claim_verified_without_study_approved_index():
    c,m,p=fixture();c['predictors']['age']['availability_status']='verified_at_or_before_index'
    c['predictors']['age']['source_timing_verified_by_study_team']=True
    with pytest.raises(ValueError,match='index'):validate_protocol(c,m,p)


def test_index_approved_still_requires_individual_feature_review():
    c,m,p=fixture()
    c['prediction_index']['definition_status']='operationally_verified'
    c['prediction_index']['approved_by_study_team']=True
    c['predictors']['age']['availability_status']='verified_at_or_before_index'
    with pytest.raises(ValueError,match='per-predictor'):validate_protocol(c,m,p)
    c['predictors']['age']['source_timing_verified_by_study_team']=True
    validate_protocol(c,m,p)
    assert make_plan(c)['unresolved_predictors']==['bmi','sex']


def test_prohibited_timing_cannot_be_marked_verified():
    c,m,p=fixture()
    c['predictors']['age']['availability_status']='known_after_index'
    c['predictors']['age']['source_timing_verified_by_study_team']=True
    with pytest.raises(ValueError):validate_protocol(c,m,p)


def test_previously_inspected_holdout_always_honored():
    c,m,p=fixture()
    c['prediction_index']['definition_status']='operationally_verified'
    c['prediction_index']['approved_by_study_team']=True
    for item in c['predictors'].values():
        item['availability_status']='verified_at_or_before_index'
        item['source_timing_verified_by_study_team']=True
    validate_protocol(c,m,p)
    assert make_plan(c)['route']=='BLOCKED_FOR_PREDICTION_PROTOCOL_REVIEW'


@pytest.mark.parametrize('ref',[ 'data/raw/people.csv','/etc/passwd',
   'research/../data/private.csv','http://insecure.test/codebook',
   'https://u:p@somewhere.com/data','scripts\\bad.sh' ])
def test_forbidden_evidence_reference(ref):
    with pytest.raises(ValueError):evidence_ref(ref)


def test_allowed_https_codebook_and_sources():
    evidence_ref('https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/PFQ_G.htm')
    evidence_ref('ml/realdata_nhanes.py')


def test_safe_project_path_and_traversal(tmp_path):
    r=tmp_path; (r/'research').mkdir();(r/'research/a.json').write_text('{}')
    assert local_path(r,'research/a.json','research').name=='a.json'
    with pytest.raises(ValueError):local_path(r,'research/../../private.csv','research')
    with pytest.raises(ValueError):local_path(r,'data/a.csv','research')


def test_no_old_ledger_or_data_read_in_plan():
    c,m,p=fixture()
    assert make_plan(c)['no_data_rows_opened']
    assert 'previous_private_ledger_metadata' not in make_plan(c)


def test_private_ledger_cannot_read_csv(tmp_path):
    c,_,p=fixture()
    r=tmp_path/'artifacts/cases/example';r.mkdir(parents=True)
    (r/'ledger.json').write_text('invalid')
    with pytest.raises((ValueError,ImportError,ModuleNotFoundError)):
        verify_prior_ledger({**c,'related_private_v22_ledger':'artifacts/cases/example/ledger.csv'},tmp_path,p)


def test_json_digest_stable_across_key_order():
    assert digest({'a':1,'b':2})==digest({'b':2,'a':1})


def test_import_only_has_no_fitted_model():
    import ml.case_dictionary_timing_v23 as module
    assert callable(module.make_plan) and not hasattr(module,'fitted_model')
