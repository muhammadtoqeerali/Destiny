"""Structural and arithmetic-only tests. NEVER train any models here."""
import copy
import pytest
from ml.case_ablation_v14 import (SCHEMA,sha_json,validate_config,columns_for,
                                   summarize)


def contracts():
    m={'case_id':'research_case','task':'classification','features':{
        'numeric':['age','bmi','walking'],'categorical':['sex']}}
    p={'case_id':'research_case','primary_metric':'brier',
       'candidates':['logistic','catboost']}
    s={'schema':'FRAILTYSCOPE_CASE_STRATEGY_V13',
       'holdout_used_in_selection':False,
       'manifest_sha256':sha_json(m),'protocol_sha256':sha_json(p),
       'primary_metric':'brier','selected_model':'logistic','selected_params':{'C':0.08}}
    a={'schema':SCHEMA,'case_id':'research_case','folds':3,
       'seeds':[1,2,3], 'variants':[
           {'name':'reference','drop_features':[],'numeric_missing_indicators':False},
           {'name':'indicators','drop_features':[],'numeric_missing_indicators':True},
           {'name':'omit_walking','drop_features':['walking'],'numeric_missing_indicators':False}]}
    return a,m,p,s


def test_valid_contract_and_changed_columns():
    a,m,p,s=contracts()
    assert validate_config(a,m,p,s) is a
    assert columns_for(m,a['variants'][2])==(['age','bmi'],['sex'])

@pytest.mark.parametrize('change',[
    lambda a,m,p,s:a.update(case_id='wrong'),
    lambda a,m,p,s:s.update(holdout_used_in_selection=True),
    lambda a,m,p,s:s.update(manifest_sha256='stale'),
    lambda a,m,p,s:s.update(protocol_sha256='stale'),
    lambda a,m,p,s:a.update(folds=7),
    lambda a,m,p,s:a.update(seeds=[2,2]),
    lambda a,m,p,s:a['variants'][1].update(drop_features=['nonexistent']),
    lambda a,m,p,s:a['variants'][0].update(numeric_missing_indicators=True),
    lambda a,m,p,s:a['variants'][1].update(numeric_missing_indicators=False),
    lambda a,m,p,s:a['variants'][2].update(drop_features=['age','bmi','walking','sex']),
    lambda a,m,p,s:s.update(selected_model='random_forest'),
    lambda a,m,p,s:a.update(variants=[a['variants'][0]]),
])
def test_contract_fail_closed(change):
    a,m,p,s=contracts();change(a,m,p,s)
    with pytest.raises(ValueError):validate_config(a,m,p,s)


def test_paired_repeat_loss_math():
    x={'reference':[{'seed':1,'n':100,'loss':.13},{'seed':2,'n':100,'loss':.15}],
       'flags':[{'seed':1,'n':100,'loss':.12},{'seed':2,'n':100,'loss':.145}],
       'omit':[{'seed':1,'n':100,'loss':.14},{'seed':2,'n':100,'loss':.16}]}
    r=summarize(x,'brier')
    assert [v['variant'] for v in r]==['reference','flags','omit']
    assert r[1]['loss_gain_vs_reference']==.0075
    assert r[1]['repeats_with_lower_loss']==2
    assert r[2]['loss_gain_vs_reference']==-.01
    assert r[0]['loss_gain_vs_reference']==0


def test_refuses_unpaired_or_nonfinite():
    x={'reference':[{'seed':1,'n':20,'loss':.2},{'seed':2,'n':20,'loss':.3}],
       'other':[{'seed':1,'n':20,'loss':.1},{'seed':3,'n':20,'loss':.1}]}
    with pytest.raises(ValueError,match='Unpaired'):summarize(x,'brier')
    x['other'][1]['seed']=2;x['other'][0]['loss']=float('nan')
    with pytest.raises(ValueError,match='Nonfinite'):summarize(x,'brier')


def test_module_import_never_evaluates():
    import ml.case_ablation_v14 as mod
    assert hasattr(mod,'main') and hasattr(mod,'run')
    assert not hasattr(mod,'trained_model')
