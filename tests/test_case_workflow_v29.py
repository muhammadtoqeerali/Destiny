"""v0.29 -- exclusively invented in-memory fixtures; no NHANES/HUNT data."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.case_workflow_v29 import (SCHEMA, EXEC_SCHEMA, REPORT_SCHEMA, digest,
    make_plan, validate_workflow, run_synthetic_workflow, _read_sources)
from ml.case_harmonization_v24 import harmonize_fixture

ROOT=Path(__file__).resolve().parents[1]


def source_contracts():
    names=['nhanes_workflow_v29','nhanes_reliability_v28','nhanes_temporal_v27',
           'nhanes_task_models_v26','nhanes_foldsafe_v25','nhanes_harmonization_v24']
    return [json.loads((ROOT/'research/cases'/(name+'.json')).read_text()) for name in names]


def invented(n=72):
    assert n%2==0
    raw=[]
    for i in range(n):
        routed=(i%11)==0
        raw.append({'PFQ054':1 if routed else 2,
                    'PFQ061B':None if routed else (5 if i%13==0 else i%4+1),
                    'PFQ061C':None if routed else (5 if i%17==0 else (i+1)%4+1),
                    'PFQ061D':5 if i%19==0 else (i+2)%4+1})
    return pd.DataFrame(raw), np.array([i%2 for i in range(n)]), [f'row_{i}' for i in range(n)], [f'person_{i//2}' for i in range(n)]


def execution(source=True, **kwargs):
    cfg,v28,v27,v26,v25,v24=source_contracts()
    raw,y,ids,people=invented()
    if not source:
        raw,_=harmonize_fixture(raw,v24['waves']['2011-2012'],synthetic_fixture=True)
    return run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,raw,y,
        row_ids=ids,groups=people,source_fixture=source,synthetic_fixture=True,**kwargs)


def test_source_protocol_and_plan():
    cfg,v28,v27,v26,v25,v24=source_contracts()
    assert validate_workflow(cfg,v28,v27,v26,v25,v24) is cfg
    plan=make_plan(cfg,v24)
    assert plan['schema']==REPORT_SCHEMA
    assert plan['route']=='BLOCKED_FOR_NEW_ANALYSIS'
    assert plan['unmapped_predictors'] and len(plan['unmapped_predictors'])==11
    assert len(plan['mapped_features'])==3
    assert plan['no_models_fitted'] and not plan['public_export']
    assert len(digest(cfg))==64


def test_integrated_raw_to_fold_models_to_reliability():
    a=execution()
    assert a['schema']==EXEC_SCHEMA and a['task']=='classification'
    assert a['n_synthetic_rows']==72 and a['n_folds']==3
    assert a['synthetic_model_fits']==6
    assert a['source_mapping_applied'] is True
    assert a['source_status_counts']['walking_difficulty']['structural_skip']>0
    d=a['aggregate_reliability']
    assert d['n_synthetic_validation_rows']==72
    assert d['n_independent_people']==36
    assert set(d['metrics_oof_pooled'])=={'dummy_prior','logistic'}
    assert np.isfinite(d['metrics_oof_pooled']['logistic']['brier'])
    assert set(d['paired_fixed_prediction_group_bootstrap'])=={'logistic'}
    assert not d['independent_validation'] and not d['participant_predictions_exported']
    assert a['selected_model'] is None and not a['models_saved']
    assert a==execution()  # deterministic entire pipeline including bootstrap


def test_canonical_and_raw_equivalent_metrics():
    raw=execution(True)
    canon=execution(False)
    assert raw['aggregate_reliability']==canon['aggregate_reliability']
    assert canon['source_mapping_applied'] is False and canon['source_status_counts'] is None


def test_obvious_fraud_and_leakage_inputs_fail_before_fitting():
    cfg,v28,v27,v26,v25,v24=source_contracts()
    raw,y,ids,people=invented()
    cases=[(raw.assign(outcome_5yr=y),y,ids,people),
           (raw.drop(columns='PFQ061B'),y,ids,people),
           (raw.assign(PFQ061D=[99]*len(raw)),y,ids,people),
           (raw,y,ids[:],['one_person']*len(raw)),
           (raw,y,ids[:],people[:])]
    cases[-1][2][1]=cases[-1][2][0]
    for frame,yy,rid,group in cases:
        with pytest.raises((ValueError,TypeError,KeyError)):
            run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,frame,yy,
                row_ids=rid,groups=group,source_fixture=True,synthetic_fixture=True)


def test_input_cannot_include_targets_after_harmonization():
    cfg,v28,v27,v26,v25,v24=source_contracts()
    raw,y,ids,people=invented()
    canonical,_=harmonize_fixture(raw,v24['waves']['2011-2012'],synthetic_fixture=True)
    canonical['outcome_5yr']=y
    with pytest.raises(ValueError,match='approved canonical'):
        run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,canonical,y,
            row_ids=ids,groups=people,synthetic_fixture=True)


def test_no_real_execution_without_explicit_fixture_contract():
    cfg,v28,v27,v26,v25,v24=source_contracts()
    raw,y,ids,people=invented()
    with pytest.raises(ValueError,match='Real research'):
        run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,raw,y,
            row_ids=ids,groups=people,source_fixture=True)


@pytest.mark.parametrize('mutate',[
    lambda c,p:c.update(holdout_history='locked_new'),
    lambda c,p:c.update(prior_exploration=False),
    lambda c,p:c.update(prediction_index_status='operationally_verified'),
    lambda c,p:c.update(task='survival'),
    lambda c,p:c.update(split_policy='forward_time'),
    lambda c,p:c.update(n_splits=2),
    lambda c,p:c.update(random_seed=42),
    lambda c,p:c.update(candidate_names=['logistic']),
    lambda c,p:c.update(candidate_names=['dummy_prior','catboost']),
    lambda c,p:c.update(reference_candidate='logistic'),
    lambda c,p:c.update(primary_metric='roc_auc'),
    lambda c,p:c.update(harmonization_wave='2013-2014'),
    lambda c,p:c.update(independent_validation=True),
    lambda c,p:c.update(candidate_selection='pick_winner'),
    lambda c,p:c.update(predictions_exported=True),
    lambda c,p:c.update(models_saved=True),
    lambda c,p:c.update(validation_role='untouched_holdout'),
    lambda c,p:c.update(input_contract='real_data'),
    lambda c,p:c.update(scope='clinically_validated'),
    lambda c,p:c.update(model_fitting_permitted=True),
    lambda c,p:c.update(holdout_scoring_permitted=True),
    lambda c,p:c.update(real_data_execution_permitted=True),
    lambda c,p:c.update(clinical_use_permitted=True),
    lambda c,p:c.update(public_export_permitted=True),
    lambda c,p:p[0].update(independent_evaluation=True),
    lambda c,p:p[1].update(independent_holdout='new_test'),
    lambda c,p:p[2].update(test_set_role='inspected'),
    lambda c,p:p[3].update(model_fitting_permitted=True),
    lambda c,p:p[4]['waves']['2011-2012'].update(source_verified=False),
])
def test_protocol_tampering_rejected(mutate):
    configs=source_contracts()
    cfg=configs[0]; others=configs[1:]
    mutate(cfg,others)
    with pytest.raises((ValueError,TypeError,KeyError)):
        validate_workflow(*configs)


def test_bad_canonical_status_or_feature_rejected():
    cfg,v28,v27,v26,v25,v24=source_contracts()
    raw,y,ids,people=invented()
    canonical,_=harmonize_fixture(raw,v24['waves']['2011-2012'],synthetic_fixture=True)
    canonical.loc[1,'walking_difficulty__status']='unknown'
    with pytest.raises(ValueError):
        run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,canonical,y,
            row_ids=ids,groups=people,synthetic_fixture=True)


def test_source_only_contract_chain(tmp_path):
    cfg,*_=source_contracts()
    # Source path was configured in the shipped source-only package.
    assert cfg['related_v28_protocol'].startswith('research/')
    assert cfg['related_private_v28_review'].startswith('artifacts/')
    assert SCHEMA==cfg['schema']


def test_regression_workflow_reuses_v25_and_v28_without_binary_metrics():
    cfg,v28,v27,v26,v25,v24=source_contracts()
    cfg.update(task='regression',candidate_names=['dummy_mean','ridge'],
               reference_candidate='dummy_mean',primary_metric='mae')
    v26.update(task='regression',primary_metric='mae',candidates=[
        {'name':'dummy_mean','params':{}}, {'name':'ridge','params':{'alpha':1.0}}])
    v27['source_task']='regression'
    v28.update(task='regression',candidate_names=['dummy_mean','ridge'],
               reference_candidate='dummy_mean',primary_metric='mae')
    raw,_,ids,people=invented()
    outcome=np.array([float(i%9)+(i%2)*0.25 for i in range(len(raw))])
    result=run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,raw,outcome,
        row_ids=ids,groups=people,source_fixture=True,synthetic_fixture=True)
    assert result['task']=='regression' and result['synthetic_model_fits']==6
    diagnostic=result['aggregate_reliability']
    assert diagnostic['task']=='regression'
    assert set(diagnostic['metrics_oof_pooled']['ridge'])=={'mae','rmse','r2'}
    assert diagnostic['calibration_or_residual_diagnostics']['ridge']['n_synthetic_residuals']==72
    assert not result['independent_validation']


def test_participant_group_overlap_through_repeated_visits_is_guarded():
    cfg,v28,v27,v26,v25,v24=source_contracts()
    raw,y,ids,_=invented()
    people=['same_person']*len(raw)
    with pytest.raises(ValueError,match='groups|Group|distinct'):
        run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,raw,y,
            row_ids=ids,groups=people,source_fixture=True,synthetic_fixture=True)


def test_forward_time_not_silently_claimed_by_person_only_protocol():
    cfg,v28,v27,v26,v25,v24=source_contracts()
    cfg['split_policy']=v28['split_policy']=v26['split_policy']='person_and_forward_time'
    v25['split_review']='person_and_forward_time'
    with pytest.raises(ValueError,match='specialist|participant-disjoint'):
        validate_workflow(cfg,v28,v27,v26,v25,v24)
