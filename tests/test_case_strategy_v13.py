"""Source-only/unit tests. NONE of these tests fit a machine-learning model."""
import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from ml.case_strategy_v13 import (SCHEMA, validate_protocol, select_from_scores,
    partition_contract, fold_indices, manifest_hash, within_project)

ROOT = Path(__file__).resolve().parents[1]
BASE = {
    'case_id': 'test_case', 'task': 'classification',
    'source': {'path': 'data/foo.csv'}, 'id_column': 'person', 'target': 'target',
    'features': {'numeric': ['age'], 'categorical': ['sex']},
    'split': {'strategy': 'cohort', 'column': 'wave',
              'development': 'A', 'evaluation': 'B', 'validation_fraction': .25},
    'models': ['dummy','logistic','random_forest','hist_boost','catboost','xgboost'],
    'selection_metric': 'brier', 'cv_folds': 3, 'trials_per_model': 4
}
PROTOCOL = {
    'schema': SCHEMA, 'case_id': 'test_case', 'primary_metric': 'brier',
    'candidates': ['logistic','random_forest','catboost'],
    'outer_folds':3, 'inner_folds':3, 'screen_trials':2,
    'refine_trials':4, 'top_k':2, 'practical_tie_margin': .001,
    'group_column':None, 'time_column':None, 'holdout_status':'locked_new'
}


def fresh():return copy.deepcopy(BASE), copy.deepcopy(PROTOCOL)


def test_nominal_manifest_and_protocol():
    a,b=fresh();assert validate_protocol(b,a)['case_id']=='test_case'


def test_unknown_model_fails_closed():
    a,b=fresh();b['candidates']=['logistic','lightgbm'];
    with pytest.raises(ValueError,match='Candidate'):validate_protocol(b,a)


def test_duplicate_candidate_rejected():
    a,b=fresh();b['candidates']=['logistic','logistic']
    with pytest.raises(ValueError,match='Duplicate'):validate_protocol(b,a)


def test_temporal_inputs_cannot_use_shuffled_cv():
    a,b=fresh();b['time_column']='visit_date'
    with pytest.raises(ValueError,match='Longitudinal'):validate_protocol(b,a)


def test_outcome_or_feature_cannot_be_group_key():
    a,b=fresh();b['group_column']='age'
    with pytest.raises(ValueError,match='predictor'):validate_protocol(b,a)


def test_holdout_status_explicit():
    a,b=fresh();b['holdout_status']='unknown'
    with pytest.raises(ValueError,match='status'):validate_protocol(b,a)


def test_model_loss_selection_is_predeclared():
    c=[{'family':'catboost','loss':.1280}, {'family':'logistic','loss':.1288},
       {'family':'random_forest','loss':.1300}]
    result=select_from_scores(c,'brier',.001)
    assert result['family']=='logistic'
    assert result['best_loss']==.128
    assert result['considered_equivalent']==['catboost','logistic']


def test_no_equivalence_margin_winner_is_best():
    r=select_from_scores([{'family':'catboost','loss':.122},
                          {'family':'logistic','loss':.123}],'brier',0)
    assert r['family']=='catboost'


def test_invalid_score_rejected():
    with pytest.raises(ValueError,match='Nonfinite'):
        select_from_scores([{'family':'logistic','loss':float('nan')}],'brier',.001)


def test_group_cv_never_crosses_groups():
    y=pd.Series(([0,1,0,1]*12))
    g=np.repeat(np.arange(12),4)
    splits=list(fold_indices(y,3,2026,'classification',g))
    assert len(splits)==3
    for tr,va in splits:assert not set(g[tr])&set(g[va])


def test_individual_cv_is_deterministic():
    y=pd.Series([0,1]*30)
    a=list(fold_indices(y,3,2026,'classification'))
    b=list(fold_indices(y,3,2026,'classification'))
    for (at,av),(bt,bv) in zip(a,b):
        assert np.array_equal(at,bt) and np.array_equal(av,bv)


def test_repeated_person_rows_fails_closed():
    a,b=fresh();frame=pd.DataFrame({'person': list(range(69))+[0], 'wave':['A']*55+['B']*15})
    y=pd.Series([0,1]*35)
    with pytest.raises(ValueError,match='landmark'):
        partition_contract(frame,y,np.arange(55),np.arange(55,70),b,a)


def test_group_overlap_across_holdout_rejected():
    a,b=fresh();b['group_column']='hospital'
    frame=pd.DataFrame({'person':range(70), 'hospital':['site1']*70})
    y=pd.Series([0,1]*35)
    with pytest.raises(ValueError,match='Group/site leakage'):
        partition_contract(frame,y,np.arange(55),np.arange(55,70),b,a)


def test_group_contract_valid():
    a,b=fresh();b['group_column']='hospital'
    frame=pd.DataFrame({'person':range(90),'hospital':np.repeat(np.arange(18),5)})
    y=pd.Series([0,1]*45)
    z=partition_contract(frame,y,np.arange(60),np.arange(60,90),b,a)
    assert z['groups_in_development']==12 and z['evaluation_n']==30


def test_plan_paths_block_traversal(tmp_path):
    (tmp_path/'research').mkdir();(tmp_path/'data').mkdir()
    (tmp_path/'research'/'ok.json').write_text('{}')
    assert within_project(tmp_path,'research/ok.json','research').exists()
    with pytest.raises(ValueError,match='inside research'):
        within_project(tmp_path,'research/../data/foo.csv','research')


def test_hash_independent_of_json_key_order():
    assert manifest_hash({'a':1,'b':2})==manifest_hash({'b':2,'a':1})


def test_development_profile_does_not_use_holdout_rows():
    from ml.case_strategy_v13 import development_profile
    a,b=fresh()
    frame=pd.DataFrame({'age':[60]*40+[99]*20,'sex':['F']*60,
                        'target':[0]*60})
    y=pd.Series([0,1]*30)
    p=development_profile(frame,y,np.arange(40),a)
    assert p['development_n']==40
    assert p['predictor_count']==2
    assert p['missingness_percent_development'][0]['missing_percent']==0
    assert p['event_prevalence']==.5


def test_staged_search_promotes_only_best_two_without_fitting(monkeypatch):
    from ml import case_strategy_v13 as strategy
    _,proto=fresh()
    calls=[]
    fake={'logistic':.1390,'random_forest':.1500,'catboost':.1320}
    def stub(x,y,numeric,categorical,family,task,metric,group,folds,trials,seed):
        calls.append((family,trials))
        assert metric=='brier' and task=='classification'
        # Distinct fixed losses for refine phase. NO estimator is created.
        loss=fake[family] - (.001 if trials==4 else 0)
        return {'family':family,'params':{},'loss':loss,'fold_losses':[loss]*3,'fold_sd':0,'trials':trials}
    monkeypatch.setattr(strategy,'tune_family',stub)
    x=pd.DataFrame({'age':list(range(30)),'sex':['F']*30})
    y=pd.Series([0,1]*15)
    r=strategy.staged_selection(x,y,['age'],['sex'],proto,'classification')
    assert r['promoted']==['catboost','logistic']
    assert r['winner']['family']=='catboost'
    assert len(calls)==5 and calls.count(('random_forest',4))==0
