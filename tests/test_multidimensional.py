import pandas as pd
import pytest
from ml.multioutcome import OUTCOMES, make_synthetic_cohort, simulated_history
from ml.approved_hunt_adapter import make_labels,describe_labels
from ml.schema import FEATURES


def baseline():
    return pd.DataFrame([{'participant_id':'PROJECT-0001','baseline_date':'2020-01-01',**{f:1 for f in FEATURES}}])

def test_simulator_endpoints_and_provenance():
    df=make_synthetic_cohort(n=130,seed=33)
    assert df.data_origin.eq('SYNTHETIC').all()
    assert len(OUTCOMES)==5
    assert all(df[k].isin([0,1]).all() for k in OUTCOMES)
    assert len(simulated_history(df.iloc[0]))==3

def test_censoring_not_a_negative():
    follow=pd.DataFrame([{'participant_id':'PROJECT-0001','last_observed_date':'2020-04-01','first_fall_date':None}])
    df=make_labels(baseline(),follow)
    assert pd.isna(df.loc[0,'fall_within_12m'])
    assert pd.isna(df.loc[0,'fracture_within_12m'])

def test_observed_event_before_dropout():
    follow=pd.DataFrame([{'participant_id':'PROJECT-0001','last_observed_date':'2020-05-01','first_fall_date':'2020-03-01'}])
    df=make_labels(baseline(),follow)
    assert df.loc[0,'fall_within_12m']==1
    assert pd.isna(df.loc[0,'fracture_within_12m'])

def test_complete_followup_negative():
    follow=pd.DataFrame([{'participant_id':'PROJECT-0001','last_observed_date':'2021-04-01','first_fall_date':None}])
    df=make_labels(baseline(),follow)
    assert df.loc[0,'fall_within_12m']==0
    assert describe_labels(df)['fall_within_12m']['eligible']==1

def test_death_truncates_nonmortality():
    follow=pd.DataFrame([{'participant_id':'PROJECT-0001','last_observed_date':'2021-04-01','death_date':'2020-02-01','first_fall_date':None}])
    df=make_labels(baseline(),follow)
    assert pd.isna(df.loc[0,'fall_within_12m'])

def test_no_direct_identifiers():
    follow=pd.DataFrame([{'participant_id':'PROJECT-0001','last_observed_date':'2021-04-01'}])
    b=baseline();b['ssn']='123'
    with pytest.raises(ValueError,match='Direct identifiers'):
        make_labels(b,follow)

def test_duplicate_rejected():
    follow=pd.DataFrame([{'participant_id':'PROJECT-0001','last_observed_date':'2021-04-01'}])
    with pytest.raises(ValueError,match='one baseline'):
        make_labels(pd.concat([baseline(),baseline()]),follow)


def test_public_export_blocked_for_approved_mode(tmp_path):
    from ml.advanced_multitarget import run
    df=make_synthetic_cohort(n=120,seed=11)
    with pytest.raises(ValueError,match='SECURITY'):
        run(df,mode='approved-local',export=tmp_path/'web/public/data/forbidden.json')

def test_benchmark_metrics_distinguish_accuracy_from_auc():
    import numpy as np
    from ml.advanced_multitarget import score
    y=pd.Series([0]*95+[1]*5)
    predictions=np.full(len(y),0.05)
    assert score(y,predictions)['roc_auc']==.5
    # A constant classifier has 95% accuracy but no ranking ability.
    assert ((predictions>=.5)==y.to_numpy()).mean()==.95
