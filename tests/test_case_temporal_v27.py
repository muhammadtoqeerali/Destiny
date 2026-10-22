"""All fitting in this file is performed ONLY on invented, in-memory synthetic fixtures."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.case_temporal_v27 import (
    SCHEMA, REPORT_SCHEMA, digest, validate_design, make_plan, _km, _km_at,
    _concordance, _ipcw_brier, _visit_chronology, _cox_fit,
    evaluate_synthetic_survival, evaluate_synthetic_longitudinal,
)

ROOT = Path(__file__).resolve().parents[1]


def configurations():
    cfg=json.loads((ROOT/'research/cases/nhanes_temporal_v27.json').read_text())
    v26=json.loads((ROOT/'research/cases/nhanes_task_models_v26.json').read_text())
    v25=json.loads((ROOT/'research/cases/nhanes_foldsafe_v25.json').read_text())
    return cfg,v26,v25


def feature_frame(n, *, seed=7):
    rng=np.random.default_rng(seed)
    out={}
    for name in ('walking_difficulty','stairs_difficulty','stooping_difficulty'):
        val=rng.choice([1.,2.,3.,4.],n)
        out[name]=val
        out[name+'__status']=['observed']*n
    return pd.DataFrame(out)


def survival(n=36):
    rng=np.random.default_rng(222)
    frame=feature_frame(n)
    # time + event are independent synthetic toy records, with both event and censoring
    t=rng.uniform(2,12,n)
    e=(rng.uniform(0,1,n)>.30).astype(int)
    people=[f'P{i:04d}' for i in range(n)]
    return frame,t,e,list(range(n)),people


def transitions(n_people=15,n_visits=3):
    rng=np.random.default_rng(291)
    rows=[];lag=[];target=[];people=[];origin=[];future=[];rid=[]
    for p in range(n_people):
        v=10.0+2*p
        for k in range(n_visits):
            rows.append([float(1+(p+k)%4),float(1+p%4),float(1+k%4)])
            lag.append(v)
            v=v+.8+.1*p+.3*k+rng.normal(0,.05)
            target.append(v)
            people.append('id_'+str(p))
            origin.append(f'{2020+k}-01-01')
            future.append(f'{2021+k}-01-01')
            rid.append(f'{p}_{k}')
    df=pd.DataFrame(rows,columns=['walking_difficulty','stairs_difficulty','stooping_difficulty'])
    for c in ['walking_difficulty','stairs_difficulty','stooping_difficulty']:
        df[c+'__status']='observed'
    return df,lag,target,rid,people,origin,future


def test_protocol_matches_prior_source_contract():
    cfg,v26,recipe=configurations()
    assert validate_design(cfg,v26,recipe) is cfg
    report=make_plan(cfg)
    assert report['schema']==REPORT_SCHEMA
    assert report['route']=='BLOCKED_FOR_NEW_ANALYSIS'
    assert report['original_task']=='classification'
    assert report['holdout_history']=='previously_inspected'
    assert report['no_models_fitted'] and not report['public_export']
    assert len(digest(cfg))==64


@pytest.mark.parametrize('key,value',[
    ('case_id','another_case'),('holdout_history','locked_new'),
    ('prior_exploration',False),('prediction_index_status','operationally_verified'),
    ('scope','approved'),('source_task','survival'),('split_policy','forward_time'),
    ('n_splits',1),('n_splits',6),('random_seed',-1),
    ('selection_rule','validated'),('independent_holdout','pristine'),
    ('specialist_demo_tasks',['right_censored_survival']),
    ('related_v26_protocol',None),('related_private_v26_review',None),
    ('real_data_execution_permitted',True),('model_fitting_permitted',True),
    ('holdout_scoring_permitted',True),('clinical_use_permitted',True),
    ('public_export_permitted',True),
])
def test_invalid_protocol_rejected(key,value):
    cfg,v26,recipe=configurations()
    cfg[key]=value
    with pytest.raises(ValueError):validate_design(cfg,v26,recipe)


def test_survival_rules_cannot_silently_change():
    cfg,v26,recipe=configurations()
    cfg['survival']['competing_events']='ignored'
    with pytest.raises(ValueError,match='Survival'): validate_design(cfg,v26,recipe)


def test_longitudinal_horizon_cannot_be_mislabeled():
    cfg,v26,recipe=configurations()
    cfg['longitudinal']['prediction_horizon']='one_year'
    with pytest.raises(ValueError,match='Variable'):validate_design(cfg,v26,recipe)


def test_km_censoring_and_tie_behavior():
    s=_km([1.,2.,3.,4.],[1,0,1,0])
    assert _km_at(s,1,before=True)==1
    assert _km_at(s,1)==.75
    assert _km_at(s,2)==.75  # Censored follow-up does not change survival
    assert _km_at(s,3)==.375
    assert _km_at(s,100)==.375
    assert _km_at(_km([1,1,2],[1,1,0]),1)==pytest.approx(1-2/3)


def test_concordance_strict_comparability_and_tied_risk():
    t=np.array([1.,3.,5.]); e=np.array([1,0,1])
    assert _concordance(t,e,np.array([.8,.4,.1]))==1
    assert _concordance(t,e,np.array([.1,.4,.8]))==0
    assert _concordance(t,e,np.array([.5,.5,.5]))==.5
    with pytest.raises(ValueError,match='comparable'):
        _concordance(np.array([1.,1.]),np.array([1,1]),np.array([.5,.6]))


def test_ipcw_early_censor_not_event_free():
    # Training has no early censoring; events happen at <= horizon, late subjects are non-events
    tr_t=np.array([2.,3.,6.,7.]);tr_e=np.array([1,0,1,0]);h=4.
    va_t=np.array([2.,3.,8.]); va_e=np.array([1,0,0]); risk=np.array([1.,.0,.0])
    result=_ipcw_brier(tr_t,tr_e,va_t,va_e,risk,h)
    assert result==0  # early-censored validation row ignored
    with pytest.raises(ValueError,match='support'):
        _ipcw_brier(np.array([1.,2.,3.]),np.array([0,0,0]),
                    np.array([2.,5.]),np.array([1,0]),np.array([.1,.2]),3.)


def test_penalized_cox_numeric_contract():
    frame=np.array([[1.,0.],[0.,1.],[1.,1.],[0.,0.],[.3,.6],[.5,.2]])
    t=np.array([2.,3.,3.,4.,5.,6.]);e=np.array([1,1,0,1,0,1])
    beta,baseline=_cox_fit(frame,t,e,alpha=1.0)
    assert len(beta)==2 and np.isfinite(beta).all()
    assert len(baseline)==4 and all(b[1]>0 for b in baseline)


def test_survival_synthetic_cv_and_reproducibility():
    cfg,_,recipe=configurations()
    X,t,e,rid,people=survival()
    first=evaluate_synthetic_survival(cfg,recipe,X,t,e,row_ids=rid,people=people,
                                      horizon=5.,synthetic_fixture=True)
    other=evaluate_synthetic_survival(cfg,recipe,X,t,e,row_ids=rid,people=people,
                                      horizon=5.,synthetic_fixture=True)
    assert first==other
    assert first['folds']==3 and not first['independent_validation']
    assert set(first['results'])=={'kaplan_meier','penalized_cox'}
    for metrics in first['results'].values():
        assert 0<=metrics['harrell_c']<=1
        assert np.isfinite(metrics['ipcw_brier'])


def test_survival_requires_synthetic_switch():
    cfg,_,recipe=configurations();X,t,e,rid,p=survival()
    with pytest.raises(ValueError,match='Real-data'):
        evaluate_synthetic_survival(cfg,recipe,X,t,e,row_ids=rid,people=p,horizon=5.)


@pytest.mark.parametrize('mutation',[lambda X,t,e,ids,p: (t.__setitem__(0,-1)),
     lambda X,t,e,ids,p: (e.__setitem__(0,2)),
     lambda X,t,e,ids,p: (ids.__setitem__(1,ids[0])),
     lambda X,t,e,ids,p: (X.__setitem__('death_date','2024-01-01')),
     lambda X,t,e,ids,p: (X.drop(columns=['walking_difficulty__status'],inplace=True)),
     lambda X,t,e,ids,p: (p.__setitem__(0,None))])
def test_survival_bad_inputs_block(mutation):
    cfg,_,recipe=configurations();X,t,e,ids,p=survival()
    mutation(X,t,e,ids,p)
    with pytest.raises(ValueError):
        evaluate_synthetic_survival(cfg,recipe,X,t,e,row_ids=ids,people=p,
                                    horizon=5.,synthetic_fixture=True)


def test_survival_requires_horizon_support():
    cfg,_,recipe=configurations();X,t,e,ids,p=survival()
    with pytest.raises(ValueError):
        evaluate_synthetic_survival(cfg,recipe,X,t,e,row_ids=ids,people=p,
                                    horizon=100.,synthetic_fixture=True)


def test_longitudinal_next_visit_grouped_cv():
    cfg,_,recipe=configurations()
    X,lag,y,ids,p,t0,t1=transitions()
    one=evaluate_synthetic_longitudinal(cfg,recipe,X,lag,y,row_ids=ids,people=p,
                index_times=t0,target_times=t1,synthetic_fixture=True)
    two=evaluate_synthetic_longitudinal(cfg,recipe,X,lag,y,row_ids=ids,people=p,
                index_times=t0,target_times=t1,synthetic_fixture=True)
    assert one==two
    assert one['folds']==3 and one['variable_horizon']
    assert set(one['results'])=={'last_observation','ridge_with_lag'}
    assert all(v['rmse']>=0 and v['mae']>=0 for v in one['results'].values())


def test_longitudinal_real_fit_blocked():
    cfg,_,recipe=configurations();X,lag,y,ids,p,t0,t1=transitions()
    with pytest.raises(ValueError,match='Real-data'):
        evaluate_synthetic_longitudinal(cfg,recipe,X,lag,y,row_ids=ids,people=p,
                index_times=t0,target_times=t1)


@pytest.mark.parametrize('change',[lambda X,l,y,ids,p,t0,t1: t1.__setitem__(0,'2019-01-01'),
     lambda X,l,y,ids,p,t0,t1: l.__setitem__(1,l[1]+3),
     lambda X,l,y,ids,p,t0,t1: t0.__setitem__(1,'2019-01-01'),
     lambda X,l,y,ids,p,t0,t1: X.__setitem__('next_outcome',y),
     lambda X,l,y,ids,p,t0,t1: ids.__setitem__(1,ids[0]),
     lambda X,l,y,ids,p,t0,t1: p.__setitem__(0,None),
     lambda X,l,y,ids,p,t0,t1: y.__setitem__(0,float('nan')),
     lambda X,l,y,ids,p,t0,t1: t1.__setitem__(0,'not-a-date')])
def test_longitudinal_invalid_chronology_or_leakage_blocked(change):
    cfg,_,recipe=configurations();X,l,y,ids,p,t0,t1=transitions()
    change(X,l,y,ids,p,t0,t1)
    with pytest.raises(ValueError):
        evaluate_synthetic_longitudinal(cfg,recipe,X,l,y,row_ids=ids,people=p,
                index_times=t0,target_times=t1,synthetic_fixture=True)


def test_longitudinal_prediction_cannot_use_target_visit_features():
    cfg,_,recipe=configurations();X,l,y,ids,p,t0,t1=transitions()
    X['visit_future_measure']=y
    with pytest.raises(ValueError,match='Exact canonical'):
        evaluate_synthetic_longitudinal(cfg,recipe,X,l,y,row_ids=ids,people=p,
                index_times=t0,target_times=t1,synthetic_fixture=True)


def test_documentary_cli_source_plan_metadata(tmp_path):
    cfg,_,_=configurations()
    plan=make_plan(cfg)
    assert plan['no_participant_tables_opened'] is True
    assert plan['no_models_fitted'] is True
    assert plan['no_holdout_targets_accessed'] is True
    assert plan['route']=='BLOCKED_FOR_NEW_ANALYSIS'
