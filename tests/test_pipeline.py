import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from ml.schema import FEATURES, TARGET
from ml.simulate import generate
from ml.train import make_pipeline, split_data, verify_synthetic


def test_synthetic_generation_reproducible_and_in_range():
    a = generate(200, 11)
    b = generate(200, 11)
    pd.testing.assert_frame_equal(a, b)
    assert a.age.between(70, 103).all()
    assert a[TARGET].isin([0, 1]).all()
    assert (a.data_origin == 'SYNTHETIC').all()
    assert TARGET not in FEATURES


def test_no_person_leaks_across_splits():
    train, val, test = split_data(generate(300, 7))
    assert len(train) + len(val) + len(test) == 300
    assert not set(train.patient_id) & set(val.patient_id)
    assert not set(val.patient_id) & set(test.patient_id)
    assert not set(train.patient_id) & set(test.patient_id)


def test_refuse_non_synthetic_export():
    df = generate(150, 12)
    df.loc[0, 'data_origin'] = 'HUNT'
    with pytest.raises(ValueError, match='PROTECTION'):
        verify_synthetic(df)


def test_missing_values_supported_by_training_pipeline():
    df = generate(240, 8)
    model = make_pipeline(LogisticRegression(max_iter=1000))
    model.fit(df[FEATURES], df[TARGET])
    pred = model.predict_proba(df[FEATURES].iloc[:4])[:, 1]
    assert np.isfinite(pred).all()
    assert ((pred >= 0) & (pred <= 1)).all()


def test_feature_groups_are_well_defined():
    from ml.train import FEATURE_GROUPS
    assert set(FEATURE_GROUPS['Clinical']) < set(FEATURE_GROUPS['Expanded'])
    assert len(FEATURE_GROUPS['Expanded']) == len(FEATURES)
    assert 'activity_minutes_day' not in FEATURE_GROUPS['Clinical']


def test_bootstrap_intervals_and_decision_curve():
    from ml.train import bootstrap_intervals, decision_curve
    y = np.array([0, 0, 1, 1] * 20)
    p = np.array([0.04, 0.20, 0.7, 0.8] * 20)
    ci = bootstrap_intervals(y,p,seed=12,repeats=80)
    assert ci['roc_auc'][0] <= ci['roc_auc'][1]
    assert 0 <= ci['brier'][0] <= 1
    curve = decision_curve(y,p)
    assert len(curve) == 8
    assert all('model' in x and 'all' in x for x in curve)


def test_core_model_with_missing_data():
    from ml.train import CORE_FEATURES
    df = generate(200,13)
    model = make_pipeline(LogisticRegression(max_iter=1000),CORE_FEATURES)
    model.fit(df[CORE_FEATURES],df[TARGET])
    p = model.predict_proba(df[CORE_FEATURES].head(5))[:,1]
    assert np.isfinite(p).all()
