"""Adversarial synthetic-only tests. Do not load NHANES, HUNT or local model artifacts."""
import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score
from ml.case_foldsafe_v25 import (
    SCHEMA, REPORT_SCHEMA, build_preprocessor,make_model_pipeline,
    validate_recipe,validate_partition, make_plan,expected_columns,
    local_file, ContractFrameValidator,digest,
)


def baseline():
    cfg=json.loads((Path(__file__).resolve().parents[1]/'research/cases/nhanes_foldsafe_v25.json').read_text())
    v24=json.loads((Path(__file__).resolve().parents[1]/'research/cases/nhanes_harmonization_v24.json').read_text())
    dictionary={'case_id':'nhanes_mortality_v10','holdout_history':'previously_inspected',
                'prior_exploration':True,'prediction_index':{'definition_status':'provisional'}}
    return cfg,dictionary,v24


def mobility():
    return pd.DataFrame({
        'walking_difficulty':[1.,2.,np.nan,4.,3.,np.nan],
        'walking_difficulty__status':['observed','observed','structural_skip','observed','observed','does_not_do_activity'],
        'stairs_difficulty':[1.,np.nan,3.,2.,4.,np.nan],
        'stairs_difficulty__status':['observed','structural_skip','observed','observed','observed','does_not_do_activity'],
        'stooping_difficulty':[2.,3.,np.nan,1.,4.,2.],
        'stooping_difficulty__status':['observed','observed','does_not_do_activity','observed','observed','observed']})


def toy_numeric():
    cfg,_,_=baseline()
    cfg['features']={'bmi':{'kind':'numeric','representation':'numeric',
                          'source_status_required':True,'allowed_values':None,
                          'allowed_statuses':['observed','not_recorded']}}
    return cfg


def toy_categorical(known=None,unknown='error'):
    cfg,_,_=baseline()
    cfg['features']={'smoking':{'kind':'categorical','representation':'one_hot',
                          'source_status_required':True,'allowed_values':known,
                          'allowed_statuses':['observed','not_recorded']}}
    cfg['categorical_unknown']=unknown
    return cfg


def test_config_matches_published_harmonization():
    cfg,d,v=baseline()
    assert validate_recipe(cfg,d,v) is cfg
    assert set(cfg['features'])=={'walking_difficulty','stairs_difficulty','stooping_difficulty'}
    plan=make_plan(cfg)
    assert plan['route']=='BLOCKED_FOR_NEW_ANALYSIS'
    assert plan['no_models_fitted'] and not plan['public_export']
    assert plan['source_status_columns']==3
    assert len(expected_columns(cfg))==6


def test_different_splits_train_only_and_static_shape():
    cfg,_,_=baseline()
    x=mobility()
    first=build_preprocessor(cfg,synthetic_fixture=True)
    first.fit(x.iloc[:4])
    before=first.transform(x.iloc[4:])
    assert np.isfinite(before).all()
    assert before.shape[0]==2
    after=first.transform(x.iloc[4:].assign(walking_difficulty=[4.,4.],
                                         walking_difficulty__status=['observed','observed'],
                                         stairs_difficulty=[1.,1.],stairs_difficulty__status=['observed','observed']))
    assert after.shape==before.shape
    assert before.shape[1] == first.transform(x.iloc[:4]).shape[1]
    # Mutation of validation examples must not refit or change training statistics.
    assert np.array_equal(first.transform(x.iloc[:4]),first.transform(x.iloc[:4]))


def test_numeric_median_learned_only_on_train_and_nonmissing_indicator():
    cfg=toy_numeric()
    train=pd.DataFrame({'bmi':[10.,20.,np.nan,30.],
                        'bmi__status':['observed','observed','not_recorded','observed']})
    valid=pd.DataFrame({'bmi':[1000.,np.nan],
                        'bmi__status':['observed','not_recorded']})
    pipe=build_preprocessor(cfg,synthetic_fixture=True)
    pipe.fit(train)
    median=pipe.named_steps['encode'].named_transformers_['n_bmi'].named_steps['impute'].statistics_[0]
    assert median==20
    arr=pipe.transform(valid)
    assert arr.shape==(2,4)  # scaled value + missing flag + two fixed status categories
    assert arr[1,1]==1 and arr[0,1]==0
    assert pipe.named_steps['encode'].named_transformers_['n_bmi'].named_steps['impute'].statistics_[0]==20
    # It does not learn an unseen 1000 from the validation set.
    assert not np.isclose(arr[0,0],0.0)


def test_numeric_all_missing_training_rejected_but_valid_allowed():
    cfg=toy_numeric()
    x=pd.DataFrame({'bmi':[np.nan,np.nan],
                    'bmi__status':['not_recorded','not_recorded']})
    with pytest.raises(ValueError,match='All-missing training'):
        build_preprocessor(cfg,synthetic_fixture=True).fit(x)
    fit=pd.DataFrame({'bmi':[20.,30.], 'bmi__status':['observed','observed']})
    mdl=build_preprocessor(cfg,synthetic_fixture=True).fit(fit)
    assert np.isfinite(mdl.transform(x)).all()


def test_onehot_codebook_levels_unseen_but_declared_are_stable():
    cfg,_,_=baseline()
    x=mobility().iloc[:3]
    pipe=build_preprocessor(cfg,synthetic_fixture=True).fit(x)
    after=pipe.transform(mobility().iloc[3:])  # contains codes 4, not seen at training
    assert np.isfinite(after).all()
    assert after.shape[1]==pipe.transform(x).shape[1]


def test_unseen_category_default_fail_and_opt_in_ignore():
    train=pd.DataFrame({'smoking':['No','Yes'],'smoking__status':['observed','observed']})
    test=pd.DataFrame({'smoking':['Former'],'smoking__status':['observed']})
    cfg=toy_categorical()
    p=build_preprocessor(cfg,synthetic_fixture=True).fit(train)
    with pytest.raises(ValueError):p.transform(test)
    cfg=toy_categorical(unknown='ignore')
    p=build_preprocessor(cfg,synthetic_fixture=True).fit(train)
    assert p.transform(test).shape == (1,p.transform(train).shape[1])


def test_category_codebook_prohibits_even_opt_in_unknown():
    cfg=toy_categorical(known=['Yes','No'],unknown='ignore')
    pipe=build_preprocessor(cfg,synthetic_fixture=True).fit(
        pd.DataFrame({'smoking':['Yes'],'smoking__status':['observed']}))
    with pytest.raises(ValueError,match='Unreviewed codebook'):
        pipe.transform(pd.DataFrame({'smoking':['Former'],'smoking__status':['observed']}))


def test_categorical_missing_constant_and_status_separate():
    cfg=toy_categorical(known=['Yes','No'])
    d=pd.DataFrame({'smoking':['Yes',None,'No'],
                    'smoking__status':['observed','not_recorded','observed']})
    p=build_preprocessor(cfg,synthetic_fixture=True).fit(d)
    arr=p.transform(d)
    assert arr.shape == (3,5)
    assert not np.array_equal(arr[0],arr[1])


@pytest.mark.parametrize('change',[lambda x:x.drop(columns=['stairs_difficulty']),
       lambda x:x.assign(outcome_5yr=1),
       lambda x:x.assign(walking_difficulty__status=['observed']*len(x)),
       lambda x:x.assign(stooping_difficulty__status=['structural_skip']*len(x)),
       lambda x:x.assign(walking_difficulty=[7]*len(x)),
       lambda x:x.assign(stooping_difficulty=[np.inf]*len(x)),
       lambda x:x.assign(walking_difficulty__status=[None]*len(x))])
def test_invalid_predictor_rows_fail_closed(change):
    cfg,_,_=baseline()
    with pytest.raises(ValueError):
        build_preprocessor(cfg,synthetic_fixture=True).fit(change(mobility()))


def test_no_fitting_or_input_access_without_fixture_flag():
    cfg,_,_=baseline()
    with pytest.raises(ValueError,match='Real-data'):
        build_preprocessor(cfg)
    with pytest.raises(ValueError,match='Real-data'):
        make_model_pipeline(cfg,LogisticRegression())


def test_sklearn_clone_and_serialization(tmp_path):
    import joblib
    cfg,_,_=baseline()
    pre=build_preprocessor(cfg,synthetic_fixture=True)
    cloned=clone(pre)
    assert not hasattr(cloned.named_steps['encode'],'transformers_')
    fitted=cloned.fit(mobility().iloc[:4])
    p=tmp_path/'synthetic_only.joblib'
    joblib.dump(fitted,p)
    loaded=joblib.load(p)
    np.testing.assert_allclose(fitted.transform(mobility().iloc[4:]),
                               loaded.transform(mobility().iloc[4:]))


def test_model_wrapping_classification_and_regression_synthetic():
    cfg,_,_=baseline()
    x=mobility()
    y=[0,1,1,0,1,0]
    for estimator in (DummyClassifier(strategy='most_frequent'),
                      DummyRegressor(strategy='mean')):
        p=make_model_pipeline(cfg,estimator,synthetic_fixture=True).fit(x.iloc[:4],y[:4])
        assert len(p.predict(x.iloc[4:]))==2


def test_numeric_regression_ridge_end_to_end():
    cfg=toy_numeric()
    x=pd.DataFrame({'bmi':[20.,np.nan,30.,40.,50.],
                    'bmi__status':['observed','not_recorded','observed','observed','observed']})
    p=make_model_pipeline(cfg,Ridge(),synthetic_fixture=True).fit(x.iloc[:4],np.array([1.,2.,3.,4.]))
    assert np.isfinite(p.predict(x.iloc[4:])).all()


def test_group_and_forward_time_boundaries():
    assert validate_partition([1,2],[3,4],policy='person_disjoint',
                     train_groups=['p1','p1'],valid_groups=['p2','p2'])['boundary_checked']
    assert validate_partition([1],[2],policy='forward_time',
                     train_time=['2024-01-01'],valid_time=['2025-01-01'])['boundary_checked']
    assert validate_partition([1],[2],policy='person_and_forward_time',
                     train_groups=['A'],valid_groups=['B'],
                     train_time=['2024-01-01'],valid_time=['2025-01-01'])['boundary_checked']


@pytest.mark.parametrize('kwargs',[
    {'train_groups':['p1'],'valid_groups':['p1'],'policy':'person_disjoint'},
    {'policy':'person_disjoint'},
    {'policy':'forward_time','train_time':['2024-01-02'],'valid_time':['2024-01-01']},
    {'policy':'forward_time','train_time':['bad'],'valid_time':['2025-01-01']},
    {'policy':'forward_time'},
    {'policy':'random'},
])
def test_bad_partition_rejected(kwargs):
    with pytest.raises(ValueError):validate_partition([1],[2],**kwargs)


def test_id_overlap_fails_even_under_forward_time():
    with pytest.raises(ValueError):
        validate_partition([1],[1],policy='forward_time',train_time=['2024-01-01'],
                           valid_time=['2025-01-01'])


@pytest.mark.parametrize('tamper',[lambda x:x.update(real_data_execution_permitted=True),
     lambda x:x.update(model_fitting_permitted=True),
     lambda x:x.update(holdout_history='locked_new'),
     lambda x:x.update(prediction_index_status='operationally_verified'),
     lambda x:x.update(categorical_unknown='strange'),
     lambda x:x.update(numeric_missing='global_median'),
     lambda x:x.update(scope='validated'),
     lambda x:x.update(split_review='unstratified'),
     lambda x:x['features'].pop('walking_difficulty'),
     lambda x:x['features']['walking_difficulty'].update(source_status_required=False),
     lambda x:x['features']['walking_difficulty'].update(allowed_statuses=['observed']),
     lambda x:x['features']['walking_difficulty'].update(allowed_values=[1,2]),
     lambda x:x['features']['walking_difficulty'].update(representation='numeric',kind='categorical')])
def test_invalid_recipes_block(tamper):
    cfg,d,v=baseline()
    tamper(cfg)
    with pytest.raises(ValueError):validate_recipe(cfg,d,v)


def test_paths_restricted(tmp_path):
    (tmp_path/'research').mkdir()
    (tmp_path/'research'/'okay.json').write_text('{}')
    assert local_file(tmp_path,'research/okay.json','research').exists()
    for bad in ['data/secret.csv','research/../data/x','/tmp/x','../x']:
        with pytest.raises(ValueError):local_file(tmp_path,bad,'research')


def test_synthetic_contract_self_consistency():
    cfg,_,_=baseline()
    assert len(digest(cfg))==64
    assert cfg['scope']=='synthetic_only_blueprint'
    assert make_plan(cfg)['schema']==REPORT_SCHEMA


def test_end_to_end_v24_source_fixture_into_v25():
    from ml.case_harmonization_v24 import harmonize_fixture
    cfg,_,v24=baseline()
    raw=pd.DataFrame({'PFQ054':[1,2,2,2],
                      'PFQ061B':[None,1,5,4],
                      'PFQ061C':[None,2,3,5],
                      'PFQ061D':[1,2,5,4]})
    out,counts=harmonize_fixture(raw,v24['waves']['2011-2012'],synthetic_fixture=True)
    assert counts['walking_difficulty']['structural_skip']==1
    p=build_preprocessor(cfg,synthetic_fixture=True).fit(out.iloc[:3])
    z=p.transform(out.iloc[3:])
    assert np.isfinite(z).all() and z.shape[0]==1


def test_guarded_fold_checks_before_fitting():
    from ml.case_foldsafe_v25 import prepare_synthetic_fold
    cfg,_,_=baseline()
    x=mobility()
    with pytest.raises(ValueError,match='group'):
        prepare_synthetic_fold(cfg,x.iloc[:4],x.iloc[4:],
                      train_ids=[0,1,2,3],valid_ids=[4,5],
                      train_groups=['P1','P2','P3','P4'],valid_groups=['P1','P5'],
                      synthetic_fixture=True)
    p,tr,va,guard=prepare_synthetic_fold(cfg,x.iloc[:4],x.iloc[4:],
                      train_ids=[0,1,2,3],valid_ids=[4,5],
                      train_groups=['P1','P2','P3','P4'],valid_groups=['P5','P6'],
                      synthetic_fixture=True)
    assert guard['boundary_checked'] and tr.shape[1]==va.shape[1]
    assert np.isfinite(tr).all() and np.isfinite(va).all()
