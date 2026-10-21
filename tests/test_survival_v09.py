"""Small synthetic unit-test fixtures ONLY; never research datasets."""
import numpy as np
import pandas as pd
import pytest
from ml.nhanes_survival_v09 import (
    FEATURES,Preprocess,construct_time_to_event,penalized_cox,
    predict_event_risk,censor_km,g_at,ipcw_brier_at,concordance,observed_horizon_auc)


def test_keep_early_censored_for_survival():
    d=pd.DataFrame({'ELIGSTAT':[1,1,1,2], 'MORTSTAT':[0,1,1,0],
                    'PERMTH_EXM':[30,45,75,24]})
    out=construct_time_to_event(d)
    assert out.duration.tolist()==[30,45,60]
    assert out.event.tolist()==[0,1,0]


def test_preprocess_train_only_and_missing_indicators():
    d=pd.DataFrame({x:[1.,2.,np.nan,3.] for x in FEATURES})
    d['sex']=['Male','Female','Male','Female']
    p=Preprocess().fit(d)
    held=d.iloc[:2].copy();held['age']=[10000,11000]
    z=p.transform(held)
    assert z.shape[0]==2 and np.isfinite(z).all()
    assert p.medians[FEATURES.index('age')]==2.
    assert 'missing:age' in p.names


def test_fit_cox_direction_and_bounds():
    rng=np.random.default_rng(12)
    n=140
    x=rng.normal(size=(n,1));true_t=rng.exponential(scale=np.exp(-1.0*x[:,0])*10)
    censor=rng.uniform(3,20,size=n)
    t=np.minimum(true_t,censor);e=(true_t<=censor).astype(int)
    beta,events,cum=penalized_cox(x,t,e,0.05)
    assert beta[0]>0.1
    risk=predict_event_risk(np.array([[-2.],[2.]]),beta,events,cum,10)
    assert 0<=risk[0]<risk[1]<=1


def test_g_censor_and_ipcw_uncensored_brier():
    t=np.array([10.,20.,70.,70.]);e=np.array([1,1,0,0])
    g=censor_km(t,e)
    assert g_at(g,60)==1.
    score,c=ipcw_brier_at(t,e,np.array([.8,.6,.2,.1]),g,60)
    assert c==0
    assert np.isclose(score,np.mean([.2**2,.4**2,.2**2,.1**2]))
    assert np.isclose(concordance(t,e,np.array([.9,.8,.3,.1])),1.)
    auc,n,c=observed_horizon_auc(t,e,np.array([.9,.8,.3,.1]))
    assert (auc,n,c)==(1.,4,0)


def test_ipcw_early_censor_excluded_and_weighted():
    t=np.array([10.,20.,70.,70.,30.]);e=np.array([1,0,0,0,0])
    g=censor_km(t,e)
    result,c=ipcw_brier_at(t,e,np.full(5,.5),g)
    assert c==2  # 20 and 30 month censoring
    assert result>0


def test_fail_closed_on_bad_training():
    with pytest.raises(ValueError):
        penalized_cox(np.ones((12,2)),np.ones(12),np.zeros(12,int),0.1)
    with pytest.raises(ValueError):
        ipcw_brier_at(np.array([30.]),np.array([0]),np.array([1.2]),[])


def test_admin_cutoff_is_not_early_censoring():
    t=np.array([10.,60.,60.,60.]);e=np.array([1,0,0,0])
    # Three participants administratively stop exactly at 60 months.
    # IPCW must use G(60-), rather than G(60)=0.
    score,unknown=ipcw_brier_at(t,e,np.array([.8,.1,.2,.3]),censor_km(t,e))
    assert 0<score<1 and unknown==0
