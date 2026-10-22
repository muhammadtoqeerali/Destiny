"""FrailtyScope v0.28 tests. Invented fixtures only; never real datasets."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from ml.case_reliability_v28 import (
    SCHEMA, REPORT_SCHEMA, EXEC_SCHEMA, assess_synthetic_oof, validate_design,
    make_plan, digest, _calibration, _scores,
)


def fixture(task='classification'):
    root=Path(__file__).resolve().parents[1]
    config=json.loads((root/'research/cases/nhanes_reliability_v28.json').read_text())
    v27={'case_id':config['case_id'],'holdout_history':config['holdout_history'],
         'prior_exploration':config['prior_exploration'],
         'prediction_index_status':config['prediction_index_status'],
         'source_task':task}
    v26={'case_id':config['case_id'],'holdout_history':config['holdout_history'],
         'prior_exploration':config['prior_exploration'],
         'prediction_index_status':config['prediction_index_status'],
         'split_policy':config['split_policy'],'n_splits':config['n_splits'],
         'task':task,'candidates':[{'name':n} for n in (
            ['dummy_prior','logistic'] if task=='classification' else ['dummy_mean','ridge'])],
         'primary_metric':'brier' if task=='classification' else 'mae'}
    recipe={'case_id':config['case_id'],'holdout_history':config['holdout_history'],
         'prior_exploration':config['prior_exploration'],
         'prediction_index_status':config['prediction_index_status'],
         'split_review':config['split_policy']}
    if task=='regression':
        config.update(task='regression',candidate_names=['dummy_mean','ridge'],
                      reference_candidate='dummy_mean',primary_metric='mae')
    return config,v27,v26,recipe


def rows(cfg, *, repeated_people=True):
    """3 folds, 18 rows each, 9 people per fold, two consecutive observations."""
    result=[]; n=cfg['n_splits']; assert n==3
    for fold in range(n):
        valid=list(range(18*fold,18*(fold+1)))
        train=[j for j in range(18*n) if j not in valid]
        gp=lambda j: 'synthetic_person_'+str(j//2)
        if cfg['task']=='classification':
            y=[int(j%2) for j in valid]
            estimates={'dummy_prior':[0.5]*18,
                       'logistic':[0.2+0.6*int(j%2) for j in valid]}
        else:
            y=[float(j%7+j%2*0.1) for j in valid]
            estimates={'dummy_mean':[3.]*18,
                       'ridge':[float(j%7+j%2*0.1+0.25) for j in valid]}
        result.append({'train_ids':['row_'+str(j) for j in train],
                       'valid_ids':['row_'+str(j) for j in valid],
                       'train_people':[gp(j) for j in train],
                       'valid_people':[gp(j) for j in valid],
                       'truth':y,'predictions':estimates})
    return result


def test_protocol_and_plan():
    cfg,v27,v26,recipe=fixture()
    assert validate_design(cfg,v27,v26,recipe) is cfg
    plan=make_plan(cfg)
    assert plan['schema']==REPORT_SCHEMA
    assert plan['route']=='BLOCKED_FOR_NEW_ANALYSIS'
    assert plan['no_models_fitted'] is True and plan['public_export'] is False
    assert plan['holdout_history']=='previously_inspected'
    assert len(digest(cfg))==64


def test_classification_results_and_conditional_intervals():
    cfg,*_=fixture()
    r=assess_synthetic_oof(cfg,rows(cfg),synthetic_fixture=True)
    assert r['schema']==EXEC_SCHEMA
    assert r['task']=='classification'
    assert r['n_independent_people']==27 and r['n_synthetic_validation_rows']==54
    assert r['metrics_oof_pooled']['logistic']['brier']<r['metrics_oof_pooled']['dummy_prior']['brier']
    assert r['metrics_oof_pooled']['logistic']['roc_auc']==1
    assert r['calibration_or_residual_diagnostics']['logistic']['slope_status'] in (
        'descriptive_in_sample_on_oof','not_estimable')
    assert r['paired_fixed_prediction_group_bootstrap']['logistic']['negative_favors_candidate']
    assert r['development_predictions_only'] and not r['independent_validation']
    assert not r['predictive_models_fitted'] and not r['participant_predictions_exported']
    assert r['selection_adjusted_intervals'] is False
    assert r==assess_synthetic_oof(cfg,rows(cfg),synthetic_fixture=True)


def test_regression_result():
    cfg,v27,v26,recipe=fixture('regression')
    assert validate_design(cfg,v27,v26,recipe) is cfg
    r=assess_synthetic_oof(cfg,rows(cfg),synthetic_fixture=True)
    assert r['task']=='regression'
    assert r['metrics_oof_pooled']['ridge']['mae'] <r['metrics_oof_pooled']['dummy_mean']['mae']
    assert r['calibration_or_residual_diagnostics']['ridge']['n_synthetic_residuals']==54
    assert 'ridge' in r['paired_fixed_prediction_group_bootstrap']


def test_support_and_suppression_of_small_bins():
    y=np.array([0,1]*16,dtype=float)
    p=np.array([0.1,0.1]*16)
    r=_calibration(y,p,5,5)
    assert r['bins_suppressed']==4
    assert r['slope'] is None  # no logit variability
    assert r['slope_status']=='not_estimable'
    assert r['bins'][0]['n']==32


@pytest.mark.parametrize('mutation',[
    lambda c,v26,r:c.update(holdout_history='locked_new'),
    lambda c,v26,r:c.update(prior_exploration=False),
    lambda c,v26,r:c.update(prediction_index_status='operationally_verified'),
    lambda c,v26,r:c.update(real_data_execution_permitted=True),
    lambda c,v26,r:c.update(model_fitting_permitted=True),
    lambda c,v26,r:c.update(holdout_scoring_permitted=True),
    lambda c,v26,r:c.update(clinical_use_permitted=True),
    lambda c,v26,r:c.update(public_export_permitted=True),
    lambda c,v26,r:c.update(scope='approved'),
    lambda c,v26,r:c.update(independent_evaluation=True),
    lambda c,v26,r:c.update(selection_context='independent_test'),
    lambda c,v26,r:c.update(source_predictions='holdout_scores'),
    lambda c,v26,r:c.update(recalibration_policy='fit_on_validation'),
    lambda c,v26,r:c.update(threshold_policy='maximize_f1'),
    lambda c,v26,r:c.update(uncertainty_unit='row'),
    lambda c,v26,r:c.update(bootstrap_type='ordinary_iid_bootstrap'),
    lambda c,v26,r:c.update(bootstrap_replicates=5),
    lambda c,v26,r:c.update(bootstrap_replicates=501),
    lambda c,v26,r:c.update(bootstrap_replicates=True),
    lambda c,v26,r:c.update(seed=-1),
    lambda c,v26,r:c.update(calibration_bins=1),
    lambda c,v26,r:c.update(minimum_bin_count=1),
    lambda c,v26,r:c.update(minimum_unique_people=1),
    lambda c,v26,r:c.update(n_splits=4),
    lambda c,v26,r:c.update(candidate_names=['dummy_prior','dummy_prior']),
    lambda c,v26,r:c.update(candidate_names=['dummy_prior','catboost']),
    lambda c,v26,r:c.update(reference_candidate='logistic'),
    lambda c,v26,r:c.update(primary_metric='roc_auc'),
    lambda c,v26,r:c.update(task='survival'),
    lambda c,v26,r:c.update(split_policy='forward_time'),
])
def test_unsafe_protocols_rejected(mutation):
    cfg,v27,v26,recipe=fixture()
    mutation(cfg,v26,recipe)
    with pytest.raises(ValueError):validate_design(cfg,v27,v26,recipe)


@pytest.mark.parametrize('mutation',[
    lambda rec:rec[0]['predictions'].pop('logistic'),
    lambda rec:rec[0]['predictions']['logistic'].__setitem__(0,1.3),
    lambda rec:rec[0]['predictions']['logistic'].__setitem__(0,float('nan')),
    lambda rec:rec[0]['truth'].__setitem__(0,2),
    lambda rec:rec[0]['truth'].__setitem__(0,float('nan')),
    lambda rec:rec[0]['truth'].__setitem__(slice(None),[1]*18),
    lambda rec:rec[0]['predictions']['logistic'].pop(),
    lambda rec:rec[0]['valid_ids'].__setitem__(1,rec[0]['valid_ids'][0]),
    lambda rec:rec[0]['train_ids'].__setitem__(0,rec[0]['valid_ids'][0]),
    lambda rec:rec[0]['valid_people'].__setitem__(0,rec[0]['train_people'][0]),
    lambda rec:rec[1]['valid_ids'].__setitem__(0,rec[0]['valid_ids'][0]),
    lambda rec:rec[1]['valid_people'].__setitem__(0,rec[0]['valid_people'][0]),
    lambda rec:rec[2]['valid_people'].__setitem__(0,None),
])
def test_bad_fold_predictions_blocked(mutation):
    cfg,*_=fixture()
    folds=rows(cfg)
    mutation(folds)
    with pytest.raises((ValueError,TypeError)):
        assess_synthetic_oof(cfg,folds,synthetic_fixture=True)


def test_not_enough_participants_or_outcomes():
    cfg,*_=fixture()
    cfg['minimum_unique_people']=40
    with pytest.raises(ValueError,match='few|enough'):
        assess_synthetic_oof(cfg,rows(cfg),synthetic_fixture=True)
    cfg['minimum_unique_people']=12
    folds=rows(cfg)
    for f in folds:
        f['truth']=[0]*16+[1,1]
    with pytest.raises(ValueError,match='Too few positive'):
        assess_synthetic_oof(cfg,folds,synthetic_fixture=True)


def test_forward_time_requires_chronology_and_no_person_overlap():
    cfg,*_=fixture()
    cfg['split_policy']='person_and_forward_time'
    folds=rows(cfg)
    for i,f in enumerate(folds):
        f['train_time']=['2024-01-01']*len(f['train_ids'])
        f['valid_time']=['2025-01-01']*len(f['valid_ids'])
    assert assess_synthetic_oof(cfg,folds,synthetic_fixture=True)['n_folds']==3
    folds[0]['valid_time'][0]='2023-01-01'
    with pytest.raises(ValueError):assess_synthetic_oof(cfg,folds,synthetic_fixture=True)


def test_no_real_data_api_and_cannot_change_safety():
    cfg,*_=fixture()
    with pytest.raises(ValueError,match='Real research'):
        assess_synthetic_oof(cfg,rows(cfg))
    cfg['model_fitting_permitted']=True
    with pytest.raises(ValueError):assess_synthetic_oof(cfg,rows(cfg),synthetic_fixture=True)


def test_metric_equivalence_and_invalid_probability():
    assert abs(_scores('classification',np.array([0,1]),np.array([.1,.9]))['brier']-.01)<1e-10
    assert _scores('regression',np.array([1.,2.]),np.array([1.,3.]))['mae']==.5


def test_regression_bad_folds():
    cfg,*_=fixture('regression')
    folds=rows(cfg)
    folds[0]['truth']=[1.]*18
    with pytest.raises(ValueError):assess_synthetic_oof(cfg,folds,synthetic_fixture=True)


def test_import_does_not_fit_or_load_research_models():
    import ml.case_reliability_v28 as m
    assert callable(m.main)
    assert not hasattr(m,'participant_data')
    assert not hasattr(m,'fitted_model')
