"""v0.18 pure contract/arithmetic fixtures: NO fitted model or respondent records."""
import copy
import math
import pytest
from ml.case_reliability_v18 import (SCHEMA,logit_scores,bounded_scores,
    validate_design,summarize_missingness,choose_nothing,validate_local_report)
from ml.case_joint_selection_v16 import digest_json


def fixtures():
    joint={'case_id':'xcase','families':['logistic','random_forest'],
        'variants':[{'name':'reference'},{'name':'missingness_indicators'}],
        'outer_seeds':[11]}
    manifest={'case_id':'xcase','task':'classification'}
    rep={'case_id':'xcase','v16_protocol_sha256':digest_json(joint),
        'dataset_sha256':'a'*64,'selected_model':'random_forest',
        'selected_preprocessing':'missingness_indicators',
        'selected_parameters':{'max_depth':4},
        'final_development_selection':{'selection':{'pair':'random_forest__missingness_indicators'}},
        'holdout_scored':False}
    cfg={'schema':SCHEMA,'case_id':'xcase','v16_protocol_sha256':digest_json(joint),
        'frozen_selected_pair':'random_forest__missingness_indicators',
        'outer_folds':3,'inner_folds':3,'outer_seeds':[13,14],
        'methods':['identity','sigmoid','isotonic'],
        'isotonic_min_calibration_n':1000,'calibration_bins':4,
        'min_calibration_bin_n':30,'min_missing_group_n':20,
        'post_hoc_development_reuse':True,
        'holdout_policy':'development_only_no_evaluation'}
    return cfg,joint,manifest,rep

def test_valid_design():
    cfg,j,m,r=fixtures()
    v=validate_design(cfg,j,m,r)
    assert v['frozen_recipe']=='random_forest__missingness_indicators'
    assert v['max_base_model_fits']==24
    assert v['outer_assessments']==6

@pytest.mark.parametrize('mutate',[
 lambda c,j,m,r:c.update(schema='WRONG'),
 lambda c,j,m,r:c.update(case_id='other'),
 lambda c,j,m,r:c.update(v16_protocol_sha256='other'),
 lambda c,j,m,r:c.update(frozen_selected_pair='logistic__reference'),
 lambda c,j,m,r:c.update(outer_folds=1),
 lambda c,j,m,r:c.update(inner_folds=6),
 lambda c,j,m,r:c.update(outer_seeds=[11,12]),
 lambda c,j,m,r:c.update(outer_seeds=[13,13]),
 lambda c,j,m,r:c.update(methods=['sigmoid','identity','isotonic']),
 lambda c,j,m,r:c.update(isotonic_min_calibration_n=12),
 lambda c,j,m,r:c.update(min_missing_group_n=4),
 lambda c,j,m,r:c.update(post_hoc_development_reuse=False),
 lambda c,j,m,r:c.update(holdout_policy='evaluate'),
 lambda c,j,m,r:r.update(holdout_scored=True),
 lambda c,j,m,r:r['final_development_selection']['selection'].update(pair='logistic__reference'),
 lambda c,j,m,r:m.update(task='regression'),
])
def test_fail_closed(mutate):
    c,j,m,r=fixtures();mutate(c,j,m,r)
    with pytest.raises(ValueError):validate_design(c,j,m,r)

def test_logit_and_bounded_probability():
    import numpy as np
    vals=logit_scores([0,.25,.5,.75,1.])
    assert np.isfinite(vals).all() and vals[0] < vals[1] < vals[2] < vals[3] < vals[4]
    with pytest.raises(ValueError):bounded_scores([.3,float('nan')])
    with pytest.raises(ValueError):bounded_scores([-.01,.2])
    with pytest.raises(ValueError):bounded_scores([1.01])

def test_missingness_suppression_arithmetic():
    import numpy as np
    import pandas as pd
    x=pd.DataFrame({'mobility':[None]*4+[1]*16,'age':range(20),
                    'rare':[None]+[1]*19})
    y=pd.Series([1,0,1,1]+[0]*15+[1])
    rows=summarize_missingness(x,y,3)
    mobility=next(v for v in rows if v['feature']=='mobility')
    assert mobility['missing_n']==4 and mobility['observed_n']==16
    assert mobility['event_rate_missing']==.75
    assert mobility['event_rate_observed']==.0625
    rare=next(v for v in rows if v['feature']=='rare')
    assert rare['event_rate_missing'] is None and rare['event_rate_suppressed'] is True
    assert len(rows)==2

def test_pure_comparison_never_selects():
    values={'identity':{'brier':.14,'log_loss':.45,'descriptive_ece':.02},
            'sigmoid':{'brier':.13,'log_loss':.43,'descriptive_ece':.03}}
    x=choose_nothing(values)
    assert x[0]['delta_brier_vs_identity']==0
    assert x[1]['delta_brier_vs_identity']==-.01
    assert x[1]['delta_descriptive_ece_vs_identity']==.01
    assert all('selected' not in r for r in x)

def fake_report():
    cfg,joint,manifest,_=fixtures()
    one={'n':100,'brier':.13,'log_loss':.45,'roc_auc':.7,
         'average_precision':.4,'descriptive_ece':.03}
    row=lambda seed:{'seed':seed,'metrics':{'identity':dict(one),'sigmoid':dict(one)}}
    report={'schema':SCHEMA,'report_type':'LOCAL_POST_HOC_DEVELOPMENT_RELIABILITY_ONLY',
        'case_id':'xcase','manifest_sha256':digest_json(manifest),
        'v16_protocol_sha256':digest_json(joint),'reliability_protocol_sha256':digest_json(cfg),
        'frozen_selected_pair':cfg['frozen_selected_pair'],
        'cohort':{'development_n':100,'evaluation_predictions_generated':0},
        'holdout_scored':False,'model_replaced':False,'calibrator_promoted':False,
        'new_model_binary_saved':False,'public_export':False,
        'repeated_development_calibration':[row(13),row(14)],
        'missingness_audit':[]}
    return cfg,joint,manifest,report

def test_report_gate_accepts_pure_fixture():
    cfg,joint,manifest,report=fake_report()
    assert validate_local_report(cfg,joint,manifest,report)['repeats']==2

@pytest.mark.parametrize('edit',[
 lambda r:r.update(holdout_scored=True),
 lambda r:r.update(calibrator_promoted=True),
 lambda r:r.update(model_replaced=True),
 lambda r:r.update(public_export=True),
 lambda r:r['cohort'].update(evaluation_predictions_generated=1),
 lambda r:r.update(frozen_selected_pair='wrong'),
 lambda r:r.update(reliability_protocol_sha256='wrong'),
 lambda r:r['repeated_development_calibration'].pop(),
 lambda r:r['repeated_development_calibration'][0]['metrics'].pop('identity'),
 lambda r:r['repeated_development_calibration'][0]['metrics']['sigmoid'].update(brier=float('nan')),
])
def test_report_gate_rejects_unsafe(edit):
    c,j,m,r=fake_report();edit(r)
    with pytest.raises(ValueError):validate_local_report(c,j,m,r)

def test_module_does_not_fit_on_import():
    import ml.case_reliability_v18 as mod
    assert callable(mod.run) and callable(mod.main)
    assert not hasattr(mod,'final_model')
