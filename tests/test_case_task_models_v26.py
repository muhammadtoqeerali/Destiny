"""Invented data only. No research records, NHANES/HUNT fitting or artifact writes."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.case_task_models_v26 import (SCHEMA, REPORT_SCHEMA, digest, make_plan,
    validate_design, evaluate_synthetic_candidates, _fold_indices)


def fixture():
    base=Path(__file__).resolve().parents[1]
    cfg=json.loads((base/'research/cases/nhanes_task_models_v26.json').read_text())
    recipe=json.loads((base/'research/cases/nhanes_foldsafe_v25.json').read_text())
    return cfg,recipe


def mobility(rows=36):
    assert rows%2==0
    people=np.repeat(np.arange(rows//2), 2)
    x=pd.DataFrame({
        'walking_difficulty':np.where(np.arange(rows)%5==0, np.nan,
            (people%4+1).astype(float)),
        'walking_difficulty__status':['does_not_do_activity' if i%5==0 else 'observed'
                                      for i in range(rows)],
        'stairs_difficulty':np.where(np.arange(rows)%7==0, np.nan,
            ((people+1)%4+1).astype(float)),
        'stairs_difficulty__status':['structural_skip' if i%7==0 else 'observed'
                                     for i in range(rows)],
        'stooping_difficulty':np.where(np.arange(rows)%11==0, np.nan,
            ((people+2)%4+1).astype(float)),
        'stooping_difficulty__status':['does_not_do_activity' if i%11==0 else 'observed'
                                       for i in range(rows)]
    })
    return x, people


def numeric_recipe():
    _,recipe=fixture()
    recipe=copy.deepcopy(recipe)
    recipe['features']={'measure': {'kind':'numeric','representation':'numeric',
        'allowed_values':None,'source_status_required':True,
        'allowed_statuses':['observed','not_recorded']}}
    return recipe


def regression():
    cfg,recipe=fixture()
    cfg=copy.deepcopy(cfg)
    cfg['task']='regression'
    cfg['primary_metric']='mae'
    cfg['candidates']=[{'name':'dummy_mean','params':{}},
                       {'name':'ridge','params':{'alpha':1.0}},
                       {'name':'random_forest','params':{'n_estimators':10,
                                      'max_depth':3,'min_samples_leaf':1}}]
    recipe=numeric_recipe()
    x=pd.DataFrame({'measure':np.arange(36,dtype=float)+1,
                    'measure__status':['observed']*36})
    x.loc[[2,5,21],'measure']=np.nan
    x.loc[[2,5,21],'measure__status']='not_recorded'
    y=np.arange(36,dtype=float)*0.7 + (np.arange(36)%3)*0.5
    return cfg,recipe,x,y,np.repeat(np.arange(18),2)


def test_source_contract_present_and_blocked():
    cfg,recipe=fixture()
    assert validate_design(cfg,recipe) is cfg
    assert cfg['schema']==SCHEMA
    plan=make_plan(cfg)
    assert plan['schema']==REPORT_SCHEMA
    assert plan['route']=='BLOCKED_FOR_NEW_ANALYSIS'
    assert not plan['no_models_fitted'] is False
    assert not plan['public_export']
    assert plan['holdout_history']=='previously_inspected'
    assert len(cfg['candidates'])==4


def test_synthetic_classification_groupcv_deterministic():
    cfg,recipe=fixture()
    x,persons=mobility()
    y=(persons%2).astype(int)
    args=dict(row_ids=[f'row{i}' for i in range(len(x))],groups=persons.tolist(),
              synthetic_fixture=True)
    result=evaluate_synthetic_candidates(cfg,recipe,x,y,**args)
    again=evaluate_synthetic_candidates(cfg,recipe,x,y,**args)
    assert result==again
    assert result['n_fits']==12 and result['n_splits']==3
    assert result['development_only'] and not result['independent_validation']
    assert not result['models_saved'] and not result['participant_predictions_exported']
    assert set(p['name'] for p in result['candidate_rankings']) == {
        'dummy_prior','logistic','random_forest','hist_gradient_boosting'}
    assert result['top_development_candidate']==result['candidate_rankings'][0]['name']
    assert all(0 <= r['mean_metrics']['roc_auc'] <=1 and
               0<=r['mean_metrics']['brier']<=1 and
               0<=r['mean_metrics']['average_precision']<=1 and
               r['mean_metrics']['log_loss']>=0 for r in result['candidate_rankings'])
    assert 'predictions' not in result and 'model' not in result


def test_regression_candidate_comparison():
    cfg,recipe,x,y,people=regression()
    assert validate_design(cfg,recipe) is cfg
    report=evaluate_synthetic_candidates(cfg,recipe,x,y,
           row_ids=list(range(len(x))),groups=list(people),synthetic_fixture=True)
    assert report['task']=='regression' and report['n_fits']==9
    assert set(report['candidate_rankings'][0]['mean_metrics'])=={'mae','rmse','r2'}
    assert all(np.isfinite(list(r['mean_metrics'].values())).all() for r in report['candidate_rankings'])
    assert report['selection_metric']=='mae'


def test_no_fitting_without_fixture_flag():
    cfg,recipe=fixture(); x,g=mobility()
    with pytest.raises(ValueError,match='Real research'):
        evaluate_synthetic_candidates(cfg,recipe,x,(g%2).astype(int),
          row_ids=list(range(len(x))),groups=g)


def test_wrong_task_outcome_data_fails():
    cfg,recipe=fixture();x,g=mobility()
    args=dict(row_ids=list(range(len(x))),groups=g,synthetic_fixture=True)
    for invalid in [np.full(len(x),1), np.array([0,1]*17+[np.nan,1]),
                    ['died' if i%2 else 'alive' for i in range(len(x))],
                    np.array([0,1]*17+[2,1]), np.array([0,1]*5)]:
        with pytest.raises(ValueError):
            evaluate_synthetic_candidates(cfg,recipe,x,invalid,**args)


def test_rejects_extra_outcome_columns_and_missing_feature():
    cfg,recipe=fixture();x,g=mobility();y=(g%2).astype(int)
    for bad in [x.assign(outcome_5yr=y),x.drop(columns=['walking_difficulty']),
                x.assign(seqn=range(len(x)))]:
        with pytest.raises(ValueError,match='authorized predictors'):
            evaluate_synthetic_candidates(cfg,recipe,bad,y,
                  row_ids=list(range(len(x))),groups=g,synthetic_fixture=True)


def test_no_group_information_rejected():
    cfg,recipe=fixture();x,g=mobility();y=(g%2).astype(int)
    with pytest.raises(ValueError,match='group'):
        evaluate_synthetic_candidates(cfg,recipe,x,y,
          row_ids=list(range(len(x))),synthetic_fixture=True)


def test_duplicate_row_id_rejected():
    cfg,recipe=fixture();x,g=mobility();y=(g%2).astype(int)
    with pytest.raises(ValueError,match='row identifiers'):
        evaluate_synthetic_candidates(cfg,recipe,x,y,
          row_ids=['same']*len(x),groups=g,synthetic_fixture=True)


def test_unbalanced_group_outcomes_fail_before_models_fit():
    cfg,recipe=fixture();x,g=mobility()
    y=np.zeros(len(x),dtype=int);y[g==0]=1
    with pytest.raises(ValueError,match='both outcome classes'):
        evaluate_synthetic_candidates(cfg,recipe,x,y,
           row_ids=list(range(len(x))),groups=g,synthetic_fixture=True)


def test_training_rows_only_reach_preprocessing_fit(monkeypatch):
    import ml.case_foldsafe_v25 as v25
    cfg,recipe=fixture();x,g=mobility();y=(g%2).astype(int)
    seen=[]; original=v25.ContractFrameValidator.fit
    def guarded_fit(self, subset, y=None):
        seen.append(tuple(subset.index))
        assert 0<len(subset)<len(x)
        return original(self,subset,y)
    monkeypatch.setattr(v25.ContractFrameValidator,'fit',guarded_fit)
    result=evaluate_synthetic_candidates(cfg,recipe,x,y,
       row_ids=list(range(len(x))),groups=g,synthetic_fixture=True)
    assert len(seen)==result['n_fits']
    assert len({frozenset(z) for z in seen})==cfg['n_splits']


def test_prevalidate_all_folds_before_any_fit(monkeypatch):
    import ml.case_foldsafe_v25 as v25
    cfg,recipe=fixture();x,g=mobility();y=(g%2).astype(int)
    y=np.array(y);y[g==0]=0;y[g==3]=0;y[g==6]=0
    count=[]
    def should_never_fit(self, x, y=None):
        count.append(True)
        raise AssertionError('should not fit invalid folds')
    monkeypatch.setattr(v25.ContractFrameValidator,'fit',should_never_fit)
    # Force unsafe group fold by making only one positive group.
    y[:]=0;y[g==1]=1
    with pytest.raises(ValueError,match='both outcome classes'):
        evaluate_synthetic_candidates(cfg,recipe,x,y,
           row_ids=list(range(len(x))),groups=g,synthetic_fixture=True)
    assert not count


def test_forward_time_prospective_synthetic():
    cfg,recipe=fixture();x,g=mobility()
    cfg=copy.deepcopy(cfg);cfg['split_policy']='forward_time'
    recipe=copy.deepcopy(recipe);recipe['split_review']='forward_time'
    dates=pd.date_range('2023-01-01',periods=len(x),freq='D').astype(str).tolist()
    y=np.array([i%2 for i in range(len(x))])
    out=evaluate_synthetic_candidates(cfg,recipe,x,y,row_ids=list(range(len(x))),
                timestamps=dates,synthetic_fixture=True)
    assert out['n_fits']==12


def test_forward_time_reject_bad_dates():
    cfg,recipe=fixture();x,g=mobility()
    cfg['split_policy']=recipe['split_review']='forward_time'
    dates=pd.date_range('2023-01-01',periods=len(x),freq='D').astype(str).tolist()
    dates[4]='garbage'
    with pytest.raises(ValueError,match='timestamps'):
        evaluate_synthetic_candidates(cfg,recipe,x,np.array([i%2 for i in range(len(x))]),
          row_ids=list(range(len(x))),timestamps=dates,synthetic_fixture=True)


def test_repeated_timestamps_do_not_get_split_across_fold():
    cfg,recipe=fixture();x,g=mobility()
    cfg['split_policy']=recipe['split_review']='forward_time'
    dates=[f'2023-01-{i//2+1:02}' for i in range(len(x))]
    y=np.array([i%2 for i in range(len(x))])
    folds=_fold_indices(cfg,len(x),y,row_ids=list(range(len(x))),groups=None,
                              timestamps=dates)
    for tr,va in folds:
        assert max(dates[i] for i in tr)<min(dates[i] for i in va)


def test_person_and_time_refuses_same_person_later():
    cfg,recipe=fixture();x,g=mobility()
    cfg['split_policy']=recipe['split_review']='person_and_forward_time'
    dates=pd.date_range('2023-01-01',periods=len(x),freq='D').astype(str).tolist()
    y=np.array([i%2 for i in range(len(x))])
    # Interleave a repeated person across every timestamp window.
    groups=['person1' if i in (0,30) else f'person{i}' for i in range(len(x))]
    with pytest.raises(ValueError,match='group'):
        evaluate_synthetic_candidates(cfg,recipe,x,y,
           row_ids=list(range(len(x))),groups=groups,timestamps=dates,synthetic_fixture=True)


def test_unsupported_specialist_tasks_explicitly_blocked():
    cfg,recipe=fixture()
    for task in ('survival','longitudinal'):
        alt=copy.deepcopy(cfg)
        alt['task']=task;alt['candidates']=[];alt['primary_metric']=None
        assert validate_design(alt,recipe) is alt
        assert make_plan(alt)['route']=='SPECIALIZED_ENGINE_REQUIRED'
        with pytest.raises(ValueError,match='Specialized'):
            evaluate_synthetic_candidates(alt,recipe,None,None,
                row_ids=[],synthetic_fixture=True)


@pytest.mark.parametrize('change',[
    lambda c:c.update(real_data_execution_permitted=True),
    lambda c:c.update(model_fitting_permitted=True),
    lambda c:c.update(holdout_scoring_permitted=True),
    lambda c:c.update(clinical_use_permitted=True),
    lambda c:c.update(public_export_permitted=True),
    lambda c:c.update(holdout_history='locked_new'),
    lambda c:c.update(prior_exploration=False),
    lambda c:c.update(prediction_index_status='operationally_verified'),
    lambda c:c.update(split_policy='forward_time'),
    lambda c:c.update(selection_rule='evaluation_winner'),
    lambda c:c.update(test_set_role='independent'),
    lambda c:c.update(task='regression'),
    lambda c:c.update(n_splits=20),
    lambda c:c.update(random_seed=-5),
    lambda c:c.update(primary_metric='accuracy'),
    lambda c:c.update(primary_metric='mae'),
    lambda c:c.update(candidates=[]),
    lambda c:c.update(candidates=[c['candidates'][1]]),
    lambda c:c['candidates'].append(copy.deepcopy(c['candidates'][1])),
    lambda c:c['candidates'][1]['params'].update(C=-1),
    lambda c:c['candidates'][1]['params'].update(C=10**99),
    lambda c:c['candidates'][2]['params'].update(n_estimators=0),
    lambda c:c['candidates'][2]['params'].update(n_estimators=40.5),
    lambda c:c['candidates'][1].update(name='ridge'),
    lambda c:c['candidates'][1]['params'].update(extra=3),
    lambda c:c.update(scope='validated'),
])
def test_invalid_protocol_blocked(change):
    cfg,recipe=fixture();change(cfg)
    with pytest.raises(ValueError): validate_design(cfg,recipe)


def test_manifest_task_must_agree():
    cfg,recipe=fixture()
    assert validate_design(cfg,recipe,{'case_id':cfg['case_id'],'task':'classification'}) is cfg
    with pytest.raises(ValueError,match='manifest'):
        validate_design(cfg,recipe,{'case_id':cfg['case_id'],'task':'regression'})


def test_regression_target_non_finite_rejected():
    cfg,recipe,x,y,g=regression()
    y[4]=np.inf
    with pytest.raises(ValueError,match='finite'):
        evaluate_synthetic_candidates(cfg,recipe,x,y,row_ids=list(range(len(x))),
                                       groups=g,synthetic_fixture=True)


def test_synthetic_report_fingerprint():
    cfg,recipe=fixture()
    assert len(digest(cfg))==64
    assert make_plan(cfg)['config_sha256']==digest(cfg)
