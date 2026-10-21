"""Synthetic UNIT-TEST fixtures only; never research data or dashboard content."""
import __main__
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from ml.case_engine_v10 import (
    CatBoostClassifierAdapter, calculate_metrics, digest, make_preprocess, split_data,
)
from ml.case_model_io_v11 import repair_model, load_legacy_or_canonical


def test_legacy_main_catboost_artifact_recovers_without_retraining(tmp_path):
    import pytest
    pytest.importorskip('catboost')
    rng = np.random.default_rng(2026)
    n = 175
    x = rng.normal(size=n)
    sex = np.where(rng.uniform(size=n) > .5, 'Female', 'Male')
    outcome = (x + .55*(sex=='Male') + rng.normal(size=n)*.6 > .2).astype(int)
    df = pd.DataFrame({'participant_no':range(n),'age':np.round(74+5*x,1),
       'sex':sex,'outcome':outcome, 'cohort':['dev']*115+['later']*60})
    raw = tmp_path/'data'/'unit.csv'
    raw.parent.mkdir(parents=True)
    df.to_csv(raw,index=False)
    spec = {'case_id':'test_case', 'source':{'path':'data/unit.csv'},
       'task':'classification','id_column':'participant_no','target':'outcome',
       'features':{'numeric':['age'],'categorical':['sex']},
       'split':{'strategy':'cohort','column':'cohort','development':'dev',
                'evaluation':'later','validation_fraction':.25},
       'models':['dummy','catboost'],'selection_metric':'brier','cv_folds':3,
       'trials_per_model':1}
    conf = tmp_path/'research'/'cases'/'case.json'
    conf.parent.mkdir(parents=True)
    conf.write_text(json.dumps(spec))
    train,valid,test = split_data(df,df.outcome,spec)
    # Create a real fitted model whose class was originally saved under __main__.
    Legacy = type('CatBoostClassifierAdapter',(CatBoostClassifierAdapter,),{})
    Legacy.__module__='__main__'
    former = getattr(__main__,'CatBoostClassifierAdapter',None)
    setattr(__main__,'CatBoostClassifierAdapter',Legacy)
    try:
        pipeline=Pipeline([('features',make_preprocess(['age'],['sex'])),
             ('model',Legacy(iterations=25,depth=2,learning_rate=.08))])
        pipeline.fit(df.iloc[train][['age','sex']],df.iloc[train].outcome)
        out=tmp_path/'artifacts'/'cases'/'test_case'
        out.mkdir(parents=True)
        file=out/'best_model.joblib'
        joblib.dump(pipeline,file)
        before=file.read_bytes()
    finally:
        if former is None:delattr(__main__,'CatBoostClassifierAdapter')
        else:setattr(__main__,'CatBoostClassifierAdapter',former)
    scores=pipeline.predict_proba(df.iloc[test][['age','sex']])[:,1]
    met=calculate_metrics('classification',df.iloc[test].outcome,scores,scores,.45)
    (out/'metrics.json').write_text(json.dumps({'case_id':'test_case','task':'classification',
       'dataset_sha256':digest(raw),'selected_model':'catboost',
       'selected_threshold':.45,'evaluation':met}))
    # Without the temporary legacy alias, ordinary loading must fail.
    import pytest
    with pytest.raises(AttributeError, match='CatBoostClassifierAdapter'):
        joblib.load(file)
    status=repair_model(tmp_path,'research/cases/case.json')
    assert status['status']=='REPAIRED_AND_VERIFIED'
    assert status['n']==len(test)
    assert (out/'best_model.v10_legacy_backup.joblib').read_bytes()==before
    fixed=joblib.load(file)
    assert type(fixed.named_steps['model']) is CatBoostClassifierAdapter
    assert np.array_equal(fixed.predict_proba(df.iloc[test][['age','sex']]),
                          pipeline.predict_proba(df.iloc[test][['age','sex']]))
    assert repair_model(tmp_path,'research/cases/case.json')['status']=='ALREADY_CANONICAL_AND_VERIFIED'


def test_non_legacy_attribute_errors_do_not_get_silenced(tmp_path):
    # A corrupt or arbitrary artifact is not automatically interpreted as a legacy model.
    p=tmp_path/'bad.joblib'
    p.write_text('not a joblib model')
    import pytest
    with pytest.raises(Exception):
        load_legacy_or_canonical(p)
