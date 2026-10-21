import pytest
from scripts.export_nhanes_aggregate import export, PROVENANCE


def sample_report():
    def metric(tn=717,fp=294,fn=63,tp=183):
        return {'roc_auc':.7993,'average_precision':.5242,'brier':.1236,'accuracy':.716,
          'precision':.3836,'recall':.7439,'f1':.5062,'confusion':{'tn':tn,'fp':fp,'fn':fn,'tp':tp}}
    names=['Regularized logistic regression','Histogram gradient boosting','XGBoost','CatBoost']
    return {'report_type':'AGGREGATE_RESEARCH_METRICS_ONLY','data_origin':'NHANES_PUBLIC_2019_LMF',
      'training_cycle':'2011-2012','test_cycle':'2013-2014',
      'counts':{'train':873,'validation':292,'test':1257,'test_events':246},
      'selected_model':'CatBoost',
      'validation_comparisons':[{'model':name,'validation':{'roc_auc':.79,'average_precision':.53,'brier':.13}} for name in names],
      'test_unweighted_threshold_050':metric(tn=978,fp=33,fn=187,tp=59),
      'test_unweighted_validation_threshold':metric(),
      'baseline_predict_none_accuracy':.8043,
      'validation_selected_threshold_F2':.17,
      'test_auc_95ci_fixed_model_bootstrap':[.7676,.8260],
      'SEQN':[123,456], 'secret_participant_data':{'do_not_export':'never'} }

def test_export_only_safe_aggregate_fields():
    res=export(sample_report())
    assert res['provenance']==PROVENANCE
    assert res['counts']['total']==2422
    assert res['selectedModel']=='CatBoost'
    assert res['testAtF2']['confusion']['tp']==183
    assert 'SEQN' not in str(res) and 'secret_participant_data' not in str(res)
    assert 'patients' not in res and 'cases' not in res and 'scores' not in res

def test_reject_synthetic_report():
    r=sample_report();r['data_origin']='SYNTHETIC'
    with pytest.raises(ValueError):export(r)

def test_reject_bad_confusion():
    r=sample_report();r['test_unweighted_validation_threshold']['confusion']['tp']=184
    with pytest.raises(ValueError):export(r)

def test_reject_bad_counts():
    r=sample_report();r['counts']['test_events']=1
    with pytest.raises(ValueError):export(r)

def test_reject_invalid_metric():
    r=sample_report();r['test_unweighted_threshold_050']['roc_auc']=float('nan')
    with pytest.raises(ValueError):export(r)
