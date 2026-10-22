"""Only arithmetic/contract fixtures. Do not train or load any ML model."""
import copy
import json

import pytest

from ml.case_stability_v17 import (
    CONFIG_SCHEMA, SCHEMA, equal_frequency_calibration, paired_diagnostics,
    summarize_selection, summarize_importance, verify_config,validate_local_report,
)


def contracts():
    joint={
        'schema':'FRAILTYSCOPE_JOINT_SELECTION_V16',
        'case_id':'sample_case', 'metric':'brier',
        'families':['logistic','random_forest'],
        'variants':[{'name':'reference','numeric_missing_indicators':False,'drop_features':[]},
                    {'name':'missingness_indicators','numeric_missing_indicators':True,'drop_features':[]}],
        'outer_seeds':[4216], 'outer_folds':3, 'inner_folds':3,
        'screen_trials':2,'refine_trials':8,'top_k':2,
        'baseline_regularization_grid':[0.02,0.1,1.],
    }
    from ml.case_joint_selection_v16 import digest_json
    manifest={'case_id':'sample_case','features':{'numeric':['age','bmi','mobility'],
                                                  'categorical':['sex']}}
    cfg={'schema':CONFIG_SCHEMA,'case_id':'sample_case','v16_config':'research/cases/case_joint.json',
         'v16_protocol_sha256':digest_json(joint),'metric':'brier',
         'outer_seeds':[4217,4218], 'permutation_repeats':2,'importance_top_k':3,
         'calibration_bins':5,'min_calibration_bin_n':40,'max_estimated_fits':1400,
         'prior_development_exploration':True,'holdout_policy':'development_only_no_evaluation'}
    return cfg,joint,manifest


def test_config_accepts_exact_reusable_design():
    c,j,m=contracts()
    r=verify_config(c,j,m)
    assert r['candidate_pairs']==4
    assert r['repeated_outer_assessments']==6
    assert r['estimated_fit_upper_bound']<=1400


@pytest.mark.parametrize('key,val',[
    ('v16_protocol_sha256','bad'),('metric','roc_auc'),('holdout_policy','holdout_ok'),
    ('prior_development_exploration',False),('outer_seeds',[4216,4217]),
    ('outer_seeds',[12,12]),('permutation_repeats',0),('importance_top_k',100),
    ('max_estimated_fits',50),('calibration_bins',2),('min_calibration_bin_n',10),
])
def test_config_rejects_unsafe_or_inconsistent_choice(key,val):
    c,j,m=contracts();c[key]=val
    with pytest.raises(ValueError): verify_config(c,j,m)


def test_calibration_uses_actual_probabilities_no_fit():
    import numpy as np
    y=np.r_[np.zeros(60,dtype=int),np.ones(60,dtype=int)]
    p=np.r_[np.full(60,.2),np.full(60,.8)]
    r=equal_frequency_calibration(y,p,3,30)
    assert sum(bin['n'] for bin in r['bins'])==120
    assert r['mean_prediction']==r['observed_prevalence']==.5
    assert r['ece_descriptive']>=0


def test_calibration_rejects_invalid_probabilities_and_small_bins():
    with pytest.raises(ValueError):equal_frequency_calibration([0,1]*10,[.1,.9]*10,3,30)
    with pytest.raises(ValueError):equal_frequency_calibration([0,1]*50,[.1,1.1]*50,2,30)


def test_oof_paired_metric_regression_fixture():
    y=[0,0,1,1]*10
    b=[.3,.3,.7,.7]*10
    a=[.1,.1,.9,.9]*10
    r=paired_diagnostics(y,a,b,'classification')
    assert r['brier_gain_vs_reference']>.05
    assert r['joint']['roc_auc']==1


def test_paired_diagnostics_rejects_mismatched_scores():
    with pytest.raises(ValueError):paired_diagnostics([0,1]*10,[.5]*19,[.5]*20,'classification')


def test_fold_frequency_nonindependence_not_hidden():
    rows=[{'selected_pair':'logistic__reference'},
          {'selected_pair':'random_forest__missingness_indicators'},
          {'selected_pair':'logistic__reference'}]
    choices=['logistic__reference','random_forest__missingness_indicators']
    r=summarize_selection(rows,choices)
    assert r['model_frequency']['logistic']==2
    assert r['preprocessing_frequency']['missingness_indicators']==1
    assert r['pair_frequency'][0]['fraction']==.6667
    with pytest.raises(ValueError):summarize_selection([{'selected_pair':'bad'}],choices)


def test_feature_permutation_omitted_columns_are_not_zero():
    rows=[{'feature_drops':{'age':.01,'bmi':.001,'sex':.005}},
          {'feature_drops':{'age':.003,'sex':-.002}}]
    a=summarize_importance(rows,['age','bmi','sex'],2)
    by={row['feature']:row for row in a}
    assert by['bmi']['assessed_folds']==1
    assert by['age']['assessed_folds']==2
    assert by['bmi']['mean_metric_decrease']!=0
    with pytest.raises(ValueError):summarize_importance([{'feature_drops':{'alien':1}}],['age'],2)


def test_report_release_boundary_rejects_unapproved_export():
    from ml.case_joint_selection_v16 import digest_json
    c,j,m=contracts()
    result={'schema':SCHEMA,'report_type':'LOCAL_DEVELOPMENT_STABILITY_DIAGNOSTICS_ONLY',
            'case_id':'sample_case','v16_protocol_sha256':digest_json(j),
            'stability_protocol_sha256':digest_json(c),'manifest_sha256':digest_json(m),
            'holdout_scored':False,'existing_model_replaced':False,
            'cohort':{'evaluation_predictions_generated':0},'public_export':False,
            'n_model_binaries_exported':0,'fold_selections':[
                {'selected_pair':'logistic__reference'} for _ in range(6)],
            'repeated_development_metrics':[{'seed':4217},{'seed':4218}],
            'importance_stability':[{'feature':x} for x in ['age','bmi','mobility','sex']]}
    assert validate_local_report(c,j,m,result)['outer_assessments']==6
    for key,value in [('holdout_scored',True),('existing_model_replaced',True),
                      ('public_export',True),('n_model_binaries_exported',1)]:
        bad=copy.deepcopy(result);bad[key]=value
        with pytest.raises(ValueError):validate_local_report(c,j,m,bad)


def test_module_import_has_no_fit_or_data_side_effects():
    import ml.case_stability_v17 as module
    assert callable(module.run) and callable(module.main)
    assert not hasattr(module,'trained_model')
