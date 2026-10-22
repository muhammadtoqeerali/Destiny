"""v0.15 logic and manifest-contract tests ONLY. No model fitting or research data."""
import copy
import math
import pytest
from ml.case_preprocess_selection_v15 import (
    SCHEMA, SUPPORTED_FAMILIES, canonical_sha, validate_design,
    choose_preprocessing, paired_summary,
)


def fixtures():
    manifest = {'case_id':'demo_case','task':'classification','features':{
        'numeric':['age','walking'], 'categorical':['sex']}}
    strategy = {'case_id':'demo_case','primary_metric':'brier'}
    selection = {'schema':'FRAILTYSCOPE_CASE_STRATEGY_V13',
        'holdout_used_in_selection':False,'manifest_sha256':canonical_sha(manifest),
        'protocol_sha256':canonical_sha(strategy),
        'selected_model':'logistic','selected_params':{'C':0.05}}
    ablation = {'case_id':'demo_case', 'variants':[
        {'name':'reference','drop_features':[],'numeric_missing_indicators':False},
        {'name':'missingness_indicators','drop_features':[], 'numeric_missing_indicators':True},
        {'name':'drop_walking','drop_features':['walking'],'numeric_missing_indicators':False}]}
    old = {'schema':'FRAILTYSCOPE_DEVELOPMENT_ABLATION_V14','case_id':'demo_case',
        'n_evaluation_predictions_generated':0,
        'selection_or_model_replacement_performed':False,
        'manifest_sha256':canonical_sha(manifest),'strategy_sha256':canonical_sha(strategy),
        'ablation_config_sha256':canonical_sha(ablation),
        'selected_model_fixed':'logistic','selected_hyperparameters_fixed':{'C':0.05},
        'primary_metric':'brier'}
    cfg = {'schema':SCHEMA, 'case_id':'demo_case','primary_metric':'brier',
        'variants':['reference','missingness_indicators'],'outer_folds':3,'inner_folds':3,
        'outer_seeds':[3411,3412],
        'regularization_grid':[0.01,0.05,0.2,1.0],
        'practical_tie_margin':0.001,
        'holdout_policy':'development_only_no_evaluation'}
    return cfg,manifest,strategy,selection,ablation,old


def test_accepts_frozen_verified_design():
    cfg,manifest,strategy,selection,ablation,old=fixtures()
    assert validate_design(cfg,manifest,strategy,selection,ablation,old) is cfg
    assert SUPPORTED_FAMILIES['logistic']==('classification','C')


@pytest.mark.parametrize('mutate', [
    lambda c,m,s,w,a,r:c.update(case_id='wrong'),
    lambda c,m,s,w,a,r:c.update(primary_metric='roc_auc'),
    lambda c,m,s,w,a,r:c.update(holdout_policy='evaluate'),
    lambda c,m,s,w,a,r:c.update(regularization_grid=[0.1, 0.01, 0.5]),
    lambda c,m,s,w,a,r:c.update(regularization_grid=[0,0.01,0.5]),
    lambda c,m,s,w,a,r:c.update(regularization_grid=[0.1,0.1,0.5]),
    lambda c,m,s,w,a,r:c.update(outer_seeds=[5,5]),
    lambda c,m,s,w,a,r:c.update(outer_folds=1),
    lambda c,m,s,w,a,r:c.update(inner_folds=6),
    lambda c,m,s,w,a,r:c.update(variants=['missingness_indicators','reference']),
    lambda c,m,s,w,a,r:c.update(variants=['reference','absent']),
    lambda c,m,s,w,a,r:c.update(variants=['reference','drop_walking']),
    lambda c,m,s,w,a,r:w.update(holdout_used_in_selection=True),
    lambda c,m,s,w,a,r:w.update(selected_model='catboost'),
    lambda c,m,s,w,a,r:w.update(manifest_sha256='corrupted'),
    lambda c,m,s,w,a,r:r.update(ablation_config_sha256='corrupted'),
    lambda c,m,s,w,a,r:r.update(n_evaluation_predictions_generated=12),
    lambda c,m,s,w,a,r:r.update(case_id='wrong'),
    lambda c,m,s,w,a,r:c.update(outer_seeds=[1,2,3,4],outer_folds=5,inner_folds=5,
        regularization_grid=[0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,0.2,0.5,1.0,2.0,3.0],
        variants=['reference','missingness_indicators','drop_walking']),
    lambda c,m,s,w,a,r:r.update(selected_hyperparameters_fixed={'C':0.9}),
    lambda c,m,s,w,a,r:m.update(task='regression'),
])
def test_rejects_unverified_or_leaking_design(mutate):
    objects=fixtures();mutate(*objects)
    with pytest.raises(ValueError):validate_design(*objects)


def test_inner_rule_choose_missingness_when_meaningful():
    rec=[{'variant':'reference','regularization':0.01,'loss':0.14},
         {'variant':'reference','regularization':0.1,'loss':0.135},
         {'variant':'missingness_indicators','regularization':0.01,'loss':0.1345},
         {'variant':'missingness_indicators','regularization':0.1,'loss':0.13}]
    v=choose_preprocessing(rec,['reference','missingness_indicators'],0.001)
    assert v['variant']=='missingness_indicators'
    assert v['reference_regularization']==0.1
    assert v['regularization']==0.1


def test_inner_rule_prefers_reference_within_practical_margin():
    rec=[{'variant':'reference','regularization':0.1,'loss':0.13},
         {'variant':'missingness_indicators','regularization':0.1,'loss':0.1294}]
    v=choose_preprocessing(rec,['reference','missingness_indicators'],0.001)
    assert v['variant']=='reference'
    assert len(v['eligible_variants'])==2


def test_inner_rule_requires_all_and_finite():
    with pytest.raises(ValueError):
        choose_preprocessing([{'variant':'reference','regularization':0.1,'loss':0.1}],
                             ['reference','missingness_indicators'],0.001)
    with pytest.raises(ValueError):
        choose_preprocessing([{'variant':'reference','regularization':0.1,'loss':math.nan},
            {'variant':'missingness_indicators','regularization':0.1,'loss':0.15}],
            ['reference','missingness_indicators'],0.001)


def test_paired_summary_uses_repeat_pairs_without_significance_claim():
    rows=[{'reference_loss':.14,'selected_loss':.13},
          {'reference_loss':.13,'selected_loss':.132}]
    s=paired_summary(rows)
    assert s['mean_loss_gain_vs_reference']==0.004
    assert s['repeats_with_lower_selection_loss']==1
    assert 'repeated' in s['inference'].lower()


def test_no_fit_during_import():
    import ml.case_preprocess_selection_v15 as module
    assert hasattr(module,'main') and hasattr(module,'run')
    assert not hasattr(module,'trained_model')
