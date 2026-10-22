"""PURE logic/security tests. No dataset loaded, no models fitted or inferred."""
import copy
import math
import sys
import types
import pytest

from ml.case_joint_selection_v16 import (
    SCHEMA, pair_name, candidate_pairs, estimated_fit_count, select_pair,
    paired_summary, digest_json, validate_config, validate_local_release, require,
)


def contracts():
    cfg={'schema':SCHEMA,'case_id':'sample_case','v15_config':'research/cases/v15.json',
         'metric':'brier', 'manifest':'research/cases/case.json',
         'strategy_protocol':'research/cases/strategy.json',
         'prior_exploration_of_development':True, 'families':['logistic','catboost','random_forest'],
         'variants':[{'name':'reference','drop_features':[],'numeric_missing_indicators':False},
                     {'name':'missingness_indicators','drop_features':[],'numeric_missing_indicators':True}],
         'baseline_regularization_grid':[.01,.1,1.], 'baseline_family':'logistic',
         'outer_folds':3,'inner_folds':3,'outer_seeds':[4216],
         'screen_trials':2,'refine_trials':8,'top_k':2,
         'practical_tie_margin':.001,'holdout_policy':'development_only_no_evaluation'}
    manifest={'case_id':'sample_case','task':'classification',
              'models':['dummy','logistic','catboost','random_forest'],
              'features':{'numeric':['age'],'categorical':['sex']}}
    strategy={'case_id':'sample_case','primary_metric':'brier',
              'candidates':['logistic','catboost','random_forest']}
    return cfg,manifest,strategy


@pytest.fixture
def stub_v13(monkeypatch):
    """Test v0.16 pure contract against v0.13 public interface without data/files."""
    mod=types.ModuleType('ml.case_strategy_v13')
    mod.METRICS={'classification':{'brier','roc_auc','average_precision'},
                 'regression':{'rmse','mae'}}
    mod.validate_protocol=lambda strategy,manifest:strategy
    monkeypatch.setitem(sys.modules,'ml.case_strategy_v13',mod)


def test_candidate_pairs_and_fit_budget():
    cfg,*_=contracts()
    assert len(candidate_pairs(cfg))==6
    assert candidate_pairs(cfg)[0]==('logistic','reference')
    assert candidate_pairs(cfg)[-1]==('random_forest','missingness_indicators')
    assert pair_name('catboost','reference')=='catboost__reference'
    assert estimated_fit_count(cfg,3)==(3*((6*2+2*8+3)*3+2)+(6*2+2*8)*3+3+1)


def test_valid_contract(stub_v13):
    cfg,manifest,strategy=contracts()
    assert validate_config(cfg,manifest,strategy) is cfg


@pytest.mark.parametrize('tamper',[
    lambda c,m,s:c.update(case_id='other'),
    lambda c,m,s:c.update(metric='roc_auc'),
    lambda c,m,s:c.update(families=['logistic','logistic']),
    lambda c,m,s:c.update(families=['logistic','ridge']),
    lambda c,m,s:c.update(families=['logistic']),
    lambda c,m,s:c.update(variants=[c['variants'][0]]),
    lambda c,m,s:c['variants'][1].update(name='omit_phq9'),
    lambda c,m,s:c.update(holdout_policy='allow_evaluation'),
    lambda c,m,s:c.update(outer_folds=6),
    lambda c,m,s:c.update(outer_seeds=[1,1]),
    lambda c,m,s:c.update(practical_tie_margin=float('nan')),
    lambda c,m,s:c.update(screen_trials=8,refine_trials=2),
    lambda c,m,s:c.update(top_k=6),
    lambda c,m,s:c.update(baseline_family='catboost'),
    lambda c,m,s:c.update(prior_exploration_of_development=None),
    lambda c,m,s:c.update(baseline_regularization_grid=[1,.01,.1]),
    lambda c,m,s:c['variants'][0].update(numeric_missing_indicators=True),
    lambda c,m,s:c['variants'][1].update(drop_features=['age']),
])
def test_contract_fail_closed(stub_v13,tamper):
    args=contracts();tamper(*args)
    with pytest.raises((ValueError,KeyError)):
        validate_config(*args)


def test_select_pair_prefers_better_model():
    rows=[{'family':'logistic','variant':'reference','loss':.14,'params':{'C':.1}},
          {'family':'logistic','variant':'missingness_indicators','loss':.135,'params':{'C':.2}},
          {'family':'catboost','variant':'reference','loss':.131,'params':{'depth':4}}]
    s=select_pair(rows,.001)
    assert s['pair']=='catboost__reference'
    assert s['inner_cv_loss']==.131


def test_select_pair_practical_tie_rule():
    rows=[{'family':'catboost','variant':'missingness_indicators','loss':.130,'params':{}},
          {'family':'logistic','variant':'reference','loss':.1305,'params':{}},
          {'family':'logistic','variant':'missingness_indicators','loss':.1304,'params':{}}]
    s=select_pair(rows,.001)
    assert s['pair']=='logistic__reference'
    assert len(s['within_tie_margin'])==3


def test_select_pair_prefers_base_preprocessing_when_near_equal():
    rows=[{'family':'logistic','variant':'reference','loss':.133,'params':{'C':.1}},
          {'family':'logistic','variant':'missingness_indicators','loss':.1325,'params':{'C':.2}}]
    assert select_pair(rows,.001)['variant']=='reference'
    assert select_pair(rows,0)['variant']=='missingness_indicators'


def test_pair_rejects_bad_evidence():
    bad=[{'family':'logistic','variant':'reference','loss':float('nan'),'params':{}}]
    with pytest.raises(ValueError):select_pair(bad,.001)
    bad=[{'family':'logistic','variant':'reference','loss':.1,'params':{}},
         {'family':'logistic','variant':'reference','loss':.12,'params':{}}]
    with pytest.raises(ValueError):select_pair(bad,.001)


def test_paired_repeat_math_and_rejects_duplicate():
    records=[{'seed':10,'reference_loss':.14,'joint_loss':.13},
             {'seed':11,'reference_loss':.145,'joint_loss':.143}]
    r=paired_summary(records)
    assert r['mean_gain_vs_reference']==.006
    assert r['repeats_improved']==2
    records[1]['seed']=10
    with pytest.raises(ValueError):paired_summary(records)


def test_paired_repeat_rejects_nan():
    with pytest.raises(ValueError):paired_summary([{'seed':1,'reference_loss':.2,'joint_loss':float('nan')}])


def test_content_hash_order_invariance():
    assert digest_json({'a':1,'b':2}) == digest_json({'b':2,'a':1})
    assert digest_json({'a':1}) != digest_json({'a':2})


def test_module_import_has_no_training_result():
    import ml.case_joint_selection_v16 as mod
    assert callable(mod.run) and callable(mod.main)
    assert not hasattr(mod,'trained_model')


def sample_local_release():
    """Hand-built metadata fixture. Never reads, trains or loads patient models."""
    config, _, _ = contracts()
    allowed = [pair_name(*pair) for pair in candidate_pairs(config)]
    report = {
        'schema': SCHEMA,
        'report_type': 'LOCAL_EXPLORATORY_JOINT_DEVELOPMENT_ONLY',
        'case_id': config['case_id'], 'v16_protocol_sha256': digest_json(config),
        'cohort': {'development_n': 120, 'evaluation_predictions_generated': 0},
        'holdout_scored': False, 'model_saved_locally_only': True,
        'clinical_deployment_permitted': False, 'public_export': False,
        'preprocessing_definitions': config['variants'],
        'models_and_policies': allowed,
        'selected_model': 'random_forest',
        'selected_preprocessing': 'missingness_indicators',
        'final_development_selection': {
            'selection': {'pair': 'random_forest__missingness_indicators'}},
        'fold_details': [
            {'seed': 4216, 'fold': i+1,
             'selected_pair': allowed[i]} for i in range(3)],
        'repeated_nested': [
            {'seed': 4216, 'reference_loss': 0.1373795, 'joint_loss': 0.1351896}],
    }
    return config, report


def test_local_release_accepts_named_preprocessing_object():
    cfg, report = sample_local_release()
    result = validate_local_release(cfg, report, True)
    assert result['selected_pair'] == 'random_forest__missingness_indicators'
    assert result['holdout_scored'] is False
    assert result['outer_assessments'] == 3


@pytest.mark.parametrize('tamper', [
    lambda c, r: r.update(selected_preprocessing='unknown'),
    lambda c, r: r.update(selected_model='unapproved'),
    lambda c, r: r.update(v16_protocol_sha256='wrong'),
    lambda c, r: r['cohort'].update(evaluation_predictions_generated=1),
    lambda c, r: r.update(holdout_scored=True),
    lambda c, r: r.update(public_export=True),
    lambda c, r: r['final_development_selection']['selection'].update(pair='logistic__reference'),
    lambda c, r: r['fold_details'][0].update(selected_pair='unknown__reference'),
    lambda c, r: r['repeated_nested'][0].update(joint_loss=float('nan')),
    lambda c, r: r.update(preprocessing_definitions=[{'name':'reference'}]),
])
def test_local_release_rejects_bad_contract(tamper):
    cfg, report = sample_local_release()
    tamper(cfg, report)
    with pytest.raises(ValueError):
        validate_local_release(cfg, report, True)


def test_local_release_requires_local_model_file():
    cfg, report = sample_local_release()
    with pytest.raises(ValueError, match='model is missing'):
        validate_local_release(cfg, report, False)
