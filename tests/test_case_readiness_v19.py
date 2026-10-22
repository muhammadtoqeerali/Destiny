"""Synthetic data and pure contracts only. NEVER fit research models or read NHANES."""
import copy
import math
import pandas as pd
import pytest
from ml.case_readiness_v19 import (
    SCHEMA, REPORT_SCHEMA, validate_contract, canonical_hash, audit_table,
    validate_report, _missingness_profile)


def config():
    return {
        'schema':SCHEMA, 'case_id':'synthetic_intake',
        'source':{'path':'data/processed/synthetic.csv','expected_sha256':None},
        'id_column':'person', 'target':'five_year_label',
        'features':{'numeric':['age','walking'],'categorical':['sex']},
        'split':{'design':'cohort','column':'cycle','development':'early',
                 'holdout':'later','holdout_status':'previously_inspected'},
        'outcome':{'type':'binary_fixed_horizon','index_time':'baseline',
                   'prediction_horizon':'5y','label_followup_status':'unverified'},
        'records':{'grain':'one_record_per_person','time_column':None,'group_column':None},
        'missingness_semantics':{'walking':{'status':'unverified','evidence_reference':''}},
        'numeric_bounds':{'age':[65,90],'walking':[1,4]},
        'post_index_columns':[], 'post_hoc_development_exploration':True,
        'min_reporting_n':20
    }


def cohort(n=60):
    d=pd.DataFrame({'person':range(n+22),
        'cycle':['early']*n+['later']*22,
        'age':[70+(i%10) for i in range(n+22)],
        'walking':[None if i%4==0 else 2 for i in range(n+22)],
        'sex':['F' if i%2 else 'M' for i in range(n+22)],
        'five_year_label':[int(i%5==0) for i in range(n)]+['UNOBSERVED_SECRET']*22})
    return d


def test_valid_and_hash_order():
    c=config()
    assert validate_contract(c) is c
    assert canonical_hash({'z':1,'a':2})==canonical_hash({'a':2,'z':1})
    assert canonical_hash({'a':2})!=canonical_hash({'a':3})


def test_outcome_is_blind_to_poisoned_holdout_labels():
    r=audit_table(cohort(),config())
    assert r['schema']==REPORT_SCHEMA
    assert r['identity_and_splits']['development_rows']==60
    assert r['identity_and_splits']['holdout_rows_unscored']==22
    assert r['no_holdout_target_analysis'] is True
    assert r['endpoint_contract']['development_event_n']==12
    assert r['n_model_fits']==0 and r['n_model_scores']==0
    assert 'UNOBSERVED_SECRET' not in repr(r)
    assert validate_report(config(),r)['holdout_scored'] is False


def test_unverified_not_inferred_from_missingness():
    r=audit_table(cohort(),config())
    walking=next(x for x in r['missingness'] if x['feature']=='walking')
    assert walking['missing_percent']==25
    assert walking['documentation_status']=='unverified'
    assert walking['requires_codebook_review'] is True
    assert r['route']['generic_tabular_training_permitted'] is True
    assert r['route']['status']=='EXPLORATORY_REVIEW_REQUIRED'
    assert not r['route']['clinical_deployment_permitted']


def test_documentary_evidence_is_mandatory_for_reviewed_status():
    c=config();c['missingness_semantics']['walking']['status']='reviewed_structural'
    with pytest.raises(ValueError,match='documentary evidence'):validate_contract(c)
    c['missingness_semantics']['walking']['evidence_reference']='Dataset instrument, item 7'
    r=audit_table(cohort(),c)
    assert next(z for z in r['missingness'] if z['feature']=='walking')['requires_codebook_review'] is False


@pytest.mark.parametrize('change',[
    lambda c:c.update(schema='wrong'),
    lambda c:c.update(case_id='../secret'),
    lambda c:c['source'].update(expected_sha256='garbage'),
    lambda c:c['source'].update(provenance={'column':'origin'}),
    lambda c:c['features']['numeric'].append('age'),
    lambda c:c.update(target='walking'),
    lambda c:c['split'].update(column='age'),
    lambda c:c['split'].update(holdout='early'),
    lambda c:c['split'].update(holdout_status='external'),
    lambda c:c['outcome'].update(type='unknown'),
    lambda c:c['records'].update(grain='unknown'),
    lambda c:c.update(post_index_columns=['age']),
    lambda c:c.update(post_hoc_development_exploration='yes'),
    lambda c:c.update(min_reporting_n=5),
    lambda c:c.update(numeric_bounds={'sex':[0,1]}),
    lambda c:c.update(numeric_bounds={'age':[90,65]}),
    lambda c:c.update(missingness_semantics={'wrong':{'status':'unverified'}}),
    lambda c:c['missingness_semantics']['walking'].update(status='MNAR'),
    lambda c:c['outcome'].update(type='time_to_event'),
    lambda c:c['outcome'].pop('label_followup_status'),
    lambda c:c['records'].update(grain='repeated_visits'),
    lambda c:c['split'].update(design='grouped'),
    lambda c:c['split'].update(design='time'),
])
def test_bad_protocol_fails_closed(change):
    c=config();change(c)
    with pytest.raises(ValueError):validate_contract(c)


def test_censored_binary_endpoint_routes_away_from_classifier():
    c=config();c['outcome']['label_followup_status']='censoring_present'
    r=audit_table(cohort(),c)
    assert r['route']['status']=='BLOCKED_FOR_CURRENT_ENGINE'
    assert not r['route']['generic_tabular_training_permitted']


def test_complete_followup_claim_requires_reference():
    c=config();c['outcome']['label_followup_status']='complete_horizon_verified'
    with pytest.raises(ValueError,match='evidence'):
        validate_contract(c)
    c['outcome']['followup_evidence_reference']='Published endpoint method appendix'
    assert validate_contract(c) is c


def test_duplicate_person_identifiers_block_current_engine():
    d=cohort();d.loc[9,'person']=d.loc[8,'person']
    r=audit_table(d,config())
    assert r['identity_and_splits']['duplicate_person_rows_in_development']==1
    assert r['route']['status']=='BLOCKED_FOR_CURRENT_ENGINE'


def test_cohort_id_overlap_blocks_current_engine():
    d=cohort();d.loc[60,'person']=d.loc[1,'person']
    r=audit_table(d,config())
    assert r['identity_and_splits']['person_overlap_between_cohorts']==1
    assert r['route']['generic_tabular_training_permitted'] is False


def test_missing_dev_target_blocks_but_holdout_target_ignored():
    d=cohort();d.loc[1,'five_year_label']=None
    r=audit_table(d,config())
    assert not r['endpoint_contract']['development_binary_labels_valid']
    assert r['route']['status']=='BLOCKED_FOR_CURRENT_ENGINE'


def test_bad_numeric_bound_blocks():
    d=cohort();d.loc[2,'walking']=99
    r=audit_table(d,config())
    assert r['route']['status']=='BLOCKED_FOR_CURRENT_ENGINE'
    assert r['numeric_quality'][1]['outside_declared_bounds']==1


def test_bad_numeric_encoding_blocks():
    d=cohort();d['age']=d['age'].astype(object);d.loc[2,'age']='not_age'
    r=audit_table(d,config())
    assert r['route']['status']=='BLOCKED_FOR_CURRENT_ENGINE'
    assert r['numeric_quality'][0]['non_numeric_nonmissing']==1


def test_survival_routes_to_specialized_engine():
    c=config();c['outcome']={'type':'time_to_event','index_time':'baseline',
        'prediction_horizon':'5y','duration_column':'followup','event_column':'died'}
    d=cohort();d['followup']=[2.5]*(len(d));d['died']=[i%2 for i in range(len(d))]
    r=audit_table(d,c)
    assert r['route']['suggested_engine']=='SPECIALIZED_SURVIVAL_REQUIRED'
    assert r['route']['generic_tabular_training_permitted'] is False
    assert r['endpoint_contract']['development_duration_valid'] is True


def test_repeated_visits_route_to_specialized_engine():
    c=config();c['records']={'grain':'repeated_visits','time_column':'visit','group_column':None}
    d=cohort();d['visit']=['0']*len(d)
    r=audit_table(d,c)
    assert r['route']['suggested_engine']=='SPECIALIZED_LONGITUDINAL_REQUIRED'


def test_grouped_route_to_specialized_splitter():
    c=config();c['split']['design']='grouped';c['records']['group_column']='site'
    d=cohort();d['site']=['A']*len(d)
    r=audit_table(d,c)
    assert r['route']['suggested_engine']=='SPECIALIZED_SPLITTER_REQUIRED'


def test_missing_patterns_suppress_sparse_groups():
    d=cohort();c=config()
    _,patterns,suppressed,pairs=_missingness_profile(d.iloc[:60],c)
    assert all(r['n']>=20 for r in patterns)
    assert all(r['both_missing_n']>=20 for r in pairs)
    assert suppressed>=0


def test_mismatched_report_rejected():
    c=config();r=audit_table(cohort(),c)
    r['public_export']=True
    with pytest.raises(ValueError):validate_report(c,r)
    r['public_export']=False;r['config_sha256']='not-same'
    with pytest.raises(ValueError):validate_report(c,r)


def test_never_performs_model_training_at_import():
    import ml.case_readiness_v19 as mod
    assert hasattr(mod,'audit_table') and hasattr(mod,'main')
    assert not hasattr(mod,'trained_model')
